"""Web-Oberfläche: fünf Bereiche — Profil, Eingang, Bestand, Finden, Abnahme — plus /start.

Hier steht keine Fachlogik. Jede Route ruft die Werkstatt (bzw. lesend ihren
Index) und rendert das Ergebnis; Formulare antworten mit POST + Redirect, damit
ein Neuladen keine Entscheidung wiederholt. Ein Server hält höchstens eine
Werkstatt — `create_app(werkstatt)`; ohne Werkstatt führt jede Seite auf
`/start`, wo Quelle und Zielablage gewählt werden.

Das Einordnen läuft als Hintergrund-Thread (`Job`), damit ein Stapel von
hundert Dateien den Browser nicht blockiert; `/eingang` zeigt Fortschritt und
lädt sich alle fünf Sekunden neu, solange der Job läuft.

Fachliche Fehler (`DokumentenassistentFehler`, `ValueError`) landen auf einer
lesbaren Fehlerseite, nie in einem 500er: ein abgeschaltetes Ollama darf den
Menschen nicht vor eine Traceback-Wand stellen.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from dokumentenassistent import dokument, modellwahl
from dokumentenassistent import web_ansicht as ansicht
from dokumentenassistent.provider import (
    ModelProvider,
    OcrEinstellungen,
    OcrNichtVerfuegbar,
    ProviderFehler,
    Sucheinstellungen,
    lade_abnahme_protokoll,
    lade_modelle,
    lade_ocr_einstellungen,
    lade_provider_suche,
    lade_seitenuebergreifend,
    lade_sucheinstellungen,
)
from dokumentenassistent.typen import DokumentenassistentFehler, Profil
from dokumentenassistent.werkstatt import Werkstatt

HIER = Path(__file__).parent
VORLAGEN = HIER / "templates"
STATISCH = HIER / "static"
ZULETZT_STANDARD = Path.home() / ".config" / "dokumentenassistent" / "zuletzt.json"

templates = Jinja2Templates(directory=str(VORLAGEN))

STATUS_TEXT = {
    "wartet": "wartet",
    "sicher": "sicher",
    "unklar": "unklar",
    "konflikt": "Konflikt",
    "duplikat": "Duplikat",
    "ocr_unsicher": "Text nicht lesbar",
}

ZUSTAND_TEXT = {
    "gefunden": "gefunden",
    "nicht_gefunden": "nicht gefunden",
    "widerspruechlich": "widersprüchlich",
}

PROTOKOLL_TEXT = {
    "duplikat": "Duplikat erkannt",
    "profil_bestaetigt": "Profil bestätigt",
    "vorschlag": "Vorschlag erzeugt",
    "korrektur": "Korrektur durch Mensch",
    "konflikt_entschieden": "Konflikt entschieden",
    "freigabe": "Kopie erzeugt",
    "uebersprungen": "Übersprungen",
    "frage": "Frage gestellt",
    "nicht_lesbar": "Nicht lesbar",
    "einordnen_abgebrochen": "Einordnen abgebrochen",
}

BEREICHE = (
    ("profil", "/profil", "01", "Profil", "Zweck, Kategorien, Namensschema"),
    ("eingang", "/eingang", "02", "Eingang", "Vorschläge prüfen und freigeben"),
    ("bestand", "/bestand", "03", "Bestand", "Zielablage, Duplikate, Protokoll"),
    ("finden", "/finden", "04", "Finden", "Fragen mit Belegen beantworten"),
    ("abnahme", "/abnahme", "05", "Abnahme", "Antworten selbst beurteilen"),
)

ABNAHME_STANDARD = Path("beweise/abnahme")
URTEILE = ("richtig", "falsch")

KONFLIKT_TEXT = {
    "ersetzt": "ersetzt",
    "verschiedene_sachverhalte": "verschiedene Sachverhalte",
    "nicht_entscheidbar": "nicht entscheidbar",
    "eigener_wert": "eigener Wert",
}

KONFLIKT_OPTIONEN = (
    ("ersetzt", "ersetzt", "Der neuere Wert gilt, der ältere ist überholt."),
    (
        "verschiedene_sachverhalte",
        "verschiedene Sachverhalte",
        "Beide Werte bleiben gültig, sie gehören zu verschiedenen Vorgängen.",
    ),
    (
        "nicht_entscheidbar",
        "nicht entscheidbar",
        "Bleibt offen. Beide Dateien bleiben aus der Zielablage heraus.",
    ),
)


# --------------------------------------------------------------- Darstellung


def _spannen(text: str, wortlaute: Iterable[str]) -> list[tuple[int, int]]:
    """Alle Fundorte der Wortlaute im Text, überlappungsfrei und sortiert."""
    treffer: list[tuple[int, int]] = []
    for wortlaut in wortlaute:
        if not wortlaut:
            continue
        start = text.find(wortlaut)
        while start != -1:
            treffer.append((start, start + len(wortlaut)))
            start = text.find(wortlaut, start + len(wortlaut))
    zusammengefasst: list[tuple[int, int]] = []
    for anfang, ende in sorted(treffer):
        if zusammengefasst and anfang <= zusammengefasst[-1][1]:
            vorher = zusammengefasst.pop()
            zusammengefasst.append((vorher[0], max(vorher[1], ende)))
        else:
            zusammengefasst.append((anfang, ende))
    return zusammengefasst


def hervorheben(text: str, wortlaute: Iterable[str]) -> Markup:
    """Belegter Wortlaut im Original-Absatz als <mark>. Alles andere wird escaped."""
    stellen = _spannen(text, list(wortlaute))
    if not stellen or stellen == [(0, len(text))]:
        return escape(text)  # ein vollständig markierter Absatz hebt nichts hervor
    teile: list[Markup] = []
    zeiger = 0
    for anfang, ende in stellen:
        teile.append(escape(text[zeiger:anfang]))
        teile.append(Markup("<mark>{}</mark>").format(text[anfang:ende]))
        zeiger = ende
    teile.append(escape(text[zeiger:]))
    return Markup("").join(teile)


_ZITAT = re.compile(r"\[([^\]]+#S\d+#A\d+)\]")


def antwort_html(text: str, karten: Iterable) -> Markup:
    """Zitate `[Datei#S1#A2]` im Antworttext werden zu nummerierten Verweisen auf die Belegkarten."""
    from dokumentenassistent.zitate import zitatgruppen

    nummern = {karte.fundstelle.id: nr for nr, karte in enumerate(karten, start=1)}

    teile = []
    zeiger = 0
    for start, end, gruppe in zitatgruppen(text, nummern):
        teile.append(str(escape(text[zeiger:start])))
        teile.append(', '.join(
            f'<a class="zitat-ref" href="#beleg-{nummern[id_]}">{nummern[id_]}</a>'
            for id_ in dict.fromkeys(gruppe)))
        zeiger = end
    teile.append(str(escape(text[zeiger:])))
    return Markup("".join(teile))


def zeit_lokal(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d.%m.%Y · %H:%M:%S")
    except ValueError:
        return iso


def _protokoll_detail(eintrag: dict) -> str:
    art = eintrag.get("art")
    if art == "duplikat":
        return " = ".join(Path(p).name for p in eintrag.get("pfade", ()))
    if art == "profil_bestaetigt":
        return f"{eintrag.get('zweck', '')} · {len(eintrag.get('kategorien', ()))} Kategorien"
    if art == "vorschlag":
        status = STATUS_TEXT.get(eintrag.get("status"), eintrag.get("status", ""))
        return f"{eintrag.get('name', '')} → {status}"
    if art == "korrektur":
        return f"{eintrag.get('kategorie') or '—'} · {eintrag.get('zielname') or '—'}"
    if art == "konflikt_entschieden":
        eigener = eintrag.get("eigener_wert")
        return eintrag.get("entscheidung", "") + (f" · „{eigener}“" if eigener else "")
    if art == "freigabe":
        return f"{eintrag.get('name', '')} → {Path(eintrag.get('zielpfad', '')).name}"
    if art in ("uebersprungen", "nicht_lesbar"):
        return f"{eintrag.get('name', '')} — {eintrag.get('grund', '')}"
    if art == "frage":
        status = ZUSTAND_TEXT.get(eintrag.get("status"), eintrag.get("status", ""))
        return f"„{eintrag.get('frage', '')}“ → {status}"
    if art == "einordnen_abgebrochen":
        return f"nach {eintrag.get('erledigt', 0)} von {eintrag.get('gesamt', 0)} Modellaufrufen"
    return ""


def _protokoll_zeilen(eintraege: tuple[dict, ...], anzahl: int = 20) -> list[dict]:
    letzte = list(eintraege)[-anzahl:]
    return [
        {
            "zeit": zeit_lokal(e.get("zeit", "")),
            "art": e.get("art", ""),
            "titel": PROTOKOLL_TEXT.get(e.get("art"), e.get("art", "")),
            "detail": _protokoll_detail(e),
        }
        for e in reversed(letzte)
    ]


templates.env.globals.update(
    hervorheben=hervorheben,
    antwort_html=antwort_html,
    STATUS_TEXT=STATUS_TEXT,
    ZUSTAND_TEXT=ZUSTAND_TEXT,
    KONFLIKT_OPTIONEN=KONFLIKT_OPTIONEN,
    KONFLIKT_TEXT=KONFLIKT_TEXT,
    BEREICHE=BEREICHE,
    LAGE_STATUS=ansicht.LAGE_STATUS,
)
templates.env.filters["zeit_lokal"] = zeit_lokal


# ------------------------------------------------------------ Hintergrundjob


@dataclass
class Job:
    """Zustand eines Hintergrundlaufs. Bewusst veränderlich: der Thread schreibt,
    die Seite liest — ein gemeinsames Objekt ist hier ehrlicher als Kopien.

    `phase` unterscheidet Auslesen (OCR) von Einordnen. Bis 24.09.2026 gab es nur
    das Einordnen als Job; `/profil/einlesen` lief synchron und hielt den Browser
    die ganze OCR-Zeit fest (gemessen 403 s über 126 echte Dateien, bei einem
    Bestand aus Scans Stunden) — ohne Balken, ohne Zähler, ohne Abbrechen."""

    phase: str = "einordnen"
    laeuft: bool = False
    erledigt: int = 0
    gesamt: int = 0
    aktuell: str = ""
    gestartet: float | None = None
    beendet: float | None = None
    fehler: str | None = None
    abgebrochen: bool = False
    neu: int = 0  # Vorschläge, die dieser Lauf erzeugt hat
    thread: threading.Thread | None = None
    abbruch: threading.Event = field(default_factory=threading.Event)


def _einordnen_im_hintergrund(werkstatt: Werkstatt, job: Job) -> None:
    """Läuft im Thread. Fehler landen in `job.fehler`, nie als toter Thread."""
    vorher = len(werkstatt.index.vorschlaege())

    def fortschritt(erledigt: int, gesamt: int, name: str) -> None:
        job.erledigt, job.gesamt, job.aktuell = erledigt, gesamt, name

    try:
        werkstatt.einordnen(fortschritt=fortschritt, abbruch=job.abbruch)
    except DokumentenassistentFehler as fehler:
        job.fehler = str(fehler)
    except Exception as fehler:  # noqa: BLE001 — ein Thread ohne Fänger stirbt stumm
        job.fehler = f"{type(fehler).__name__}: {fehler}"
    job.neu = len(werkstatt.index.vorschlaege()) - vorher
    job.abgebrochen = job.abbruch.is_set()
    # Der Fortschritt meldet VOR jedem Modellaufruf; die laufende Datei wird bei Abbruch
    # noch fertig gerechnet — also zählt der zuletzt gemeldete Aufruf als erledigt.
    if job.fehler is None:
        job.erledigt = min(job.erledigt + 1, job.gesamt) if job.abgebrochen else job.gesamt
    job.beendet = time.time()
    job.laeuft = False


def _auslesen_im_hintergrund(werkstatt: Werkstatt, job: Job) -> None:
    """Erfassen und Auslesen in einem Lauf. Erfassen ist schnell und hat keine eigene
    Anzeige; die Zeit steckt im Auslesen, und nur dort meldet der Fortschritt."""

    def fortschritt(erledigt: int, gesamt: int, name: str) -> None:
        job.erledigt, job.gesamt, job.aktuell = erledigt, gesamt, name

    try:
        job.neu = len(werkstatt.erfassen())
        werkstatt.auslesen(fortschritt=fortschritt)
    except DokumentenassistentFehler as fehler:
        job.fehler = str(fehler)
    except Exception as fehler:  # noqa: BLE001 — ein Thread ohne Fänger stirbt stumm
        job.fehler = f"{type(fehler).__name__}: {fehler}"
    if job.fehler is None:
        job.erledigt = job.gesamt
    job.beendet = time.time()
    job.laeuft = False


_JOBS = {"einordnen": _einordnen_im_hintergrund, "auslesen": _auslesen_im_hintergrund}


def _job_starten(request: Request, werkstatt: Werkstatt, phase: str = "einordnen") -> Job:
    job = Job(phase=phase, laeuft=True, gestartet=time.time())
    job.thread = threading.Thread(
        target=_JOBS[phase], args=(werkstatt, job), daemon=True, name=phase
    )
    request.app.state.job = job
    job.thread.start()
    return job


# ------------------------------------------------------------ Ansichtsdaten


class KeineWerkstatt(Exception):
    """Noch kein Bestand geöffnet — die Seite führt auf /start."""


def _seite(name: str, kontext: dict, status: int = 200) -> HTMLResponse:
    """Eine Vorlage rendern. `request` steckt bereits im Kontext (siehe `_basis`)."""
    return templates.TemplateResponse(
        request=kontext["request"], name=name, context=kontext, status_code=status
    )


def _werkstatt(request: Request) -> Werkstatt:
    werkstatt = request.app.state.werkstatt
    if werkstatt is None:
        raise KeineWerkstatt
    return werkstatt


WerkstattAbhaengigkeit = Annotated[Werkstatt, Depends(_werkstatt)]


def _basis(request: Request, werkstatt: Werkstatt | None, aktiv: str) -> dict:
    job: Job = request.app.state.job
    return {
        "request": request,
        "aktiv": aktiv,
        "quelle": werkstatt.quelle if werkstatt else None,
        "zielablage": werkstatt.zielablage if werkstatt else None,
        "profil": werkstatt.profil if werkstatt else None,
        "hinweis": request.query_params.get("hinweis"),
        "offene_konflikte": len(werkstatt.index.konflikte(offen=True)) if werkstatt else 0,
        "job": job,
        "modelle": modellwahl.anzeige(werkstatt) if werkstatt else None,
        "modellwahl": _modellwahl(werkstatt) if werkstatt else None,
    }


def _modellwahl(werkstatt: Werkstatt) -> dict | None:
    p, ps = werkstatt.provider, getattr(werkstatt, "provider_suche", None)
    if not hasattr(p, "host"):  # Test-Fakes ohne Laufzeit: nur Anzeige, keine Wahl
        return None
    return {"verfuegbar": modellwahl.verfuegbar(werkstatt),
            "llm": p.llm_modell, "llm_suche": (ps or p).llm_modell,
            "embedding": p.embed_modell, "sprache": getattr(p, "sprache", "Deutsch"),
            "fundstellen": modellwahl.fundstellen_anzahl(werkstatt)}


def _zeilen_text(rohtext: str) -> tuple[str, ...]:
    return tuple(zeile.strip() for zeile in rohtext.splitlines() if zeile.strip())


def _zurueck(ziel: str, hinweis: str) -> RedirectResponse:
    trenner = "&" if "?" in ziel else "?"
    return RedirectResponse(f"{ziel}{trenner}hinweis={quote(hinweis)}", status_code=303)


# ------------------------------------------------------------------- Routen

router = APIRouter()


@router.get("/", include_in_schema=False)
def start() -> RedirectResponse:
    return RedirectResponse("/profil", status_code=303)


# ---- /start: Bestand wählen


def _start_kontext(request: Request, werte: dict, fehler: str | None = None) -> dict:
    werkstatt: Werkstatt | None = request.app.state.werkstatt
    return _basis(request, werkstatt, "start") | {
        "werte": werte,
        "fehler": fehler,
        "zuletzt": ansicht.lies_zuletzt(request.app.state.zuletzt_pfad),
    }


@router.get("/start", response_class=HTMLResponse)
def start_seite(request: Request):
    return _seite("start.html", _start_kontext(request, {"quelle": "", "ziel": "", "zweck": ""}))


@router.get("/ordner")
def ordner_liste(pfad: str = ""):
    """Unterordner eines Pfades für den Ordnerbrowser auf /start.

    Gibt nur Ordnernamen und ihren Pfad — keine Dateien, keine Inhalte. Ein
    Grenzfall ist eine Meldung mit 400, kein Traceback: die Seite zeigt sie an,
    statt den Browser leer stehen zu lassen. Ein Pfad im Textfeld bleibt der
    schnellere Weg, der Browser ist der Ausweg, wenn man ihn nicht zur Hand hat.
    """
    try:
        return JSONResponse(ansicht.unterordner(pfad))
    except ValueError as fehler:
        return JSONResponse({"fehler": str(fehler)}, status_code=400)


def _pruefe_pfade(quelle_text: str, ziel_text: str) -> tuple[Path, Path]:
    """Lesbare Fehler statt Traceback: Quelle muss ein Ordner sein, Ziel darf nicht darin liegen."""
    if not quelle_text.strip():
        raise ValueError("Bitte einen Quellordner angeben.")
    quelle = Path(quelle_text.strip()).expanduser()
    if not quelle.is_dir():
        raise ValueError(f"Quellordner nicht gefunden oder kein Ordner: {quelle}")
    ziel = Path(ziel_text.strip()).expanduser() if ziel_text.strip() else quelle.with_name(quelle.name + "_sortiert")
    if ziel.resolve() == quelle.resolve() or ziel.resolve().is_relative_to(quelle.resolve()):
        raise ValueError(f"Die Zielablage darf nicht innerhalb der Quelle liegen: {ziel}")
    return quelle, ziel


@router.post("/start", response_class=HTMLResponse)
def start_oeffnen(
    request: Request,
    quelle: str = Form(""),
    ziel: str = Form(""),
    zweck: str = Form(""),
):
    werte = {"quelle": quelle, "ziel": ziel, "zweck": zweck}
    if request.app.state.job.laeuft:
        return _seite("start.html", _start_kontext(request, werte, "Solange eine Einordnung läuft, bleibt der Bestand, wie er ist."))
    try:
        quelle_pfad, ziel_pfad = _pruefe_pfade(quelle, ziel)
        provider = request.app.state.provider_laden()
        provider_suche = request.app.state.provider_suche_laden()
        einstellungen = request.app.state.sucheinstellungen_laden()
        ocr = request.app.state.ocr_laden()
        seitenuebergreifend = request.app.state.seitenuebergreifend_laden()
    except (ValueError, ProviderFehler, OcrNichtVerfuegbar) as fehler:
        return _seite("start.html", _start_kontext(request, werte, str(fehler)))
    request.app.state.werkstatt = Werkstatt(
        quelle=quelle_pfad, zielablage=ziel_pfad, provider=provider, provider_suche=provider_suche,
        sucheinstellungen=einstellungen, ocr=ocr,
        seitenuebergreifend=seitenuebergreifend,
    )
    request.app.state.zweck_vorbelegt = zweck.strip()
    ansicht.merke_zuletzt(request.app.state.zuletzt_pfad, quelle_pfad, ziel_pfad)
    return RedirectResponse("/profil", status_code=303)


# ---- Profil


@router.get("/profil", response_class=HTMLResponse)
def profil_seite(request: Request, werkstatt: WerkstattAbhaengigkeit):
    return _seite("profil.html", _profil_kontext(request, werkstatt, None))


def _profil_kontext(request: Request, werkstatt: Werkstatt, entwurf: Profil | None) -> dict:
    job: Job = request.app.state.job
    return (
        _basis(request, werkstatt, "profil")
        | ansicht.profil_daten(werkstatt)
        | {
            "entwurf": entwurf,
            "zweck_vorbelegt": request.app.state.zweck_vorbelegt,
            "job": job,
            # Nur die eigene Phase zeigen: sonst blendet /profil den Balken des
            # Einordnens ein, das auf /eingang läuft.
            "fortschritt": (ansicht.fortschritt_daten(job, time.time())
                            if job.laeuft and job.phase == "auslesen" else None),
            "job_meldung": ansicht.job_meldung(job) if job.phase == "auslesen" else None,
        }
    )


@router.post("/profil/einlesen")
def profil_einlesen(request: Request, werkstatt: WerkstattAbhaengigkeit) -> RedirectResponse:
    """Startet Erfassen + Auslesen im Hintergrund und kehrt sofort zurück. Kein Modellaufruf,
    aber bei Scans der teuerste Schritt überhaupt — deshalb ein Job und keine Wartezeit."""
    if request.app.state.job.laeuft:
        return _zurueck("/profil", "Es läuft bereits ein Durchgang — bitte warten.")
    _job_starten(request, werkstatt, phase="auslesen")
    return RedirectResponse("/profil", status_code=303)


@router.post("/profil/vorschlagen", response_class=HTMLResponse)
def profil_vorschlagen(
    request: Request,
    werkstatt: WerkstattAbhaengigkeit,
    zweck: str = Form(...),
):
    """Der Entwurf wird nur gezeigt, nicht gespeichert — bestätigt wird er im Formular."""
    entwurf = werkstatt.profil_vorschlagen(zweck.strip())
    return _seite("profil.html", _profil_kontext(request, werkstatt, entwurf))


@router.post("/profil/bestaetigen")
def profil_bestaetigen(
    werkstatt: WerkstattAbhaengigkeit,
    zweck: str = Form(...),
    kategorien: str = Form(""),
    dokumenttypen: str = Form(""),
    felder: str = Form(""),
    namensschema: str = Form(""),
    eigentuemer: str = Form(""),
) -> RedirectResponse:
    profil = Profil(
        zweck=zweck.strip(),
        kategorien=_zeilen_text(kategorien),
        dokumenttypen=_zeilen_text(dokumenttypen),
        felder=_zeilen_text(felder),
        namensschema=namensschema.strip(),
        eigentuemer=eigentuemer.strip() or None,
    )
    werkstatt.profil_bestaetigen(profil)
    return _zurueck("/profil", "Profil bestätigt. Es gilt ab jetzt für jede Einordnung.")


# ---- Eingang


@router.get("/eingang", response_class=HTMLResponse)
def eingang_seite(request: Request, werkstatt: WerkstattAbhaengigkeit):
    job: Job = request.app.state.job
    filter_ = ansicht.filter_aus(request.query_params)
    alle = ansicht.zeilen(werkstatt)
    zeilen = [z for z in alle if filter_.passt(z)]
    return _seite(
        "eingang.html",
        _basis(request, werkstatt, "eingang")
        | {
            "zeilen": zeilen,
            "uebersicht": ansicht.uebersicht(alle),
            "filter": filter_,
            "karten": ansicht.konfliktkarten(werkstatt),
            "anzahl_sicher": sum(1 for z in zeilen if z["status"] == "sicher"),
            "eingeordnet": any(z["vorschlag"] is not None for z in alle),
            "fortschritt": ansicht.fortschritt_daten(job, time.time()) if job.laeuft else None,
            "job_meldung": ansicht.job_meldung(job),
        },
    )


@router.post("/eingang/einordnen")
def eingang_einordnen(request: Request, werkstatt: WerkstattAbhaengigkeit) -> RedirectResponse:
    """Startet den Hintergrundjob und kehrt sofort zurück. Ein zweiter Start wartet."""
    if request.app.state.job.laeuft:
        return _zurueck("/eingang", "Es läuft bereits eine Einordnung — bitte warten oder abbrechen.")
    _job_starten(request, werkstatt)
    return RedirectResponse("/eingang", status_code=303)


@router.post("/eingang/abbrechen")
def eingang_abbrechen(request: Request) -> RedirectResponse:
    job: Job = request.app.state.job
    if not job.laeuft:
        return _zurueck("/eingang", "Es läuft keine Einordnung.")
    job.abbruch.set()
    return _zurueck("/eingang", "Abbruch angefordert — die laufende Datei wird noch fertig gerechnet.")


@router.post("/eingang/freigeben")
def eingang_freigeben(
    werkstatt: WerkstattAbhaengigkeit,
    hashes: Annotated[list[str] | None, Form()] = None,
    zurueck: str = Form("/eingang"),
) -> RedirectResponse:
    angehakt = tuple(hashes or ())
    if not angehakt:
        return _zurueck(zurueck, "Keine Zeile angehakt — nichts kopiert.")
    pfade = werkstatt.freigeben(angehakt)
    uebersprungen = len(angehakt) - len(pfade)
    hinweis = f"{len(pfade)} Kopien erzeugt."
    if uebersprungen:
        hinweis += f" {uebersprungen} übersprungen (siehe Protokoll im Bestand)."
    return _zurueck(zurueck, hinweis)


@router.post("/eingang/korrigieren")
def eingang_korrigieren(
    werkstatt: WerkstattAbhaengigkeit,
    hash: str = Form(...),
    kategorie: str = Form(""),
    zielname: str = Form(""),
    zurueck: str = Form("/eingang"),
) -> RedirectResponse:
    vorschlag = werkstatt.korrigiere(
        hash,
        kategorie=kategorie.strip() or None,
        zielname=zielname.strip() or None,
    )
    return _zurueck(zurueck, f"„{vorschlag.datei_name}“ korrigiert und auf sicher gesetzt.")


@router.get("/eingang/{hash}", response_class=HTMLResponse)
def eingang_detail(request: Request, hash: str, werkstatt: WerkstattAbhaengigkeit):
    datei = werkstatt.index.datei(hash)
    if datei is None:
        raise ValueError(f"Unbekannter Hash: {hash!r}")
    vorschlag = next((v for v in werkstatt.index.vorschlaege() if v.datei_hash == hash), None)
    offene = [k for k in werkstatt.index.konflikte(offen=True) if hash in (k.hash_a, k.hash_b)]
    return _seite(
        "eingang_detail.html",
        _basis(request, werkstatt, "eingang")
        | {
            "datei": datei,
            "vorschlag": vorschlag,
            "status": vorschlag.status if vorschlag else (werkstatt.index.status(hash) or "unklar"),
            "fundstellen": werkstatt.index.fundstellen(hash),
            "marken": ansicht.belege_je_fundstelle(vorschlag),
            "karten": [ansicht.konfliktkarte(werkstatt, k) for k in offene],
            "zielpfad": werkstatt.index.zielpfad(hash),
        },
    )


@router.post("/konflikt/{id}")
def konflikt_entscheiden(
    id: str,
    werkstatt: WerkstattAbhaengigkeit,
    entscheidung: str = Form(...),
    eigener_wert: str = Form(""),
    zurueck: str = Form("/eingang"),
) -> RedirectResponse:
    konflikt = werkstatt.entscheide_konflikt(id, entscheidung, eigener_wert.strip() or None)
    return _zurueck(zurueck, f"Konflikt zu „{konflikt.feld}“ entschieden: {entscheidung}.")


# ---- Bestand, Finden


@router.get("/bestand", response_class=HTMLResponse)
def bestand_seite(request: Request, werkstatt: WerkstattAbhaengigkeit):
    return _seite(
        "bestand.html",
        _basis(request, werkstatt, "bestand")
        | {
            "ablage": ansicht.ablage(werkstatt),
            "duplikate": ansicht.duplikate(werkstatt),
            "offene_karten": ansicht.konfliktkarten(werkstatt, offen=True),
            "entschiedene_karten": ansicht.konfliktkarten(werkstatt, offen=False),
            "protokoll": _protokoll_zeilen(werkstatt.index.protokoll()),
        },
    )


@router.get("/finden", response_class=HTMLResponse)
def finden_seite(request: Request, werkstatt: WerkstattAbhaengigkeit):
    return _seite(
        "finden.html",
        _basis(request, werkstatt, "finden") | {"frage": "", "antwort": None, "strittige": ()},
    )


@router.post("/finden", response_class=HTMLResponse)
def finden_fragen(
    request: Request,
    werkstatt: WerkstattAbhaengigkeit,
    frage: str = Form(...),
):
    antwort = werkstatt.frage(frage.strip())
    hashes = {karte.fundstelle.datei_hash for karte in antwort.karten}
    strittige = [
        k
        for k in werkstatt.index.konflikte(offen=True)
        if hashes & {k.hash_a, k.hash_b}
    ]
    return _seite(
        "finden.html",
        _basis(request, werkstatt, "finden")
        | {"frage": frage, "antwort": antwort, "strittige": strittige},
    )


# ---- Abnahme: der Auftraggeber urteilt selbst
#
# Zweck (22.09.2026): der bisherige Goldstandard `beispiele/malerbetrieb` ist synthetisch —
# Dokumente UND Fragen stammen aus derselben Quelle, die Retrieval-Zahlen tragen deshalb
# Autorenschafts-Bias (siehe `germanquad.py`). Hier legt der Auftraggeber 30–50 EIGENE
# Dokumente ein, fragt selbst und urteilt selbst. Kein Login, kein Löschen, kein Bearbeiten:
# jedes Urteil ist eine Zeile, die bleibt.


def _kartenzeilen(antwort) -> list[dict]:
    return [
        {"id": k.fundstelle.id, "datei": k.fundstelle.datei_name, "wortlaut": k.wortlaut}
        for k in antwort.karten
    ]


def _abnahme_kontext(request: Request, werkstatt: Werkstatt, frage: str, antwort) -> dict:
    return (
        _basis(request, werkstatt, "abnahme")
        | ansicht.abnahme_daten(request.app.state.abnahme_pfad)
        | {
            "frage": frage,
            "antwort": antwort,
            "karten_json": json.dumps(_kartenzeilen(antwort), ensure_ascii=False) if antwort else "[]",
        }
    )


@router.get("/abnahme", response_class=HTMLResponse)
def abnahme_seite(request: Request, werkstatt: WerkstattAbhaengigkeit):
    return _seite("abnahme.html", _abnahme_kontext(request, werkstatt, "", None))


@router.post("/abnahme", response_class=HTMLResponse)
def abnahme_fragen(request: Request, werkstatt: WerkstattAbhaengigkeit, frage: str = Form(...)):
    antwort = werkstatt.frage(frage.strip())
    return _seite("abnahme.html", _abnahme_kontext(request, werkstatt, frage.strip(), antwort))


@router.post("/abnahme/urteil")
def abnahme_urteilen(
    request: Request,
    werkstatt: WerkstattAbhaengigkeit,
    frage: str = Form(...),
    antwort: str = Form(""),
    antwort_status: str = Form(...),
    karten: str = Form("[]"),
    urteil: str = Form(...),
    bemerkung: str = Form(""),
) -> RedirectResponse:
    """Hängt eine Zeile an `beweise/abnahme/<datum>/urteile.jsonl` (Standard, `knapp`) bzw.
    `urteile-voll.jsonl` (`voll`) an — welcher Modus gilt, steht in `modelle.yaml`
    (`abnahme_protokoll`, siehe `provider.lade_abnahme_protokoll`).

    Frage, Antworttext, Antwort-Status und Belegkarten kommen als versteckte Felder zurück,
    damit der Server zwischen Frage und Urteil nichts merken muss — kein Sitzungszustand,
    kein zweiter Modellaufruf, und ein Neuladen wiederholt die Frage nicht."""
    if urteil not in URTEILE:
        return _zurueck("/abnahme", f"Unbekanntes Urteil: {urteil!r} — nichts geschrieben.")
    try:
        belegkarten = json.loads(karten)
    except json.JSONDecodeError:
        belegkarten = []
    modus = request.app.state.abnahme_protokoll_laden()
    zeile = ansicht.urteilszeile(
        modus,
        zeit=datetime.now().astimezone().isoformat(timespec="seconds"),
        frage=frage,
        antwort_text=antwort,
        antwort_status=antwort_status,
        belegkarten=belegkarten,
        urteil=urteil,
        bemerkung=bemerkung.strip(),
        llm=getattr(werkstatt.provider, "llm_modell", None),
        llm_suche=getattr(werkstatt.provider_suche, "llm_modell", None),
        embedding=getattr(werkstatt.provider, "embed_modell", None),
        reranker=getattr(werkstatt.sucheinstellungen.reranker, "modell_name", None),
        top_n=werkstatt.sucheinstellungen.top_n,
        absaetze_durchsucht=len(werkstatt.index.durchsuchbare_fundstellen()),
    )
    pfad = ansicht.haenge_urteil_an(request.app.state.abnahme_pfad, zeile, modus)
    return _zurueck("/abnahme", f"Urteil „{urteil}“ angehängt an {pfad}.")


# ------------------------------------------------------------------- Fehler


def _fehlerseite(request: Request, fehler: Exception) -> HTMLResponse:
    werkstatt: Werkstatt | None = request.app.state.werkstatt
    return _seite(
        "fehler.html",
        _basis(request, werkstatt, "")
        | {"meldung": str(fehler), "art": type(fehler).__name__},
    )


def _zum_start(request: Request, fehler: Exception) -> RedirectResponse:
    return RedirectResponse("/start", status_code=303)


def create_app(
    werkstatt: Werkstatt | None,
    *,
    modelle: Path = Path("modelle.yaml"),
    zuletzt: Path = ZULETZT_STANDARD,
    abnahme: Path = ABNAHME_STANDARD,
    provider_laden: Callable[[], ModelProvider] | None = None,
    provider_suche_laden: Callable[[], ModelProvider | None] | None = None,
    sucheinstellungen_laden: Callable[[], Sucheinstellungen] | None = None,
    ocr_laden: Callable[[], OcrEinstellungen] | None = None,
    seitenuebergreifend_laden: Callable[[], bool] | None = None,
    abnahme_protokoll_laden: Callable[[], str] | None = None,
) -> FastAPI:
    """Höchstens eine Werkstatt pro Server. Ohne Werkstatt startet alles auf /start;
    `provider_laden` liefert das Modell für einen dort geöffneten Bestand."""
    app = FastAPI(title="Dokumentenassistent", docs_url=None, redoc_url=None)
    app.state.werkstatt = werkstatt
    app.state.job = Job()
    app.state.zuletzt_pfad = zuletzt
    app.state.abnahme_pfad = Path(abnahme)
    app.state.zweck_vorbelegt = ""
    app.state.modelle_pfad = Path(modelle)
    app.state.provider_laden = provider_laden or (lambda: lade_modelle(modelle))
    app.state.provider_suche_laden = provider_suche_laden or (lambda: lade_provider_suche(modelle))
    # Reranker/rerank_k/top_n aus derselben modelle.yaml; Standard = heutiges Verhalten.
    app.state.sucheinstellungen_laden = sucheinstellungen_laden or (lambda: lade_sucheinstellungen(modelle))
    # OCR-Engine aus derselben modelle.yaml. Wie beim Reranker wird beim Oeffnen eines Bestands
    # geladen und dabei geprueft: fehlt das Extra `ocr-paddle`, erscheint der Hinweis auf
    # /start -- kein stiller Rueckfall auf Tesseract.
    app.state.ocr_laden = ocr_laden or (lambda: lade_ocr_einstellungen(modelle))
    app.state.seitenuebergreifend_laden = (
        seitenuebergreifend_laden or (lambda: lade_seitenuebergreifend(modelle)))
    # abnahme_protokoll aus derselben modelle.yaml, erst beim Urteil gelesen (nicht hier eager) --
    # sonst bräuchte jede modelle-lose Route (z. B. /start) trotzdem eine gültige modelle.yaml.
    app.state.abnahme_protokoll_laden = abnahme_protokoll_laden or (lambda: lade_abnahme_protokoll(modelle))
    app.mount("/static", StaticFiles(directory=str(STATISCH)), name="static")
    app.include_router(router)
    app.include_router(modellwahl.router)
    app.include_router(dokument.router)
    app.add_exception_handler(KeineWerkstatt, _zum_start)
    app.add_exception_handler(DokumentenassistentFehler, _fehlerseite)
    app.add_exception_handler(ValueError, _fehlerseite)
    return app


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    zerleger = argparse.ArgumentParser(
        prog="dokumentenassistent", description="Lokaler Dokumentenassistent — Web-Oberfläche"
    )
    zerleger.add_argument("--quelle", type=Path, help="Quellordner, bleibt unverändert (sonst Wahl unter /start)")
    zerleger.add_argument("--ziel", type=Path, help="Zielablage für bestätigte Kopien")
    zerleger.add_argument("--modelle", type=Path, default=Path("modelle.yaml"))
    zerleger.add_argument("--abnahme", type=Path, default=ABNAHME_STANDARD,
                          help="Ordner für die Urteile der Abnahme (append-only, je Tag eine Datei)")
    zerleger.add_argument("--port", type=int, default=8765)
    args = zerleger.parse_args(argv)
    if (args.quelle is None) != (args.ziel is None):
        zerleger.error("--quelle und --ziel gehören zusammen — beide angeben oder beide weglassen")

    werkstatt = None
    if args.quelle is not None:
        werkstatt = Werkstatt(
            quelle=args.quelle,
            zielablage=args.ziel,
            provider=lade_modelle(args.modelle),
            provider_suche=lade_provider_suche(args.modelle),
            sucheinstellungen=lade_sucheinstellungen(args.modelle),
            ocr=lade_ocr_einstellungen(args.modelle),
            seitenuebergreifend=lade_seitenuebergreifend(args.modelle),
        )
        ansicht.merke_zuletzt(ZULETZT_STANDARD, args.quelle, args.ziel)
    app = create_app(werkstatt, modelle=args.modelle, abnahme=args.abnahme)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


__all__ = ["antwort_html", "create_app", "hervorheben", "main", "zeit_lokal"]

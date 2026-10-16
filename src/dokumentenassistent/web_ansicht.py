"""Ansichtsdaten für die Web-Oberfläche: reine Zählerei und Umformung.

Keine Fachlogik — alles hier liest den Index und formt daraus, was eine Vorlage
braucht: Stapelzeilen, Übersicht je Unterordner, Filter, Fortschrittsanzeige,
die Liste „Zuletzt geöffnet". Nichts hier verändert den Bestand.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from dokumentenassistent.typen import Beleg, Datei, Konflikt, Vorschlag
from dokumentenassistent.werkstatt import Werkstatt

QUELLE_SELBST = "(Quelle)"  # Ordnername für Dateien direkt in der Quelle

# Reihenfolge der Übersicht: wartet zuerst, dann die Befunde in Badge-Reihenfolge.
LAGE_STATUS = ("wartet", "sicher", "unklar", "konflikt", "duplikat", "ocr_unsicher")

ZULETZT_MAX = 5


# ----------------------------------------------------------------- Stapelzeilen


def belege_je_fundstelle(vorschlag: Vorschlag | None) -> dict[str, list[str]]:
    """Wortlaute je Fundstellen-ID — damit ein Beleg nur dort markiert wird, wo er herkommt."""
    if vorschlag is None:
        return {}
    je_id: dict[str, list[str]] = {}
    for feld in vorschlag.felder:
        if feld.beleg is None:
            continue
        je_id.setdefault(feld.beleg.fundstelle_id, []).append(feld.beleg.wortlaut)
    return je_id


def _erster_beleg(vorschlag: Vorschlag | None) -> Beleg | None:
    if vorschlag is None:
        return None
    return next((f.beleg for f in vorschlag.felder if f.beleg is not None), None)


def ordner_von(datei: Datei, quelle: Path) -> str:
    """Erste Ordnerebene unterhalb der Quelle; Dateien direkt in der Quelle = „(Quelle)"."""
    try:
        teile = datei.pfad.relative_to(quelle).parts
    except ValueError:
        return QUELLE_SELBST
    return teile[0] if len(teile) > 1 else QUELLE_SELBST


def _relativer_ordner(datei: Datei, quelle: Path) -> str:
    try:
        eltern = datei.pfad.relative_to(quelle).parent
    except ValueError:
        return ""
    return "" if str(eltern) == "." else str(eltern)


def _zeile(werkstatt: Werkstatt, datei: Datei, vorschlag: Vorschlag | None, offen: set[str]) -> dict:
    status = vorschlag.status if vorschlag else (werkstatt.index.status(datei.hash) or "unklar")
    return {
        "datei": datei,
        "vorschlag": vorschlag,
        "status": status if vorschlag or status == "ocr_unsicher" else "wartet",
        "ordner": ordner_von(datei, werkstatt.quelle),
        "relordner": _relativer_ordner(datei, werkstatt.quelle),
        "beleg": _erster_beleg(vorschlag),
        "belege": sum(1 for f in (vorschlag.felder if vorschlag else ()) if f.beleg),
        "zielpfad": werkstatt.index.zielpfad(datei.hash),
        "konflikt_offen": datei.hash in offen,
        "original": None,
    }


def _duplikatzeile(werkstatt: Werkstatt, datei: Datei) -> dict:
    original = werkstatt.index.datei(datei.hash)
    return {
        "datei": datei,
        "vorschlag": None,
        "status": "duplikat",
        "ordner": ordner_von(datei, werkstatt.quelle),
        "relordner": _relativer_ordner(datei, werkstatt.quelle),
        "beleg": None,
        "belege": 0,
        "zielpfad": None,
        "konflikt_offen": False,
        "original": original,
    }


def zeilen(werkstatt: Werkstatt) -> list[dict]:
    """Eine Stapelzeile je Datei in der Quelle — auch Duplikate, damit die Übersicht
    auf die Gesamtzahl kommt. Sortiert nach Pfad wie der Index."""
    vorschlaege = {v.datei_hash: v for v in werkstatt.index.vorschlaege()}
    offen = {h for k in werkstatt.index.konflikte(offen=True) for h in (k.hash_a, k.hash_b)}
    erste = [_zeile(werkstatt, d, vorschlaege.get(d.hash), offen) for d in werkstatt.index.dateien()]
    doppelte = [_duplikatzeile(werkstatt, d) for d in werkstatt.index.duplikate()]
    return sorted(erste + doppelte, key=lambda z: str(z["datei"].pfad))


# ---------------------------------------------------------------- Übersicht


def _verteilung(zeilen_: list[dict]) -> list[dict]:
    """Zahl und Anteil je Status, in LAGE_STATUS-Reihenfolge, nur besetzte."""
    gesamt = len(zeilen_) or 1
    posten = []
    for status in LAGE_STATUS:
        anzahl = sum(1 for z in zeilen_ if z["status"] == status)
        if anzahl:
            posten.append({"status": status, "anzahl": anzahl, "anteil": round(100 * anzahl / gesamt, 2)})
    return posten


def uebersicht(zeilen_: list[dict]) -> dict:
    """Status-Verteilung gesamt und je Unterordner (erste Ebene)."""
    ordner_namen = sorted({z["ordner"] for z in zeilen_}, key=lambda n: (n != QUELLE_SELBST, n.lower()))
    return {
        "gesamt": len(zeilen_),
        "abgearbeitet": sum(1 for z in zeilen_ if z["status"] != "wartet"),
        "verteilung": _verteilung(zeilen_),
        "ordner": [
            {
                "name": name,
                "gesamt": sum(1 for z in zeilen_ if z["ordner"] == name),
                "verteilung": _verteilung([z for z in zeilen_ if z["ordner"] == name]),
            }
            for name in ordner_namen
        ],
    }


# ------------------------------------------------------------------- Filter


@dataclass(frozen=True)
class Filter:
    status: tuple[str, ...] = ()
    ordner: str = ""
    suche: str = ""

    @property
    def aktiv(self) -> bool:
        return bool(self.status or self.ordner or self.suche)

    def passt(self, zeile: dict) -> bool:
        if self.status and zeile["status"] not in self.status:
            return False
        if self.ordner and zeile["ordner"] != self.ordner:
            return False
        return self.suche.lower() in zeile["datei"].name.lower()

    def query(self, **ersetzt: str | tuple[str, ...]) -> str:
        """GET-Parameter dieses Filters, einzelne Werte ersetzt — für Links, die den Filter setzen."""
        werte = {"status": self.status, "ordner": self.ordner, "suche": self.suche} | ersetzt
        paare = [(k, v) for k, v in werte.items() if isinstance(v, str) and v]
        paare += [("status", s) for s in (werte["status"] or ())]
        return "?" + urlencode(paare) if paare else ""


def filter_aus(params) -> Filter:
    """Aus den Query-Parametern; unbekannte Status werden ignoriert."""
    status = tuple(s for s in params.getlist("status") if s in LAGE_STATUS)
    return Filter(status=status, ordner=params.get("ordner", "").strip(), suche=params.get("suche", "").strip())


# ------------------------------------------------------------ Fortschritt


def dauer_text(sekunden: float | None) -> str:
    if sekunden is None:
        return "—"
    ganz = int(round(sekunden))
    if ganz < 60:
        return f"{ganz} s"
    minuten, rest = divmod(ganz, 60)
    return f"{minuten} min {rest:02d} s"


def fortschritt_daten(job, jetzt: float) -> dict:
    """Balken, Zähler, verstrichene und geschätzte Restzeit aus dem Durchschnitt je Datei."""
    verstrichen = jetzt - job.gestartet if job.gestartet else 0.0
    rest = (job.gesamt - job.erledigt) * verstrichen / job.erledigt if job.erledigt else None
    return {
        "anteil": round(100 * job.erledigt / job.gesamt, 1) if job.gesamt else 0,
        "nummer": min(job.erledigt + 1, job.gesamt) if job.gesamt else 0,
        "verstrichen": dauer_text(verstrichen),
        "verstrichen_s": int(verstrichen),
        "rest": dauer_text(rest),
    }


def job_meldung(job) -> str | None:
    """Ein Satz nach dem Ende — oder None, solange nichts zu berichten ist.

    Seit 24.09.2026 gibt es zwei Phasen; die Meldung muss sagen, welche gemeint ist,
    sonst behauptet ein gescheitertes Auslesen, das Einordnen sei abgebrochen."""
    if job.laeuft or job.beendet is None:
        return None
    phase = "Auslesen" if job.phase == "auslesen" else "Einordnen"
    if job.fehler:
        return f"{phase} abgebrochen mit Fehler: {job.fehler}"
    dauer = dauer_text(job.beendet - job.gestartet) if job.gestartet else "—"
    if job.phase == "auslesen":
        return f"{job.neu} Dateien gefunden und ausgelesen in {dauer}."
    if job.abgebrochen:
        return (
            f"Einordnen abgebrochen nach {job.erledigt} von {job.gesamt} Modellaufrufen, "
            f"{job.neu} Vorschläge gespeichert — Wiederaufnahme mit „Stapel einordnen“, "
            "nichts wird doppelt gerechnet."
        )
    return f"{job.neu} Vorschläge erzeugt in {dauer}."


# --------------------------------------------------------------- Zuletzt


def lies_zuletzt(pfad: Path) -> list[dict]:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    return [e for e in daten if isinstance(e, dict) and "quelle" in e and "ziel" in e] if isinstance(daten, list) else []


def merke_zuletzt(pfad: Path, quelle: Path, ziel: Path) -> list[dict]:
    """Neuer Eintrag vorn, gleiche Paare nur einmal, höchstens ZULETZT_MAX."""
    neu = {"quelle": str(quelle), "ziel": str(ziel), "zeit": datetime.now().astimezone().isoformat(timespec="seconds")}
    alte = [e for e in lies_zuletzt(pfad) if (e["quelle"], e["ziel"]) != (neu["quelle"], neu["ziel"])]
    liste = [neu, *alte][:ZULETZT_MAX]
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(liste, ensure_ascii=False, indent=2), encoding="utf-8")
    return liste


# --------------------------------------------------------- Ordnerbrowser


def _normalisiert(pfad_text: str | None) -> Path:
    """Ohne Angabe beginnt der Browser im Heimatverzeichnis; `~` und `..` löst der Server auf."""
    roh = (pfad_text or "").strip()
    return (Path(roh).expanduser() if roh else Path.home()).resolve()


def unterordner(pfad_text: str | None) -> dict:
    """Die Unterordner eines Pfades — nur Namen, nie etwas aus den Dateien.

    Versteckte Ordner (Punkt-Präfix) bleiben draußen, Symlinks werden nicht
    verfolgt. Grenzfälle melden sich als `ValueError` mit lesbarem Satz: fehlt,
    kein Ordner, keine Leseberechtigung — wie `_pruefe_pfade` für die Textfelder.
    """
    pfad = _normalisiert(pfad_text)
    if not pfad.exists():
        raise ValueError(f"Ordner nicht gefunden: {pfad}")
    if not pfad.is_dir():
        raise ValueError(f"Das ist kein Ordner: {pfad}")
    try:
        gefunden = sorted(
            (e for e in pfad.iterdir()
             if not e.name.startswith(".") and not e.is_symlink() and e.is_dir()),
            key=lambda e: e.name.casefold(),
        )
    except PermissionError:
        raise ValueError(f"Keine Leseberechtigung für: {pfad}") from None
    return {
        "pfad": str(pfad),
        # Die Wurzel ist ihr eigener Elternteil — dort endet der Weg nach oben.
        "eltern": None if pfad.parent == pfad else str(pfad.parent),
        "ordner": [{"name": e.name, "pfad": str(e)} for e in gefunden],
    }


# --------------------------------------------------------------- Abnahme

URTEILE_LETZTE = 10

# Dateiname je Modus statt eines Schalters in derselben Datei: der Schutz vor Klartext im
# `voll`-Protokoll wird damit MECHANISCH (eine .gitignore-Zeile auf einen festen Dateinamen)
# statt disziplinarisch (jemand müsste an ein Feld denken). Siehe .gitignore und
# beweise/abnahme/README.md.
_DATEINAME_JE_MODUS = {"knapp": "urteile.jsonl", "voll": "urteile-voll.jsonl"}


def _hash16(text: str) -> str:
    """sha256, erste 16 Hex-Zeichen — kurz genug für eine Protokollzeile, lang genug,
    dass zwei verschiedene Texte in der Praxis nie denselben Hash tragen."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def urteilszeile(
    modus: str,
    *,
    zeit: str,
    frage: str,
    antwort_text: str,
    antwort_status: str,
    belegkarten: list[dict],
    urteil: str,
    bemerkung: str,
    llm: str | None,
    llm_suche: str | None,
    embedding: str | None,
    reranker: str | None,
    top_n: int | None,
    absaetze_durchsucht: int,
) -> dict:
    """Eine Zeile für `urteile.jsonl` (`knapp`, Standard) oder `urteile-voll.jsonl` (`voll`).

    Anlass (23.09.2026): der Auftraggeber will die Abnahme-Ansicht mit ECHTEN, teils
    vertraulichen Dokumenten benutzen. Das Protokoll liegt im Projektordner unter Git — ein
    unbedachtes `git add` hätte fremden Dokumentinhalt im Repository, schriebe eine Zeile
    Frage, Antworttext und Belegwortlaut im Klartext. `knapp` belegt deshalb nur das URTEIL
    (Hashes/Längen/Kennzahlen), nie den Inhalt; `voll` schreibt wie vor dieser Änderung, für
    den synthetischen Korpus, wo Inhalt unkritisch und zur Fehlersuche nützlich ist.

    Auch die Fundstellen-ID einer Belegkarte (`datei#S..#A..`) trägt den Dateinamen und damit
    schon Inhalt — im knappen Modus wird deshalb NICHT `karten_ids` (reine IDs) geschrieben,
    sondern `karten_ids_hash` (jede ID gehasht). Wer das hier zu `karten_ids` "vereinfacht",
    holt die Klartext-Dateinamen zurück in ein Protokoll, das inhaltsfrei sein soll.
    """
    if modus not in _DATEINAME_JE_MODUS:
        raise ValueError(f"Unbekannter abnahme_protokoll-Modus: {modus!r}")
    zeile = {
        "zeit": zeit,
        "status": antwort_status,
        "karten_anzahl": len(belegkarten),
        "urteil": urteil,
        "llm": llm,
        "llm_suche": llm_suche,
        "embedding": embedding,
        "reranker": reranker,
        "top_n": top_n,
        "absaetze_durchsucht": absaetze_durchsucht,
    }
    if modus == "voll":
        zeile |= {
            "frage": frage,
            "antwort": antwort_text,
            "belegkarten": belegkarten,
            "bemerkung": bemerkung,
        }
    else:
        zeile |= {
            "frage_hash": _hash16(frage),
            "frage_zeichen": len(frage),
            "antwort_hash": _hash16(antwort_text),
            "antwort_zeichen": len(antwort_text),
            "karten_ids_hash": [_hash16(k["id"]) for k in belegkarten],
            "bemerkung_zeichen": len(bemerkung),
        }
    return zeile


def urteilspfad(ordner: Path, modus: str = "knapp") -> Path:
    """`<ordner>/<datum>/urteile.jsonl` (`knapp`) bzw. `.../urteile-voll.jsonl` (`voll`) —
    ein Tag, eine Datei je Modus, append-only."""
    dateiname = _DATEINAME_JE_MODUS.get(modus, _DATEINAME_JE_MODUS["knapp"])
    return Path(ordner) / datetime.now().astimezone().date().isoformat() / dateiname


def haenge_urteil_an(ordner: Path, zeile: dict, modus: str = "knapp") -> Path:
    """Anhängen, nie überschreiben: ein Urteil des Auftraggebers ist ein Messwert,
    kein Zustand. Auch ein späteres, anderes Urteil zur selben Frage löscht das frühere nicht."""
    pfad = urteilspfad(ordner, modus)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    return pfad


def lies_urteile(ordner: Path) -> list[dict]:
    """Alle Urteile aller Tage und beider Protokoll-Dateien, je Datei in Schreibreihenfolge
    (zwischen den beiden Dateien eines Tages nur alphabetisch, nicht zeitlich sortiert — das
    genügt für Zähler und die „letzten N", eine exakte Gesamtreihenfolge braucht niemand).
    Kaputte Zeilen werden übersprungen, damit eine unvollständige letzte Zeile die Seite
    nicht zerlegt."""
    urteile: list[dict] = []
    for pfad in sorted(Path(ordner).glob("*/urteile*.jsonl")):
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            if not zeile.strip():
                continue
            try:
                urteile.append(json.loads(zeile))
            except json.JSONDecodeError:
                continue
    return urteile


def abnahme_daten(ordner: Path) -> dict:
    """Zähler und die letzten `URTEILE_LETZTE`, neueste zuerst."""
    urteile = lies_urteile(ordner)
    return {
        "urteile": list(reversed(urteile[-URTEILE_LETZTE:])),
        "urteile_gesamt": len(urteile),
        "urteile_richtig": sum(1 for u in urteile if u.get("urteil") == "richtig"),
        "urteile_falsch": sum(1 for u in urteile if u.get("urteil") == "falsch"),
        "urteile_pfad": f"{urteilspfad(ordner, 'knapp')} (Standard) bzw. "
        f"{urteilspfad(ordner, 'voll').name} (voll)",
    }


# ------------------------------------------------------------ Bestand u. a.


def konfliktkarte(werkstatt: Werkstatt, konflikt: Konflikt) -> dict:
    return {
        "konflikt": konflikt,
        "name_a": _dateiname(werkstatt, konflikt.hash_a),
        "name_b": _dateiname(werkstatt, konflikt.hash_b),
        "fundstelle_a": werkstatt.index.fundstelle(konflikt.beleg_a.fundstelle_id),
        "fundstelle_b": werkstatt.index.fundstelle(konflikt.beleg_b.fundstelle_id),
    }


def _dateiname(werkstatt: Werkstatt, hash_: str) -> str:
    datei = werkstatt.index.datei(hash_)
    return datei.name if datei else hash_[:12]


def konfliktkarten(werkstatt: Werkstatt, offen: bool | None = True) -> list[dict]:
    return [konfliktkarte(werkstatt, k) for k in werkstatt.index.konflikte(offen=offen)]


def ablage(werkstatt: Werkstatt) -> list[dict]:
    """Bestätigte Zielkopien, gruppiert nach Kategorie."""
    nach_kategorie: dict[str, list[dict]] = {}
    for vorschlag in werkstatt.index.vorschlaege():
        zielpfad = werkstatt.index.zielpfad(vorschlag.datei_hash)
        if zielpfad is None:
            continue
        eintrag = {"vorschlag": vorschlag, "zielpfad": zielpfad}
        nach_kategorie.setdefault(vorschlag.kategorie or "ohne Kategorie", []).append(eintrag)
    return [
        {"kategorie": kategorie, "dateien": sorted(dateien, key=lambda e: e["zielpfad"].name)}
        for kategorie, dateien in sorted(nach_kategorie.items())
    ]


def duplikate(werkstatt: Werkstatt) -> list[dict]:
    return [
        {"duplikat": d, "original": werkstatt.index.datei(d.hash)}
        for d in werkstatt.index.duplikate()
    ]


def profil_daten(werkstatt: Werkstatt) -> dict:
    dateien = werkstatt.index.dateien()
    return {
        "dateien": dateien,
        "anzahl_dateien": len(dateien),
        "anzahl_duplikate": len(werkstatt.index.duplikate()),
        "anzahl_fundstellen": sum(len(werkstatt.index.fundstellen(d.hash)) for d in dateien),
    }


__all__ = [
    "LAGE_STATUS",
    "QUELLE_SELBST",
    "Filter",
    "ablage",
    "abnahme_daten",
    "belege_je_fundstelle",
    "dauer_text",
    "duplikate",
    "filter_aus",
    "fortschritt_daten",
    "haenge_urteil_an",
    "job_meldung",
    "konfliktkarte",
    "konfliktkarten",
    "lies_urteile",
    "lies_zuletzt",
    "merke_zuletzt",
    "ordner_von",
    "profil_daten",
    "uebersicht",
    "unterordner",
    "urteilspfad",
    "urteilszeile",
    "zeilen",
]

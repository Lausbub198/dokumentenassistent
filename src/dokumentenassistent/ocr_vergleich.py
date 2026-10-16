"""OCR-Vergleich: Tesseract (= heutiger Produktpfad) gegen die portablen Alternativen, gemessen
an echten deutschen Dokumenten — ohne dass jemand etwas von Hand beurteilen muss.

Aenderung der Anforderung am 23.09.2026: Messlatte statt Kandidat
----------------------------------------------------------------
Apple Vision hat die erste Messung gewonnen (F1 Wort paarweise 105:43, Zahlentreue 91,7 gegen
83,6 %, Faktor 4,7 schneller). Es laeuft aber nur auf macOS, und gefordert ist eine Loesung
fuer **alle** Rechner. `vision` und `vision_korrektur` bleiben deshalb in der Tabelle, aber
als **Messlatte** — was auf dieser Hardware erreichbar waere —, nicht als Kandidat. Die offene
Frage lautet seither: ist `tesseract` die beste **portable** Engine? Dagegen treten
`tesseract_vorverarbeitet` (dieselbe Engine mit `ocr_vorverarbeitung.vorverarbeite`),
`paddleocr` und `easyocr` an; jede haengt an einer eigenen Abhaengigkeitsgruppe und wird bei
fehlender Installation laut uebersprungen (`pruefe_engines`), nie stillschweigend.

Warum das ohne Handarbeit geht
------------------------------
Ein Teil der PDFs im Korpus **hat eine Textebene**, vom Erzeuger gesetzt und damit korrekt.
Rendert man genau diese Seiten zu Bildern, schickt sie durch die OCR und vergleicht das
Ergebnis mit der eingebetteten Textebene, ist die Textebene die **Wahrheit** und die Differenz
die Fehlerrate der OCR. Die Dateien **ohne** Textebene (die, die im Produkt tatsaechlich an der
OCR haengen) liefern keine Wahrheit; sie dienen nur als Laufzeit- und Plausibilitaetsprobe
(`--ohne-textebene N`: kommt ueberhaupt Text heraus, und wie lange dauert es).

Entscheidungsregel — **vor** der Messung festgelegt, am 23.09.2026 repariert
----------------------------------------------------------------------------
Eine Engine wird empfohlen, wenn sie gegenueber `tesseract`

1. **F1 ueber die Wort-Multimenge und F1 ueber die Zeichen-Trigramm-Multimenge haelt oder
   verbessert** (Median ueber die Seiten), **und**
2. die **Zahlentreue nicht verschlechtert** (`zahlen_verfehlt` + `daten_verfehlt` nicht hoeher).

Bis zum 23.09.2026 stand in Punkt 1 "CER und WER senkt". Das war falsch — nicht ungenau,
sondern an der falschen Groesse gemessen: die Editierdistanz zaehlt eine abweichende
**Lesereihenfolge** als Lesefehler (siehe "Gemessene Grenze der Wahrheit"), und auf einem
Drittel der Seiten dominierte genau das die Kennzahl. CER und WER bleiben im Bericht als
Nebenkennzahlen stehen, weil sie Zeichenfehler *innerhalb* einer Zeile fein aufloesen —
aber sie koennen die Leitkennzahl nicht sein, solange sie Layout mitmessen.

**`zahlen_erfunden` (bzw. `daten_erfunden`) ist ein Ausschlusskriterium**, unabhaengig von CER:
Dieser Assistent antwortet mit Zitatpflicht und wird nach Betraegen und Fristen gefragt. Eine
Engine, die eine Zahl erfindet, die auf dem Papier nie stand, erzeugt ein falsches Zitat —
das ist schlimmer als eine Engine, die die Zahl gar nicht liest. Deshalb wird
`usesLanguageCorrection` bei Vision **ausgeschaltet** gemessen (`vision`) und zusaetzlich
**eingeschaltet** (`vision_korrektur`): die Sprachkorrektur "repariert" Text anhand eines
Sprachmodells und ist genau der Mechanismus, der Zahlen und Namen erfinden kann. Die Messung
macht diesen Unterschied sichtbar, statt ihn zu vermuten.

Fairness der Normalisierung
---------------------------
Vor jedem Vergleich laufen Referenz und OCR-Text durch **dieselbe** Funktion `normalisiere`
(Unicode-NFKC, vereinheitlichte Anfuehrungszeichen und Striche, gefalteter Leerraum). Sie kennt
die Herkunft des Textes nicht und kann deshalb keine Engine bevorzugen; sie entfernt nur
Unterschiede, die keine Lesefehler sind (Ligatur `ﬁ` gegen `fi`, harte Zeilenumbrueche,
typografische gegen gerade Anfuehrungszeichen).

Gemessene Grenze der Wahrheit (Lauf 23.09.2026, 150 Seiten)
-----------------------------------------------------------
Auf **51 von 144** Seiten liegt die CER ueber 0,3 — und zwar bei allen drei Engines zugleich,
nicht bei einer allein. Die OCR liefert dort **gleich viel** Text wie die Referenz
(Median-Verhaeltnis Zeichen OCR/Referenz: 1,0, in beiden Gruppen gleich), es fehlt also nichts
und nichts ist doppelt: die **Reihenfolge** unterscheidet sich. Bei mehrspaltigen Seiten und
Tabellen liest die eingebettete Textebene in einer anderen Folge als die OCR, und die
Editierdistanz zaehlt das als Fehler, obwohl jedes Zeichen richtig gelesen wurde. Die
absoluten CER-Werte sind deshalb eine **Obergrenze**, kein Lesefehleranteil. Der *Vergleich*
der Engines bleibt gueltig — alle drei lesen dieselben Seiten gegen dieselbe Referenz.

Dagegen messen `wortmengen_kennzahlen` und `zeichen_ngramm_kennzahlen` (seit 23.09.2026)
reihenfolge-unabhaengig: sie vergleichen Multimengen, nicht Positionen. Der Bericht weist
beides getrennt aus, einmal ueber alle Seiten und einmal ueber die **tragfaehige Teilmenge**
(alle Engines CER <= 0,3) — dort, und nur dort, trug die alte Kennzahl.

Aus demselben Grund ist `zahlen_erfunden` hier **kein reiner Halluzinationszaehler**: auch die
heutige Produkt-Engine kommt auf einen dreistelligen Wert, was gegen Erfindung und fuer eine
stellenweise unvollstaendige Referenz spricht (Zahlen in Kopfzeilen, Stempeln oder
Bildbereichen, die die Textebene nicht fuehrt). Als Ausschlusskriterium taugt die Zahl hier
nur im **Vergleich** der Engines untereinander, nicht als absoluter Wert.

Messkommandos
-------------
    uv sync --extra ocr --extra ocr-paddle --extra ocr-easy
    uv run --extra ocr-paddle --extra ocr-easy python -m dokumentenassistent.ocr_vergleich \\
        --korpus <ordner> --seiten 150 --seed 42 \\
        --engines tesseract_vorverarbeitet paddleocr easyocr \\
        --uebernehmen beweise/ocr-reihenfolge/<datum>/laeufe.jsonl \\
        --uebernehmen-engines tesseract vision vision_korrektur
    uv run --extra ocr-paddle --extra ocr-easy python -m dokumentenassistent.ocr_vergleich \\
        --korpus <ordner> --ohne-textebene 10 --engines tesseract paddleocr easyocr
    uv run python -m dokumentenassistent.ocr_vergleich --bericht beweise/ocr/<datum>/

`--uebernehmen` traegt die Seitenzeilen eines frueheren Laufs mit, statt dieselben Engines
ueber dieselben 150 Seiten erneut zu schicken. Das ist nur zulaessig, weil die Stichprobe
deterministisch ist (Seed, Seitenzahl, dpi, `min_zeichen`, Korpus) — und es wird geprueft:
jedes Paar, das im alten Lauf fehlt, ist eine laute Warnung, keine stille Luecke.

Datenschutz: in Bericht und JSONL steht **kein Dokumentinhalt** — nur Dateiname, Seitenzahl
und Kennzahlen.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from .ocr_bericht import (  # noqa: F401 - Teil der oeffentlichen Flaeche des Vergleichs
    fasse_zusammen,
    kennzahlen,
    paarweise,
    schreibe_bericht,
    tragfaehige_seiten,
)
from .ocr_kennzahlen import (  # noqa: F401 - Teil der oeffentlichen Flaeche des Vergleichs
    cer,
    datumsangaben,
    levenshtein,
    normalisiere,
    wer,
    wortmengen_kennzahlen,
    zahlen,
    zahlentreue,
    zeichen_ngramm_kennzahlen,
)
from .ocr_vorverarbeitung import (  # noqa: F401 - Teil der API
    schaetze_neigung,
    vorverarbeite,
)
from .typen import DokumentenassistentFehler

PDFTOPPM = "/opt/homebrew/bin/pdftoppm"
OCR_SPRACHE = "deu"  # identisch zu auslesen.py, damit die Zahl auf den Assistenten passt
VISION_SPRACHEN = ["de-DE"]
STANDARD_DPI = 300
STANDARD_SEITEN = 150
STANDARD_SEED = 42
# Seiten unter dieser Laenge sind Deckblaetter, Stempel- oder Bildseiten: dort ist die
# eingebettete Textebene kein belastbarer Massstab (oft nur eine Kopfzeile, waehrend das Bild
# viel mehr zeigt), und ein einzelner Lesefehler wuerde die CER dominieren. 200 Zeichen sind
# etwa ein Absatz Flietext — ab da traegt die Seite genug Text, um eine Fehlerrate zu stuetzen.
MIN_ZEICHEN = 200


class OcrVergleichFehler(DokumentenassistentFehler):
    """Korpus fehlt, Renderer fehlt, oder eine Engine ist nicht verfuegbar."""


# =================================================================== Stichprobe


def stichprobe(
    kandidaten: Sequence[tuple[str, int]], anzahl: int, seed: int
) -> tuple[tuple[str, int], ...]:
    """Deterministische Auswahl von hoechstens `anzahl` Seiten, reihum ueber die Dateien.

    Reihum, damit eine Stichprobe von 150 Seiten nicht aus drei dicken Dateien kommt und
    der Befund damit an drei Dokumententypen haengt. `seed` macht den Lauf wiederholbar.
    """
    wuerfel = random.Random(seed)
    je_datei: dict[str, list[tuple[str, int]]] = {}
    for eintrag in kandidaten:
        je_datei.setdefault(eintrag[0], []).append(eintrag)
    reihenfolge = sorted(je_datei)
    wuerfel.shuffle(reihenfolge)
    for name in reihenfolge:
        wuerfel.shuffle(je_datei[name])
    auswahl: list[tuple[str, int]] = []
    runde = 0
    while len(auswahl) < anzahl:
        nachschub = [je_datei[name][runde] for name in reihenfolge if runde < len(je_datei[name])]
        if not nachschub:
            break
        auswahl.extend(nachschub[: anzahl - len(auswahl)])
        runde += 1
    return tuple(auswahl)



# =================================================================== Korpus und Rendern


def textebenen(pfad: Path) -> dict[int, str]:
    """Seitennummer -> eingebetteter Text (wie `auslesen._lies_pdf`, ohne OCR-Zweig)."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        seiten = PdfReader(str(pfad)).pages
        return {
            nummer: (seite.extract_text() or "").strip()
            for nummer, seite in enumerate(seiten, start=1)
        }
    except (PdfReadError, OSError, ValueError, KeyError):
        return {}


def sammle_korpus(korpus: Path, min_zeichen: int) -> tuple[dict[tuple[str, int], str], dict[Path, int]]:
    """(Referenzseiten, PDFs ohne Textebene -> Seitenzahl).

    Referenzseiten sind Seiten mit eingebettetem Text ab `min_zeichen` Zeichen (normalisiert).
    Ein PDF gilt als "ohne Textebene", wenn keine seiner Seiten Text liefert; seine Seitenzahl
    wird mitgefuehrt, damit die Laufzeitprobe nicht nur Deckblaetter misst.
    """
    referenzen: dict[tuple[str, int], str] = {}
    ohne: dict[Path, int] = {}
    for pfad in sorted(korpus.rglob("*")):
        if pfad.suffix.lower() != ".pdf" or not pfad.is_file():
            continue
        seiten = textebenen(pfad)
        if not any(seiten.values()):
            ohne[pfad] = len(seiten)
            continue
        for nummer, text in seiten.items():
            if len(normalisiere(text)) >= min_zeichen:
                referenzen[(str(pfad), nummer)] = text
    return referenzen, ohne


def rendere(pdf: Path, seite: int, dpi: int, ziel: Path) -> tuple[Path, float]:
    """Eine PDF-Seite als PNG; gibt (Bildpfad, Dauer in Sekunden) zurueck."""
    praefix = ziel / f"seite-{seite}"
    start = time.perf_counter()
    lauf = subprocess.run(
        [PDFTOPPM, "-r", str(dpi), "-f", str(seite), "-l", str(seite), "-png", "-singlefile",
         str(pdf), str(praefix)],
        capture_output=True,
        check=False,  # Rueckgabewert wird unten selbst geprueft, mit Datei- und Seitenangabe
    )
    dauer = time.perf_counter() - start
    bild = praefix.with_suffix(".png")
    if lauf.returncode != 0 or not bild.exists():
        raise OcrVergleichFehler(f"pdftoppm fehlgeschlagen: {pdf.name} Seite {seite}")
    return bild, dauer


# ========================================================================== Engines


def tesseract_text(bild: Path) -> str:
    """Genau wie das Produkt (`auslesen._ocr_bilder`): pytesseract, lang='deu'."""
    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(bild), lang=OCR_SPRACHE).strip()


def _vision_module():
    try:
        import Quartz
        import Vision
        from Foundation import NSURL
    except ImportError as fehler:  # pragma: no cover - haengt an der Installation
        raise OcrVergleichFehler(
            "Apple Vision fehlt. Nachinstallieren ueber die Extra-Gruppe: "
            "uv run --extra ocr python -m dokumentenassistent.ocr_vergleich ... "
            f"(Importfehler: {fehler})"
        ) from fehler
    return Quartz, Vision, NSURL


def vision_text(bild: Path, *, korrektur: bool) -> str:
    """Apple Vision (`VNRecognizeTextRequest`), Sprache de-DE, Stufe `accurate`.

    `korrektur=False` schaltet `usesLanguageCorrection` ab — siehe Modul-Docstring: eine
    Engine, die Text anhand eines Sprachmodells repariert, kann Zitate erzeugen, die auf dem
    Papier nie standen. Beide Varianten werden gemessen.
    """
    Quartz, Vision, NSURL = _vision_module()
    quelle = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(bild)), None)
    if quelle is None:
        raise OcrVergleichFehler(f"Vision kann das Bild nicht oeffnen: {bild.name}")
    cg_bild = Quartz.CGImageSourceCreateImageAtIndex(quelle, 0, None)
    anfrage = Vision.VNRecognizeTextRequest.alloc().init()
    anfrage.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    anfrage.setRecognitionLanguages_(VISION_SPRACHEN)
    anfrage.setUsesLanguageCorrection_(korrektur)
    bearbeiter = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_bild, None)
    erfolg, fehler = bearbeiter.performRequests_error_([anfrage], None)
    if not erfolg:
        raise OcrVergleichFehler(f"Vision-Anfrage fehlgeschlagen: {bild.name} ({fehler})")
    zeilen = [
        beobachtung.topCandidates_(1)[0].string()
        for beobachtung in (anfrage.results() or [])
        if beobachtung.topCandidates_(1)
    ]
    return "\n".join(zeilen).strip()


# ------------------------------------------------- portable Engines (ab 23.09.2026)
#
# Anlass: Apple Vision hat die Messung vom 23.09. gewonnen, ist aber macOS-only. Gefordert
# ist eine Loesung, die auf allen Rechnern laeuft — Vision bleibt nur noch als Messlatte
# in der Tabelle. Die offene Frage "ist Tesseract die beste portable Engine?" war
# ungemessen; diese drei Engines haengen sie in denselben Messstand.


def tesseract_vorverarbeitet_text(bild: Path) -> str:
    """Dieselbe Tesseract-Engine, aber mit `vorverarbeite` vor der Erkennung.

    Der Unterschied zu `tesseract` ist damit **genau eine** Zeile — jede Abweichung in den
    Kennzahlen kommt aus der Vorverarbeitung und aus nichts anderem.
    """
    import pytesseract
    from PIL import Image

    with Image.open(bild) as roh:
        aufbereitet = vorverarbeite(roh)
    return pytesseract.image_to_string(aufbereitet, lang=OCR_SPRACHE).strip()


_MODELLE: dict[str, object] = {}  # geladene Modelle je Engine — Ladezeit faellt einmal an


def _fehlende_gruppe(engine: str, gruppe: str, fehler: Exception) -> OcrVergleichFehler:
    return OcrVergleichFehler(
        f"Engine '{engine}' braucht die Abhaengigkeitsgruppe '{gruppe}'. Nachinstallieren: "
        f"uv sync --extra {gruppe}  (Importfehler: {type(fehler).__name__}: {fehler})"
    )


def _paddle_leser():
    if "paddleocr" not in _MODELLE:
        try:
            from paddleocr import PaddleOCR
        except ImportError as fehler:
            raise _fehlende_gruppe("paddleocr", "ocr-paddle", fehler) from fehler
        _MODELLE["paddleocr"] = PaddleOCR(
            lang="german",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _MODELLE["paddleocr"]


def paddleocr_text(bild: Path) -> str:
    """PaddleOCR mit dem deutschen Erkennungsmodell, CPU.

    Die drei Vorstufen (Seitenorientierung, Entzerrung, Zeilenorientierung) sind **aus**:
    sie kosten Laufzeit und wuerden der Engine eine Vorverarbeitung geben, die `tesseract`
    nicht hat — der Vergleich soll die Erkennung messen, nicht ungleiche Vorstufen.
    """
    ergebnis = _paddle_leser().predict(str(bild))
    zeilen = [
        text
        for block in (ergebnis or [])
        for text in (block.get("rec_texts") or ())
    ]
    return "\n".join(zeilen).strip()


def _easyocr_leser():
    if "easyocr" not in _MODELLE:
        try:
            import easyocr
        except ImportError as fehler:
            raise _fehlende_gruppe("easyocr", "ocr-easy", fehler) from fehler
        _MODELLE["easyocr"] = easyocr.Reader(["de"], gpu=False, verbose=False)
    return _MODELLE["easyocr"]


def easyocr_text(bild: Path) -> str:
    """EasyOCR, deutsches Modell, CPU. `paragraph=False` — keine Nachgruppierung von Zeilen."""
    zeilen = _easyocr_leser().readtext(str(bild), detail=0, paragraph=False)
    return "\n".join(zeilen).strip()


ENGINES = {
    "tesseract": tesseract_text,
    "tesseract_vorverarbeitet": tesseract_vorverarbeitet_text,
    "paddleocr": paddleocr_text,
    "easyocr": easyocr_text,
    "vision": lambda bild: vision_text(bild, korrektur=False),
    "vision_korrektur": lambda bild: vision_text(bild, korrektur=True),
}

# Verfuegbarkeitsprobe je Engine: laeuft **vor** dem Lauf, damit eine fehlende
# Abhaengigkeitsgruppe eine Meldung ist und nicht 150 Fehlerzeilen. Engines ohne Eintrag
# (tesseract, tesseract_vorverarbeitet) haengen nur an Produkt-Abhaengigkeiten.
ENGINE_PRUEFUNG = {
    "vision": _vision_module,
    "vision_korrektur": _vision_module,
    "paddleocr": _paddle_leser,
    "easyocr": _easyocr_leser,
}


def pruefe_engines(namen: Sequence[str]) -> tuple[str, ...]:
    """Unbekannte Namen sind ein Abbruch; nicht verfuegbare Engines werden laut uebersprungen."""
    unbekannt = [name for name in namen if name not in ENGINES]
    if unbekannt:
        raise OcrVergleichFehler(f"Unbekannte Engine(s): {', '.join(unbekannt)}")
    verfuegbar = []
    for name in namen:
        pruefung = ENGINE_PRUEFUNG.get(name)
        if pruefung is not None:
            try:
                pruefung()
            except OcrVergleichFehler as fehler:
                print(f"[uebersprungen] Engine '{name}': {fehler}", file=sys.stderr)
                continue
        verfuegbar.append(name)
    return tuple(verfuegbar)


# ============================================================================ Lauf


class Protokoll:
    """Append-only JSONL, **sofort** geschrieben und geflusht — ein abgebrochener Lauf
    behaelt jede bis dahin gemessene Seite."""

    def __init__(self, pfad: Path) -> None:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        self._datei = pfad.open("a", encoding="utf-8")

    def schreibe(self, zeile: dict) -> None:
        self._datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        self._datei.flush()

    def schliesse(self) -> None:
        self._datei.close()


def bereits_gemessen(zeilen: Sequence[dict]) -> set[tuple[str, int]] | set:
    """(Engine, Dateiname, Seite) aller Messungen, die in diesem Protokoll schon stehen.

    **Uebernommene** Zeilen zaehlen nicht mit: sie stammen aus einem anderen Lauf, und ob
    dort etwas uebernommen wurde, darf nicht entscheiden, was hier noch zu messen ist.
    """
    return {
        (zeile["engine"], zeile["datei"], zeile["seite"])
        for zeile in zeilen
        if zeile.get("art") == "seite" and not zeile.get("uebernommen")
    }


def messe_seiten(
    seiten: Sequence[tuple[Path, int, str | None]],
    engines: Sequence[str],
    dpi: int,
    protokoll: Protokoll,
    erledigt: set = frozenset(),
) -> list[dict]:
    """Rendert jede Seite einmal und laesst alle Engines darauf laufen.

    `text` ist die Referenz oder `None` (Seiten ohne Textebene: nur Laufzeit und Textmenge).
    Jede Zeile geht sofort ins Protokoll.

    `erledigt` enthaelt (Engine, Dateiname, Seite) bereits gemessener Kombinationen. Eine
    Seite, fuer die keine Engine mehr offen ist, wird gar nicht erst gerendert — ein
    abgebrochener Lauf (hier: nach 100 von 150 Seiten) laesst sich damit fortsetzen, statt
    zwei Stunden Messung zu wiederholen oder dieselbe Seite doppelt in die Mediane zu legen.
    """
    zeilen: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        for pdf, nummer, referenz in seiten:
            offen = [e for e in engines if (e, pdf.name, nummer) not in erledigt]
            if not offen:
                continue
            try:
                bild, render_sekunden = rendere(pdf, nummer, dpi, Path(tmp))
            except OcrVergleichFehler as fehler:
                protokoll.schreibe({"art": "fehler", "datei": pdf.name, "seite": nummer,
                                    "meldung": str(fehler)})
                continue
            for engine in offen:
                zeile = _messe_eine(engine, bild, pdf, nummer, referenz, render_sekunden)
                protokoll.schreibe(zeile)
                zeilen.append(zeile)
            bild.unlink(missing_ok=True)
    return zeilen


def _messe_eine(
    engine: str, bild: Path, pdf: Path, nummer: int, referenz: str | None, render_sekunden: float
) -> dict:
    zeile = {"art": "seite", "engine": engine, "datei": pdf.name, "seite": nummer,
             "render_sekunden": round(render_sekunden, 3)}
    start = time.perf_counter()
    try:
        text = ENGINES[engine](bild)
    except Exception as fehler:  # noqa: BLE001 - jede Engine darf scheitern, nie stillschweigend
        zeile.update({"art": "fehler", "ocr_sekunden": round(time.perf_counter() - start, 3),
                      "meldung": f"{type(fehler).__name__}: {fehler}"})
        return zeile
    zeile["ocr_sekunden"] = round(time.perf_counter() - start, 3)
    zeile["zeichen_ocr"] = len(normalisiere(text))
    if referenz is None:
        zeile["art"] = "laufzeitprobe"
        return zeile
    zeile["zeichen_referenz"] = len(normalisiere(referenz))
    zeile["cer"] = cer(referenz, text)
    zeile["wer"] = wer(referenz, text)
    zeile.update(wortmengen_kennzahlen(referenz, text))
    zeile.update(zeichen_ngramm_kennzahlen(referenz, text))
    zeile.update(zahlentreue(referenz, text))
    return zeile

def uebernommene_zeilen(
    alt: Sequence[dict], seiten: Sequence[tuple[str, int]], engines: Sequence[str]
) -> tuple[list[dict], tuple[tuple[str, str, int], ...]]:
    """Seitenzeilen eines frueheren Laufs fuer genau die jetzt gemessenen Seiten.

    Damit bleibt die Tabelle vergleichbar, ohne `tesseract`, `vision` und `vision_korrektur`
    erneut ueber 150 Seiten zu schicken. Uebernommen wird **nur**, was zur aktuellen
    Stichprobe passt (gleiche Datei, gleiche Seite); jedes fehlende Paar wird zurueckgegeben
    statt verschwiegen — eine lueckenhafte Uebernahme wuerde die paarweisen Zaehlungen
    stillschweigend auf weniger Seiten stellen.

    Verglichen wird ueber den **Dateinamen**, nicht ueber den Pfad: das Protokoll fuehrt seit
    jeher `pdf.name` (damit im Beweis kein Ordnerbaum steht), die Stichprobe dagegen den
    vollen Pfad. Der erste Versuch verglich Pfade und uebernahm daher nichts — 0 Zeilen,
    450 fehlend. Die Warnung hat es gefangen; ohne sie waere der Bericht einfach ohne
    Vergleichsengines erschienen.
    """
    gesucht = {(Path(datei).name, nummer) for datei, nummer in seiten}
    vorhanden = {
        (zeile["engine"], zeile["datei"], zeile["seite"]): zeile
        for zeile in alt
        if zeile.get("art") == "seite" and zeile.get("engine") in set(engines)
    }
    zeilen: list[dict] = []
    fehlend: list[tuple[str, str, int]] = []
    for engine in engines:
        for datei, nummer in sorted(gesucht):
            treffer = vorhanden.get((engine, datei, nummer))
            if treffer is None:
                fehlend.append((engine, datei, nummer))
            else:
                zeilen.append({**treffer, "uebernommen": True})
    return zeilen, tuple(fehlend)




# ============================================================================== CLI


def _argumente(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--korpus", type=Path)
    parser.add_argument("--seiten", type=int, default=STANDARD_SEITEN)
    parser.add_argument("--engines", nargs="+", default=["tesseract", "vision"])
    parser.add_argument("--dpi", type=int, default=STANDARD_DPI)
    parser.add_argument("--min-zeichen", type=int, default=MIN_ZEICHEN)
    parser.add_argument("--seed", type=int, default=STANDARD_SEED)
    parser.add_argument("--ausgabe", type=Path, default=Path("beweise/ocr"))
    parser.add_argument("--ohne-textebene", type=int, default=0,
                        help="Laufzeitprobe: N Seiten aus PDFs ohne Textebene (keine Wahrheit)")
    parser.add_argument("--bericht", type=Path, help="Nur Bericht aus vorhandener laeufe.jsonl bauen")
    parser.add_argument("--uebernehmen", type=Path,
                        help="laeufe.jsonl eines frueheren Laufs: dessen Seitenzeilen fuer "
                             "--uebernehmen-engines werden mitgefuehrt statt neu gemessen")
    parser.add_argument("--uebernehmen-engines", nargs="+", default=[],
                        help="Engines, deren Messung aus --uebernehmen kommt")
    parser.add_argument("--fortsetzen", action="store_true",
                        help="Bereits im Zielordner protokollierte (Engine, Datei, Seite) "
                             "ueberspringen statt erneut zu messen")
    return parser.parse_args(argv)


def _erledigt(args, ordner: Path) -> tuple[set, bool]:
    """Was in diesem Zielordner schon gemessen wurde — leer ohne `--fortsetzen`.

    Ohne den Schalter bleibt das alte Verhalten: ein zweiter Lauf misst alles neu und legt
    die Zeilen dazu. Das ist bewusst die Vorgabe, denn stilles Ueberspringen waere die
    gefaehrlichere Voreinstellung.
    """
    pfad = ordner / "laeufe.jsonl"
    if not args.fortsetzen or not pfad.exists():
        return set(), False
    schon = [json.loads(z) for z in pfad.read_text("utf-8").splitlines() if z]
    vorhanden = bereits_gemessen(schon)
    print(f"Fortsetzen: {len(vorhanden)} Messung(en) liegen bereits vor und werden uebersprungen")
    return vorhanden, any(z.get("art") == "uebernahme" for z in schon)


def _uebernahme(args, seiten: Sequence[tuple[Path, int, str | None]], protokoll: Protokoll,
                schon_uebernommen: bool = False) -> list[dict]:
    """Alte Messungen einlesen, gegen die aktuelle Stichprobe pruefen und ins Protokoll legen.

    Fehlende Paare sind eine laute Warnung, kein stiller Verlust: sie bedeuten, dass die
    beiden Laeufe **nicht** dieselbe Stichprobe gesehen haben — und genau darauf beruht die
    Vergleichbarkeit der Tabelle.

    Beim Fortsetzen (`schon_uebernommen`) passiert nichts: die Zeilen stehen bereits im
    Protokoll und ein zweites Mal geschrieben wuerden sie in jedem Median doppelt zaehlen.
    """
    if not args.uebernehmen or not args.uebernehmen_engines or schon_uebernommen:
        return []
    alt = [json.loads(z) for z in args.uebernehmen.read_text("utf-8").splitlines() if z]
    zeilen, fehlend = uebernommene_zeilen(
        alt, [(str(pfad), nummer) for pfad, nummer, _ in seiten], args.uebernehmen_engines
    )
    if fehlend:
        print(f"[WARNUNG] {len(fehlend)} Messung(en) fehlen im uebernommenen Lauf — die "
              f"Stichproben sind nicht deckungsgleich (z. B. {fehlend[0]})", file=sys.stderr)
    protokoll.schreibe({"art": "uebernahme", "quelle": str(args.uebernehmen),
                        "engines": list(args.uebernehmen_engines),
                        "zeilen": len(zeilen), "fehlend": len(fehlend)})
    for zeile in zeilen:
        protokoll.schreibe(zeile)
    return zeilen


def _waehle_seiten(args, referenzen, ohne) -> list[tuple[Path, int, str | None]]:
    if args.ohne_textebene:
        kandidaten = tuple(
            (str(pfad), nummer) for pfad, anzahl in ohne.items() for nummer in range(1, anzahl + 1)
        )
        auswahl = stichprobe(kandidaten, args.ohne_textebene, args.seed)
        return [(Path(datei), nummer, None) for datei, nummer in auswahl]
    auswahl = stichprobe(tuple(referenzen), args.seiten, args.seed)
    return [(Path(datei), nummer, referenzen[(datei, nummer)]) for datei, nummer in auswahl]


def main(argv: Sequence[str] | None = None) -> int:
    args = _argumente(argv)
    if args.bericht:
        print(f"Bericht: {schreibe_bericht(args.bericht)}")
        return 0
    if not args.korpus or not args.korpus.is_dir():
        raise OcrVergleichFehler("--korpus <ordner> fehlt oder ist kein Ordner")
    engines = pruefe_engines(args.engines)
    if not engines:
        raise OcrVergleichFehler("Keine Engine verfuegbar — nichts zu messen")
    referenzen, ohne = sammle_korpus(args.korpus, args.min_zeichen)
    print(f"Referenzseiten: {len(referenzen)} | PDFs ohne Textebene: {len(ohne)}")
    seiten = _waehle_seiten(args, referenzen, ohne)
    ordner = args.ausgabe / date.today().isoformat()
    erledigt, schon_uebernommen = _erledigt(args, ordner)
    protokoll = Protokoll(ordner / "laeufe.jsonl")
    protokoll.schreibe({"art": "lauf", "beginn": datetime.now().isoformat(timespec="seconds"),
                        "korpus": str(args.korpus), "engines": list(engines), "dpi": args.dpi,
                        "seed": args.seed, "min_zeichen": args.min_zeichen,
                        "seiten_geplant": len(seiten), "modus": "laufzeitprobe" if args.ohne_textebene else "wahrheit"})
    try:
        alt = _uebernahme(args, seiten, protokoll, schon_uebernommen)
        zeilen = alt + messe_seiten(seiten, engines, args.dpi, protokoll, erledigt)
        for engine in (*args.uebernehmen_engines, *engines):
            protokoll.schreibe(fasse_zusammen(zeilen, engine))
    finally:
        protokoll.schliesse()
    print(f"Bericht: {schreibe_bericht(ordner)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

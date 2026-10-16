"""M3: Datei → Seiten. PDF mit Textebene über pypdf, sonst OCR über die gewählte Engine.

Formate: `.pdf` (Textebene oder Bild-PDF), `.jpg`, `.jpeg`, `.png`, `.docx`,
`.md`, `.txt`. Alles andere ergibt `NichtLesbar`. Originale werden nur
gelesen, nie verändert.

Text/Markdown/DOCX
-------------------
`.txt`/`.md` werden als UTF-8 gelesen, mit Fallback auf Latin-1 bei
Kodierungsfehlern. Markdown-Syntax wird nicht konvertiert — Überschriften
und Betonungen bleiben als Rohzeichen stehen, das Chunking (`fundstellen.zerlege`)
trennt ohnehin nur an Leerzeilen. Lange Text-/Markdown-Dateien werden ab
`MAX_SEITENLAENGE` Zeichen an Absatzgrenzen (Leerzeilen) in mehrere Seiten
geteilt, damit Belegkarten einen echten Seitenbezug haben statt „Seite 1"
für alles.

`.docx`-Absätze werden durch Leerzeilen getrennt aneinandergehängt (Format,
das `fundstellen.zerlege` als eigene Absätze erkennt); Tabellenzeilen folgen
danach, Zellen durch `" | "` verbunden.

OCR-Engine wählbar (24.09.2026)
-------------------------------
`lies_seiten(pfad, ocr)` nimmt seit dem 24.09.2026 `OcrEinstellungen` entgegen:
Engine (`paddleocr` oder `tesseract`), Drehung, Sprache und Schwelle. **Ohne das
Argument bleibt alles beim Alten** (Tesseract, `deu`, Schwelle 0,6) — bestehende
Aufrufer und Tests sind damit unverändert gültig. Was das Produkt tatsächlich
benutzt, steht in `modelle.yaml` (`provider.lade_ocr_einstellungen`), Standard
dort ist `paddleocr`.

Warum der Wechsel: `paddleocr` hat zwei Messungen gewonnen —
`docs/ocr-portabel-2026-09-23.md` (96 gerenderte Seiten mit Textebene als
Wahrheit: F1 Wort paarweise 81:14 besser als Tesseract, Zahlentreue 94,7 gegen
84,3 %) und das Gegenlesen von 10 echten Scan-/Fotoseiten durch den Auftraggeber
(`beweise/ocr-scans/2026-09-24/urteile.json`: 7 brauchbar / 0 Fehler-in-Zahlen /
3 unbrauchbar gegen 3/1/5 bei Tesseract). Die ganze Kette steht in
`docs/ocr-entscheidung-2026-09-24.md`.

OCR-Sicherheit
--------------
**Tesseract:** `pytesseract.image_to_data(..., lang=...)` liefert je erkanntem
Wortkasten eine Konfidenz `conf`. Gezählt werden alle Kästen mit `conf >= 0` (der
Wert `-1` markiert Struktur-Kästen ohne Worterkennung). Sicherheit = arithmetisches
Mittel dieser Konfidenzen geteilt durch 100, also 0.0–1.0.

**PaddleOCR:** `predict` liefert `rec_scores` — einen Wert in 0…1 je erkannter
**Textzeile**, nicht je Wortkasten. Sicherheit = arithmetisches Mittel dieser
Zeilen-Scores.

Beide Größen heißen `Seite.sicherheit` und sind trotzdem **nicht dieselbe Größe**.
Zeilen-Scores liegen sichtbar höher (Median 0,994 gegen 0,799 auf denselben zehn
Scan-Seiten). Deshalb hat jede Engine ihre eigene Schwelle, und deshalb steht die
Schwelle in `modelle.yaml` statt als Konstante im Code (Ableitung:
`docs/ocr-entscheidung-2026-09-24.md`).

**Was der Zeilen-Score nicht leistet:** mit eingeschalteter Seitenorientierung
trennt er „brauchbar" und „unbrauchbar" nicht mehr — die Werte der als unbrauchbar
beurteilten Seiten (0,947–0,987) liegen mitten in der brauchbaren Klasse
(0,975–1,000). Die PaddleOCR-Schwelle weist deshalb faktisch nur noch leere
Ergebnisse ab; die Begründung steht bei `provider.OCR_STANDARD`.

Unverändert für **jede** Engine: erkennt die OCR kein einziges Wort bzw. keine
Zeile, ist die Sicherheit 0.0 — ein leeres Ergebnis ist kein sicheres Ergebnis.
Auf den zehn Scan-Seiten trifft genau das einmal zu (`paddleocr` liest auf einer
reinen Bildseite nichts).

Gemessen mit den Test-Fixtures (Tesseract 5, `deu`):

* `bild_pdf` (sauberer Scan, sechs Wortkästen, conf 95–96) → **0.958**
* `unscharfes_bild` (12° gedreht + GaussianBlur 4) → kein Wortkasten, kein Text
  → **0.0**

Die reine Mittelwertbildung aus dem Plan trennt die beiden Fälle also klar; nötig
war nur die Regel für das leere Ergebnis.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import io
import shutil
import subprocess
import re
import tempfile
from pathlib import Path
from statistics import fmean
from zipfile import BadZipFile

import pytesseract
from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf import __version__ as PYPDF_VERSION
from pypdf.errors import PdfReadError

from .typen import DokumentenassistentFehler, Seite

PDF_ENDUNG = ".pdf"
BILD_ENDUNGEN = (".jpg", ".jpeg", ".png")
TEXT_ENDUNGEN = (".txt", ".md")
DOCX_ENDUNG = ".docx"
OCR_SPRACHE = "deu"
OCR_HINWEIS = "OCR nötig, aber tesseract fehlt — nachinstallieren: brew install tesseract tesseract-lang"
PADDLE_HINWEIS = (
    "OCR-Engine 'paddleocr' gewählt, aber das Paket fehlt — nachinstallieren: "
    "uv sync --extra ocr-paddle  (oder in modelle.yaml `ocr: tesseract` setzen)"
)
MAX_SEITENLAENGE = 3000  # Zeichen; Absatzgrenze für die Seitenteilung langer Text-/Markdown-Dateien
TEXT_KODIERUNGEN = ("utf-8", "latin-1")


class NichtLesbar(DokumentenassistentFehler):
    """Unbekanntes Format oder kaputte Datei."""


class OcrNichtVerfuegbar(DokumentenassistentFehler):
    """Die gewählte OCR-Engine fehlt (oder ist unbekannt), obwohl OCR nötig wäre."""


@dataclasses.dataclass(frozen=True)
class OcrEinstellungen:
    """Was `lies_seiten` außer dem Pfad braucht — aus `modelle.yaml`, hier nur durchgereicht.

    Die Standardwerte sind **das Verhalten vor dem 24.09.2026**: Tesseract, `deu`,
    Schwelle 0,6. Ein Aufrufer ohne Argument bekommt damit exakt das, was er vorher
    bekam. Was das Produkt benutzt, entscheidet `provider.lade_ocr_einstellungen`
    (Standard dort: `paddleocr`, `german`, 0,80) — nicht dieser Code-Default.

    `drehung` schaltet **genau eine** von PaddleOCRs drei Vorstufen ein: die
    Seitenorientierung (`use_doc_orientation_classify`). Gemessen 24.09.2026 an zehn
    echten Scan-Seiten, jede Stufe einzeln (`beweise/ocr-drehung/2026-09-24/`):

      * Seitenorientierung: die drei verdrehten Seiten springen von 122/97/91 auf
        495/564/413 Zeichen, und **keine** der sieben anderen Seiten wird schlechter
        (zeichenweise identisch). Über alle zehn: 182 Zahlen, 26 Datumsangaben,
        10410 Zeichen — in jeder Spalte vorn, ohne Zeitkosten.
      * Entzerrung (`use_doc_unwarping`) **schadet**: verschlechtert 4 der 7 guten
        Seiten; auf Seite 4 verschwinden 6 von 13 Zahlen ersatzlos.
      * Zeilenorientierung (`use_textline_orientation`) verschlechtert eine Seite leicht.
      * Alle drei zusammen: 168 erkannte Zahlen — UNTER „gar keine Drehung" (179).

    Deshalb bleiben die beiden anderen Stufen aus und sind **nicht** einzeln schaltbar:
    ein Schlüssel für eine Einstellung, die gemessen nur schadet, wäre Konfiguration
    ohne Fall. Bei Tesseract hat das Feld keine Wirkung; Tesseract hat keine
    entsprechenden Stufen (die alternative `ocr_vorverarbeitung.vorverarbeite` ist auf
    96 gerenderten Seiten paarweise 25:51 durchgefallen und ist deshalb nicht im
    Produktpfad).
    """

    engine: str = "tesseract"
    drehung: bool = True
    sprache: str = OCR_SPRACHE
    schwelle: float = 0.6
    pdf_extraktion: str = 'pypdf'
    seitenbereinigung: bool = False  # Kopf-/Fußzeilen, Seitenzahlen, Silbentrennung (seitenrand.py)


def tesseract_vorhanden() -> bool:
    """Ist das tesseract-Programm im PATH? (Modulfunktion, damit Tests sie ersetzen können.)"""
    return shutil.which("tesseract") is not None


def paddleocr_vorhanden() -> bool:
    """Ist das Paket `paddleocr` installiert? Prüft ohne es zu **importieren**.

    `importlib.util.find_spec` findet das Paket, ohne `paddlepaddle` zu laden — der
    Import kostet mehrere Sekunden und zieht ein vollständiges Inferenz-Framework
    nach. Beim Start soll nur die Frage „ist es da?" beantwortet werden.
    """
    return importlib.util.find_spec("paddleocr") is not None


def fordere_ocr(ocr: OcrEinstellungen) -> None:
    """Prüft **beim Start**, ob die gewählte Engine benutzbar ist.

    Kein stiller Rückfall auf Tesseract: wer `paddleocr` einstellt und das Extra
    nicht installiert hat, bekommt eine Meldung mit Installationsbefehl — sonst
    liefe das Produkt mit einer anderen, messbar schwächeren Engine, als in
    `modelle.yaml` steht (3 gegen 7 brauchbare Scan-Seiten).
    """
    if ocr.engine == "tesseract":
        _fordere_tesseract()
    elif ocr.engine == "paddleocr":
        if not paddleocr_vorhanden():
            raise OcrNichtVerfuegbar(PADDLE_HINWEIS)
    else:
        raise OcrNichtVerfuegbar(
            f"Unbekannte OCR-Engine: {ocr.engine!r} — erlaubt sind 'paddleocr' und 'tesseract'"
        )


def lies_seiten(pfad: Path, ocr: OcrEinstellungen | None = None) -> tuple[Seite, ...]:
    """Liest eine Datei in unveränderliche Seiten.

    `ocr` fehlt → `OcrEinstellungen()`, also Tesseract wie vor dem 24.09.2026.

    Die OCR-Schwelle (Status `ocr_unsicher`) wird nicht hier, sondern im
    Orchestrator (`werkstatt.py`) aus `Seite.sicherheit` abgeleitet — `ocr.schwelle`
    reist hier nur mit, damit Engine und zugehörige Schwelle nicht getrennt werden
    können.
    """
    einstellungen = ocr or OcrEinstellungen()
    endung = pfad.suffix.lower()
    if endung == PDF_ENDUNG:
        seiten = _lies_pdf(pfad, einstellungen)
        if not einstellungen.seitenbereinigung:
            return seiten
        from dokumentenassistent.seitenrand import bereinige_seiten
        # Die Version trägt die Bereinigung, damit ein Index sieht, dass anders ausgelesen wurde.
        return tuple(dataclasses.replace(s, extraktor_version=f'{s.extraktor_version or ""}+seitenrand-v1')
                     for s in bereinige_seiten(seiten))
    if endung in BILD_ENDUNGEN:
        return (_lies_bild(pfad, einstellungen),)
    if endung in TEXT_ENDUNGEN:
        return _lies_text(pfad)
    if endung == DOCX_ENDUNG:
        return _lies_docx(pfad)
    raise NichtLesbar(f"Format nicht unterstützt: {endung or pfad.name} ({pfad.name})")


def _lies_pdf(pfad: Path, ocr: OcrEinstellungen) -> tuple[Seite, ...]:
    if ocr.pdf_extraktion in ('pdftotext', 'pdftotext_layout'):
        if not shutil.which('pdftotext') or not shutil.which('pdfinfo'):
            raise NichtLesbar('pdftotext/pdfinfo fehlt: Poppler installieren')
        version = _pdftotext_version()
        count = _pdfinfo_seiten(pfad)
        texte = _pdftotext_alle_seiten(pfad, count, ocr)
        return tuple(_pdftotext_seite(pfad, text, nummer, ocr, version)
                     for nummer, text in enumerate(texte, start=1))
    try:
        seiten_objekte = PdfReader(str(pfad)).pages
        if ocr.pdf_extraktion != 'pypdf':
            raise NichtLesbar('Unbekannte PDF-Extraktion')
        return tuple(
            _pdf_seite(seite, nummer, ocr) for nummer, seite in enumerate(seiten_objekte, start=1)
        )
    except PdfReadError as fehler:
        raise NichtLesbar(f"PDF nicht lesbar: {pfad.name} ({fehler})") from fehler


def _pdftotext_version() -> str:
    try:
        result = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True,
                                timeout=10, check=False)
    except subprocess.TimeoutExpired as exc:
        raise NichtLesbar('pdftotext Zeitlimit bei Versionsprüfung') from exc
    except OSError as exc:
        raise NichtLesbar('pdftotext nicht ausführbar') from exc
    if result.returncode:
        raise NichtLesbar('pdftotext Versionsprüfung fehlgeschlagen')
    lines = (result.stderr or result.stdout).splitlines()
    if not lines or not lines[0].strip():
        raise NichtLesbar('pdftotext Versionsprüfung lieferte keine Version')
    return lines[0].strip()


def _pdfinfo_seiten(pfad: Path) -> int:
    try:
        result = subprocess.run(['pdfinfo', str(pfad)], capture_output=True, timeout=60, check=False)
    except subprocess.TimeoutExpired as exc:
        raise NichtLesbar('pdfinfo Zeitlimit') from exc
    except OSError as exc:
        raise NichtLesbar('pdfinfo Ausführung fehlgeschlagen') from exc
    match = re.search(rb'^Pages:\s*(\d+)', result.stdout, re.M)
    if result.returncode or not match or int(match.group(1)) < 1:
        raise NichtLesbar('pdfinfo konnte PDF-Seiten nicht bestimmen')
    return int(match.group(1))


def _pdftotext_alle_seiten(pfad: Path, count: int, ocr: OcrEinstellungen) -> tuple[str, ...]:
    try:
        layout = ['-layout'] if ocr.pdf_extraktion == 'pdftotext_layout' else []
        result = subprocess.run(['pdftotext', *layout, '-enc', 'UTF-8', str(pfad), '-'],
                                capture_output=True, timeout=max(60, count * 3), check=False)
    except subprocess.TimeoutExpired as exc:
        raise NichtLesbar('pdftotext Zeitlimit bei PDF-Seite') from exc
    except OSError as exc:
        raise NichtLesbar('pdftotext Ausführung fehlgeschlagen') from exc
    if result.returncode:
        raise NichtLesbar('pdftotext konnte PDF nicht auslesen')
    try:
        parts = result.stdout.decode('utf-8').split('\f')
    except UnicodeDecodeError as exc:
        raise NichtLesbar('pdftotext lieferte kein UTF-8') from exc
    if len(parts) == count + 1 and not parts[-1].strip():
        parts.pop()
    if len(parts) != count:
        raise NichtLesbar('pdftotext lieferte falsche Seitenzahl')
    return tuple(part.strip() for part in parts)


def _pdftotext_seite(pfad: Path, text: str, nummer: int, ocr: OcrEinstellungen,
                     version: str) -> Seite:
    if text:
        return Seite(nummer, text, False, None, ocr.pdf_extraktion, version)
    try:
        seite = PdfReader(str(pfad)).pages[nummer - 1]
    except (PdfReadError, ValueError, IndexError) as exc:
        raise NichtLesbar('PDF-Bildseite für OCR nicht lesbar') from exc
    bilder = _pdf_bilder(seite)
    if bilder:
        fordere_ocr(ocr)
        ocr_text, sicherheit = _ocr_bilder(bilder, ocr)
        return Seite(nummer, ocr_text, True, sicherheit, f'ocr:{ocr.engine}', None)
    if (seite.extract_text() or '').strip():
        raise NichtLesbar('pdftotext lieferte trotz nativer Textebene keinen Text')
    return Seite(nummer, '', False, None, ocr.pdf_extraktion, version)


def _pdf_seite(seite, nummer: int, ocr: OcrEinstellungen) -> Seite:
    text = (seite.extract_text() or "").strip()
    if text:
        return Seite(nummer=nummer, text=text, per_ocr=False, sicherheit=None,
                     extraktor='pypdf', extraktor_version=PYPDF_VERSION)

    bilder = _pdf_bilder(seite)
    if not bilder:
        return Seite(nummer=nummer, text="", per_ocr=False, sicherheit=None,
                     extraktor='pypdf', extraktor_version=PYPDF_VERSION)

    fordere_ocr(ocr)
    ocr_text, sicherheit = _ocr_bilder(bilder, ocr)
    return Seite(nummer=nummer, text=ocr_text, per_ocr=True, sicherheit=sicherheit,
                 extraktor=f'ocr:{ocr.engine}')


def _pdf_bilder(seite) -> tuple[Image.Image, ...]:
    """Eingebettete Bilder einer PDF-Seite als PIL-Bilder."""
    try:
        return tuple(Image.open(io.BytesIO(eintrag.data)) for eintrag in seite.images)
    except (UnidentifiedImageError, OSError, ValueError, KeyError):
        return ()


def _lies_bild(pfad: Path, ocr: OcrEinstellungen) -> Seite:
    fordere_ocr(ocr)
    try:
        bild = Image.open(pfad)
    except (UnidentifiedImageError, OSError) as fehler:
        raise NichtLesbar(f"Bild nicht lesbar: {pfad.name} ({fehler})") from fehler
    text, sicherheit = _ocr_bilder((bild,), ocr)
    return Seite(nummer=1, text=text, per_ocr=True, sicherheit=sicherheit)


def _ocr_bilder(bilder: tuple[Image.Image, ...], ocr: OcrEinstellungen) -> tuple[str, float]:
    """OCR über alle Bilder einer Seite: zusammengefügter Text und mittlere Konfidenz.

    Die Konfidenz ist je nach Engine über Wortkästen (Tesseract) oder Textzeilen
    (PaddleOCR) gemittelt — dieselbe Zahl im Feld, nicht dieselbe Größe. Kein
    erkanntes Stück ergibt 0.0, für beide Engines gleich.
    """
    lies = _paddle_seite if ocr.engine == "paddleocr" else _tesseract_seite
    texte: list[str] = []
    konfidenzen: list[float] = []
    for bild in bilder:
        teil, werte = lies(bild, ocr)
        texte.append(teil)
        konfidenzen.extend(werte)
    text = "\n".join(teil for teil in texte if teil)
    return text, (fmean(konfidenzen) if konfidenzen else 0.0)


def _tesseract_seite(bild: Image.Image, ocr: OcrEinstellungen) -> tuple[str, list[float]]:
    """Text und Wortkonfidenzen (0…1); `conf < 0` sind Struktur-Kästen ohne Worterkennung."""
    text = pytesseract.image_to_string(bild, lang=ocr.sprache).strip()
    daten = pytesseract.image_to_data(bild, lang=ocr.sprache, output_type=pytesseract.Output.DICT)
    return text, [float(wert) / 100 for wert in daten["conf"] if float(wert) >= 0]


def _paddle_seite(bild: Image.Image, ocr: OcrEinstellungen) -> tuple[str, list[float]]:
    """Text und Zeilen-Scores von PaddleOCR.

    Das Bild geht als **PNG-Datei** an `predict` und nicht als Array: genau so ist
    die Engine in `ocr_vergleich.py` und `ocr_scans.py` gemessen worden, und genau
    diese Messung trägt die Entscheidung. Ein anderer Eingabeweg (Farbkanal-
    Reihenfolge, Skalierung) wäre eine ungemessene Abweichung an der Stelle, an der
    das Ergebnis entsteht.
    """
    leser = paddle_leser(ocr.sprache, ocr.drehung)
    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "seite.png"
        bild.convert("RGB").save(datei, "PNG")
        ergebnis = leser.predict(str(datei))
    zeilen = [t for block in (ergebnis or []) for t in (block.get("rec_texts") or ())]
    werte = [float(s) for block in (ergebnis or []) for s in (block.get("rec_scores") or ())]
    return "\n".join(zeilen).strip(), werte


_PADDLE_LESER: dict[tuple[str, bool], object] = {}


def paddle_leser(sprache: str, drehung: bool):
    """Den PaddleOCR-Leser holen; das Laden der Modelle fällt einmal je Einstellung an (~5 s).

    Modulfunktion, damit Tests sie ersetzen können — `paddleocr` wird in Tests nie
    importiert (Wächter: `test_M3_G17_paddleocr_wird_in_den_tests_nie_geladen`).
    """
    schluessel = (sprache, drehung)
    if schluessel not in _PADDLE_LESER:
        try:
            from paddleocr import PaddleOCR
        except ImportError as fehler:
            raise OcrNichtVerfuegbar(f"{PADDLE_HINWEIS}  (Importfehler: {fehler})") from fehler
        # NUR die Seitenorientierung. Die beiden anderen Vorstufen (`use_doc_unwarping`,
        # `use_textline_orientation`) bleiben AUS, weil sie gemessen schaden — siehe
        # Docstring von `OcrEinstellungen.drehung` und beweise/ocr-drehung/2026-09-24/.
        _PADDLE_LESER[schluessel] = PaddleOCR(
            lang=sprache,
            use_doc_orientation_classify=drehung,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _PADDLE_LESER[schluessel]


def _fordere_tesseract() -> None:
    if not tesseract_vorhanden():
        raise OcrNichtVerfuegbar(OCR_HINWEIS)


def _lies_text(pfad: Path) -> tuple[Seite, ...]:
    text = _lies_text_mit_fallback(pfad)
    return _text_zu_seiten(text)


def _lies_text_mit_fallback(pfad: Path) -> str:
    rohdaten = pfad.read_bytes()
    for kodierung in TEXT_KODIERUNGEN:
        try:
            return rohdaten.decode(kodierung)
        except UnicodeDecodeError:
            continue
    return rohdaten.decode(TEXT_KODIERUNGEN[-1], errors="replace")


def _text_zu_seiten(text: str) -> tuple[Seite, ...]:
    if len(text) <= MAX_SEITENLAENGE:
        return (Seite(nummer=1, text=text, per_ocr=False, sicherheit=None),)
    teile = _teile_an_absaetzen(text, MAX_SEITENLAENGE)
    return tuple(
        Seite(nummer=nummer, text=teil, per_ocr=False, sicherheit=None)
        for nummer, teil in enumerate(teile, start=1)
    )


def _teile_an_absaetzen(text: str, max_laenge: int) -> list[str]:
    """Absätze (durch Leerzeilen getrennt) so packen, dass jede Seite höchstens
    `max_laenge` Zeichen hat. Ein einzelner überlanger Absatz bildet eine eigene,
    dann selbst überlange Seite — er wird nicht mitten im Wort zerschnitten."""
    absaetze = text.split("\n\n")
    seiten: list[str] = []
    aktuelle: list[str] = []
    laenge = 0
    for absatz in absaetze:
        zusatz = len(absatz) + (2 if aktuelle else 0)
        if aktuelle and laenge + zusatz > max_laenge:
            seiten.append("\n\n".join(aktuelle))
            aktuelle = [absatz]
            laenge = len(absatz)
        else:
            aktuelle.append(absatz)
            laenge += zusatz
    if aktuelle:
        seiten.append("\n\n".join(aktuelle))
    return seiten


def _lies_docx(pfad: Path) -> tuple[Seite, ...]:
    try:
        dokument = DocxDocument(str(pfad))
    except (PackageNotFoundError, KeyError, ValueError, BadZipFile) as fehler:
        raise NichtLesbar(f"DOCX nicht lesbar: {pfad.name} ({fehler})") from fehler
    text = _docx_text(dokument)
    return (Seite(nummer=1, text=text, per_ocr=False, sicherheit=None),)


def _docx_text(dokument: DocxDocument) -> str:
    absaetze = [absatz.text for absatz in dokument.paragraphs if absatz.text]
    tabellenzeilen = [
        " | ".join(zelle.text for zelle in zeile.cells)
        for tabelle in dokument.tables
        for zeile in tabelle.rows
    ]
    return "\n\n".join(absaetze + tabellenzeilen)

"""Gegenlese-Paket fuer echte Scan-Seiten — der Fall, den `ocr_vergleich.py` nicht messen kann.

Warum es dieses Modul gibt
--------------------------
Alle bisherigen OCR-Zahlen (`docs/ocr-portabel-2026-09-23.md`) stammen von **sauber
gerenderten** PDF-Seiten mit Textebene. Nur dort gibt es eine maschinelle Wahrheit, gegen die
sich eine Fehlerrate rechnen laesst. Im Betrieb haengen an der OCR aber genau die anderen
Seiten: **134 Seiten** ohne Textebene (119 aus 34 PDFs plus 15 Bilddateien) — Scans und
Handyfotos, schief, verrauscht, wechselnd belichtet. Ob `paddleocr` (die Empfehlung) dort
ueberhaupt sauber liest und ob die Bild-Vorverarbeitung, die auf Renderings durchfiel, hier
hilft, ist **ungemessen**.

Dort gibt es keine Wahrheit, also gibt es auch nichts automatisch zu bewerten. Deshalb ist
dieses Modul ausdruecklich **kein Messstand mit Urteil**, sondern ein Vorlagenbauer: es zieht
eine deterministische Stichprobe, laesst vier Engines darauflaufen und legt Bild und Texte so
nebeneinander, dass **ein Mensch** urteilen kann. Die Maschine wertet nichts, hebt nichts
hervor und schlaegt nichts vor — jede Hervorhebung waere eine Vorwegnahme des Urteils, das
hier gerade der einzige belastbare Teil ist.

Maschinell erhoben wird nur, was ohne Wahrheit erhebbar ist (`indikatoren`): Zeichenzahl,
Anzahl erkannter Zahlen und Datumsangaben, Konfidenz (soweit die Engine eine liefert) und
Dauer. Das sind **Indikatoren, keine Qualitaet** — mehr Zeichen kann mehr gelesener Text oder
mehr Rauschen sein. Ihr Zweck ist, nach dem Gegenlesen gegen das menschliche Urteil gehalten
zu werden: taugt einer von ihnen als billiger Stellvertreter, liesse sich die naechste Runde
ohne Handarbeit fahren.

Datenschutz
-----------
Der Korpus ist privat. Das Gegenlese-Paket enthaelt naturgemaess Dokumentinhalt (die Bilder
und den OCR-Text) — das ist der Zweck und bleibt lokal: `beweise/ocr-scans/` steht in der
`.gitignore`. In `laeufe.jsonl` steht **kein** Dokumentinhalt, nur Dateiname, Seitenzahl und
Kennzahlen; `protokollzeile` bekommt den Text, gibt aber nur Zahlen zurueck.

Das Paket laeuft **offline**: eine einzige HTML-Datei, ein PNG je Seite, kein Server, keine
externe Adresse, kein `fetch`. Die Urteile werden im Browser gesammelt und als JSON-Datei
zum Herunterladen angeboten.

Messkommando
------------
    uv run --extra ocr --extra ocr-paddle python -m dokumentenassistent.ocr_scans \\
        --korpus $DOKASS_BESTAND --seiten 10 --seed 42
"""
from __future__ import annotations

import argparse
import html
import os
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from .ocr_kennzahlen import datumsangaben, normalisiere, zahlen
from .ocr_vergleich import (
    OCR_SPRACHE,
    OcrVergleichFehler,
    Protokoll,
    STANDARD_DPI,
    STANDARD_SEED,
    _paddle_leser,
    _vision_module,
    rendere,
    stichprobe,
    textebenen,
    vorverarbeite,
)

BILDENDUNGEN = (".jpg", ".jpeg", ".png")
# macOS legt auf fremden Dateisystemen neben jeder Datei einen Metadaten-Rumpf `._<name>`
# an. Er traegt dieselbe Endung, ist aber kein Bild — der erste Lauf ist genau darueber
# gestolpert ("cannot identify image file") und hat neun statt zehn Seiten geliefert. Er
# erklaert zugleich die Differenz zur Zaehlung vom 23.09.2026: 16 statt 15 Bilddateien.
APPLEDOUBLE = "._"
STANDARD_SEITEN = 10
# Urteilsstufen des Gegenlesens. Drei, nicht fuenf: der Unterschied, auf den es ankommt, ist
# "kann ich das Dokument damit beantworten" — und die Zwischenstufe muss die Stelle benennen,
# an der dieser Assistent scheitert, naemlich falsche Zahlen in einem Zitat.
URTEILE = ("brauchbar", "Fehler in Zahlen", "unbrauchbar")
STANDARD_ENGINES = ("tesseract", "tesseract_vorverarbeitet", "paddleocr", "vision")
# Ab diesem loadavg gilt eine gemessene Dauer als unter Fremdlast entstanden und damit als
# **nicht belastbar**. Der Wert ist nicht frei gewaehlt: der Lauf vom 23.09.2026 hat gezeigt,
# dass sich die Zeiten unter Fremdlast verdoppeln (paddleocr 30 s -> 57 s). Gemessen, nicht
# behauptet — `loadavg` steht je Zeile im Protokoll, die Schwelle ist nur die Lesehilfe.
# Die Lesequalitaet ist davon unberuehrt: Fremdlast macht eine Engine langsamer, nicht dümmer.
FREMDLAST = 4.0


# =========================================================== Quellen und Ziehung


def ocr_pflichtige_quellen(korpus: Path) -> tuple[tuple[str, int], ...]:
    """Alle (Datei, Seite), die im Betrieb an der OCR haengen.

    Das sind zwei Sorten: jede Seite eines PDFs, das **keine** Textebene fuehrt, und jede
    Bilddatei (als Seite 1). PDFs **mit** Textebene bleiben aussen vor — sie brauchen keine
    OCR, und genau sie waren der Messstand der bisherigen Runden.
    """
    quellen: list[tuple[str, int]] = []
    for pfad in sorted(korpus.rglob("*")):
        if not pfad.is_file() or pfad.name.startswith(APPLEDOUBLE):
            continue
        endung = pfad.suffix.lower()
        if endung in BILDENDUNGEN:
            quellen.append((str(pfad), 1))
        elif endung == ".pdf":
            seiten = textebenen(pfad)
            if not any(seiten.values()):
                quellen.extend((str(pfad), nummer) for nummer in sorted(seiten))
    return tuple(quellen)


def ziehe(korpus: Path, anzahl: int, seed: int) -> tuple[tuple[str, int], ...]:
    """Deterministische Stichprobe, reihum ueber die Dateien (`ocr_vergleich.stichprobe`).

    Reihum ist hier wichtiger als bei der Wahrheitsmessung: zehn Seiten aus einem Dokument
    waeren zehnmal derselbe Scanner, dieselbe Beleuchtung, dieselbe Schrift — und der Befund
    haengte an einem Geraet statt an einem Bestand.
    """
    return stichprobe(ocr_pflichtige_quellen(korpus), anzahl, seed)


# ==================================================================== Kennzahlen


def indikatoren(text: str) -> dict[str, int]:
    """Zeichenzahl, Anzahl Zahlen, Anzahl Datumsangaben — ohne Wahrheit, also ohne Urteil.

    Dieselbe Normalisierung und dieselben Erkenner wie in der Wahrheitsmessung, damit die
    Zahlen zwischen beiden Runden vergleichbar bleiben. `zahlen` laesst Datumsangaben
    ausdruecklich aus, sonst zaehlte `14.08.2026` dreimal.
    """
    fest = normalisiere(text)
    return {"zeichen": len(fest), "zahlen": len(zahlen(fest)), "daten": len(datumsangaben(fest))}


def protokollzeile(
    *, engine: str, quelle: Path, seite: int, nummer: int, text: str,
    konfidenz: float | None, sekunden: float, loadavg: float,
) -> dict:
    """Eine Zeile fuer `laeufe.jsonl` — **ohne** Dokumentinhalt.

    Der Text geht hinein und kommt nicht wieder heraus: gespeichert werden nur die
    Kennzahlen aus `indikatoren`. `loadavg` steht dabei, weil eine Dauer ohne die Last der
    Maschine keine Aussage ueber die Engine ist (Befund 23.09.2026: unter Fremdlast
    verdoppelten sich die Zeiten).
    """
    return {
        "art": "seite", "engine": engine, "paket_seite": nummer,
        "datei": quelle.name, "seite": seite,
        **indikatoren(text),
        "konfidenz": None if konfidenz is None else round(konfidenz, 4),
        "ocr_sekunden": round(sekunden, 3),
        "loadavg": round(loadavg, 2),
        "dauer_unter_fremdlast": loadavg >= FREMDLAST,
    }


# ======================================================================= Engines
#
# Eigene Funktionen statt `ocr_vergleich.ENGINES`, weil hier **zusaetzlich die Konfidenz**
# gebraucht wird: ohne Wahrheit ist sie der einzige Wert, den die Engine selbst ueber ihr
# Ergebnis sagt. Jede liefert (Text, Konfidenz oder None).


def _tesseract(bild: Path, *, vorverarbeitet: bool) -> tuple[str, float | None]:
    import pytesseract
    from PIL import Image

    with Image.open(bild) as roh:
        eingabe = vorverarbeite(roh) if vorverarbeitet else roh.copy()
    text = pytesseract.image_to_string(eingabe, lang=OCR_SPRACHE).strip()
    daten = pytesseract.image_to_data(eingabe, lang=OCR_SPRACHE,
                                      output_type=pytesseract.Output.DICT)
    # `conf < 0` sind Struktur-Kaesten ohne Text — dieselbe Regel wie `auslesen._wortkonfidenzen`.
    werte = [float(w) for w in daten["conf"] if float(w) >= 0]
    return text, (sum(werte) / len(werte) / 100 if werte else None)


def _paddleocr(bild: Path) -> tuple[str, float | None]:
    """Wie in der Wahrheitsmessung: Vorstufen aus, damit der Vergleich die Erkennung misst.

    `rec_scores` ist die Konfidenz je erkannter **Textzeile** (nicht je Wortkasten wie bei
    Tesseract) — die beiden Spalten sind deshalb nicht dieselbe Groesse und duerfen nicht
    gegeneinander gelesen werden.
    """
    ergebnis = _paddle_leser().predict(str(bild))
    zeilen = [t for block in (ergebnis or []) for t in (block.get("rec_texts") or ())]
    werte = [float(s) for block in (ergebnis or []) for s in (block.get("rec_scores") or ())]
    return "\n".join(zeilen).strip(), (sum(werte) / len(werte) if werte else None)


def _vision(bild: Path) -> tuple[str, float | None]:
    """Apple Vision ohne Sprachkorrektur — Messlatte, macOS-only, kein Kandidat."""
    Quartz, Vision, NSURL = _vision_module()
    quelle = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(bild)), None)
    if quelle is None:
        raise OcrVergleichFehler(f"Vision kann das Bild nicht oeffnen: {bild.name}")
    anfrage = Vision.VNRecognizeTextRequest.alloc().init()
    anfrage.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    anfrage.setRecognitionLanguages_(["de-DE"])
    anfrage.setUsesLanguageCorrection_(False)
    bearbeiter = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        Quartz.CGImageSourceCreateImageAtIndex(quelle, 0, None), None
    )
    erfolg, fehler = bearbeiter.performRequests_error_([anfrage], None)
    if not erfolg:
        raise OcrVergleichFehler(f"Vision-Anfrage fehlgeschlagen: {bild.name} ({fehler})")
    kandidaten = [b.topCandidates_(1)[0] for b in (anfrage.results() or []) if b.topCandidates_(1)]
    werte = [float(k.confidence()) for k in kandidaten]
    return ("\n".join(k.string() for k in kandidaten).strip(),
            sum(werte) / len(werte) if werte else None)


SCAN_ENGINES = {
    "tesseract": lambda bild: _tesseract(bild, vorverarbeitet=False),
    "tesseract_vorverarbeitet": lambda bild: _tesseract(bild, vorverarbeitet=True),
    "paddleocr": _paddleocr,
    "vision": _vision,
}


# ======================================================================= Rendern


def bild_fuer(quelle: Path, seite: int, dpi: int, ziel: Path) -> None:
    """Die Seite als PNG unter `ziel` — PDF ueber `pdftoppm`, Bilddatei durch Umwandeln.

    `dpi` gilt nur fuer PDFs: eine Bilddatei hat die Aufloesung, mit der fotografiert oder
    gescannt wurde, und sie hochzurechnen wuerde Information vortaeuschen, die nicht da ist.
    Genau dieses Bild sieht die OCR — und genau dieses Bild sieht der Auftraggeber.
    """
    if quelle.suffix.lower() in BILDENDUNGEN:
        from PIL import Image

        with Image.open(quelle) as roh:
            roh.convert("RGB").save(ziel, "PNG")
        return
    # Ueber einen Zwischenordner, nicht direkt in den Paketordner: `rendere` benennt die Datei
    # nach der **Quell**seite (`seite-6.png`), das Paket nach der **Paket**seite
    # (`seite-06.png`). Beide Namensraeume im selben Ordner haben sich beim ersten Lauf
    # prompt getroffen — eine liegengebliebene `seite-6.png` neben `seite-02.png`.
    with tempfile.TemporaryDirectory() as tmp:
        gerendert, _dauer = rendere(quelle, seite, dpi, Path(tmp))
        gerendert.replace(ziel)


# ================================================================= Gegenlese-HTML


_STIL = """
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 1.5rem;
       background: #f5f5f4; color: #1c1917; }
h1 { font-size: 1.3rem; } h2 { font-size: 1.05rem; margin: 0 0 .6rem; }
.seite { background: #fff; border: 1px solid #d6d3d1; border-radius: 6px;
         padding: 1rem; margin-bottom: 2rem; }
.paar { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1.2rem; }
.bild { position: sticky; top: 1rem; align-self: start; }
.bild img { width: 100%; border: 1px solid #a8a29e; background: #fff; }
.engine { border-top: 1px solid #e7e5e4; padding-top: .7rem; margin-top: .7rem; }
.engine:first-child { border-top: 0; margin-top: 0; padding-top: 0; }
.engine h3 { font-family: ui-monospace, monospace; font-size: .95rem; margin: 0 0 .4rem; }
pre { white-space: pre-wrap; word-break: break-word; font-size: .82rem; line-height: 1.45;
      background: #fafaf9; border: 1px solid #e7e5e4; padding: .6rem; margin: 0 0 .5rem;
      max-height: 22rem; overflow: auto; }
.leer { color: #78716c; font-style: italic; }
label.urteil { margin-right: 1rem; font-size: .88rem; }
textarea { width: 100%; box-sizing: border-box; font: inherit; font-size: .85rem;
           min-height: 2.6rem; margin-top: .4rem; }
.herkunft { color: #57534e; font-size: .85rem; }
#sichern { position: fixed; right: 1.5rem; bottom: 1.5rem; padding: .8rem 1.2rem;
           font-size: 1rem; background: #1c1917; color: #fff; border: 0; border-radius: 6px;
           cursor: pointer; }
@media (max-width: 900px) { .paar { grid-template-columns: 1fr; } .bild { position: static; } }
"""

# Reines JavaScript, kein Netz: die Urteile werden aus dem Formular gelesen und als
# JSON-Datei zum Herunterladen angeboten (Blob + <a download>). Kein `fetch`, kein Server,
# kein Speicher ausserhalb dieser Seite — ein Doppelklick in Safari genuegt.
_SKRIPT = """
function sichern() {
  const urteile = [];
  document.querySelectorAll('div.engine').forEach(function (kasten) {
    const gewaehlt = kasten.querySelector('input[type=radio]:checked');
    urteile.push({
      paket_seite: Number(kasten.dataset.seite),
      datei: kasten.dataset.datei,
      quell_seite: Number(kasten.dataset.quellSeite),
      engine: kasten.dataset.engine,
      urteil: gewaehlt ? gewaehlt.value : null,
      notiz: kasten.querySelector('textarea').value
    });
  });
  const inhalt = JSON.stringify({ gegengelesen_am: new Date().toISOString(),
                                  paket: document.body.dataset.paket,
                                  urteile: urteile }, null, 2);
  const ziel = document.createElement('a');
  ziel.href = URL.createObjectURL(new Blob([inhalt], { type: 'application/json' }));
  ziel.download = 'urteile.json';
  ziel.click();
  URL.revokeObjectURL(ziel.href);
}
"""


def gegenlese_html(seiten: Sequence[dict], datum: str) -> str:
    """Eine Datei: links das Bild, rechts die OCR-Ergebnisse untereinander, je Engine ein Urteil.

    Bewusst **ohne** jede Hervorhebung von Unterschieden. Ein Diff waere eine maschinelle
    Vorentscheidung darueber, was wichtig ist — und die Maschine ist genau das, was hier
    geprueft wird. Die Reihenfolge der Engines ist in jeder Seite dieselbe, damit das Auge
    sie nicht suchen muss.
    """
    teile = [
        "<!DOCTYPE html>", '<html lang="de">', '<head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>OCR-Gegenlesen {html.escape(datum)}</title>",
        f"<style>{_STIL}</style><script>{_SKRIPT}</script></head>",
        f'<body data-paket="{html.escape(datum)}">',
        f"<h1>OCR-Gegenlesen {html.escape(datum)} — {len(seiten)} echte Scan-Seiten</h1>",
        "<p>Links das Bild, das die OCR gesehen hat. Rechts, was jede Engine daraus gelesen "
        "hat. Bitte je Engine urteilen und unten rechts <em>Urteile sichern</em> drücken; "
        "die Datei <code>urteile.json</code> landet im Download-Ordner.</p>",
    ]
    for seite in seiten:
        teile += _seiten_block(seite)
    teile += ['<button id="sichern" onclick="sichern()">Urteile sichern</button>',
              "</body></html>"]
    return "\n".join(teile) + "\n"


def _seiten_block(seite: dict) -> list[str]:
    nummer = seite["nummer"]
    kopf = (f"Seite {nummer} von {html.escape(str(seite['datei']))}, "
            f"Seite {seite['seite']} der Quelle")
    teile = [
        '<section class="seite">', f"<h2>{kopf}</h2>", '<div class="paar">',
        f'<div class="bild"><img src="{html.escape(seite["bild"])}" '
        f'alt="Seite {nummer}"></div>', "<div>",
    ]
    for ergebnis in seite["ergebnisse"]:
        teile += _engine_block(seite, ergebnis)
    teile += ["</div>", "</div>", "</section>"]
    return teile


def _engine_block(seite: dict, ergebnis: dict) -> list[str]:
    engine, nummer = ergebnis["engine"], seite["nummer"]
    text = ergebnis.get("text") or ""
    inhalt = (f"<pre>{html.escape(text)}</pre>" if text.strip()
              else '<pre class="leer">(kein Text gelesen)</pre>')
    teile = [
        f'<div class="engine" data-seite="{nummer}" data-engine="{html.escape(engine)}" '
        f'data-datei="{html.escape(str(seite["datei"]))}" data-quell-seite="{seite["seite"]}">',
        f"<h3>{html.escape(engine)}</h3>", inhalt, "<div>",
    ]
    for urteil in URTEILE:
        teile.append(
            f'<label class="urteil"><input type="radio" name="urteil-{nummer}-{engine}" '
            f'value="{urteil}"> {urteil}</label>'
        )
    teile += ["</div>",
              f'<textarea name="notiz-{nummer}-{engine}" '
              f'placeholder="Notiz (was ist falsch?)"></textarea>', "</div>"]
    return teile


# ======================================================================== README


def readme_text(seiten: Sequence[dict], engines: Sequence[str], datum: str,
                lasten: Sequence[float] = ()) -> str:
    """Anleitung fuer den Auftraggeber — was zu tun ist und was das Ergebnis **nicht** ist.

    `lasten` sind die **je Messung** abgelesenen loadavg-Werte, nicht der Wert zu Beginn.
    Der Unterschied ist nicht akademisch: der Lauf vom 24.09.2026 startete bei 3,6 (also
    unter `FREMDLAST`) und lief bei bis zu 10,2 weiter. Ein README, das den Startwert
    befragt, liess 37 von 40 unbelastbaren Zeitangaben unkommentiert — es schwieg also genau
    dann, wenn es haette reden muessen.
    """
    ziehung = "\n".join(
        f"| {s['nummer']} | {s['datei']} | {s['seite']} |" for s in seiten
    )
    betroffen = [w for w in lasten if w >= FREMDLAST]
    last = (
        f"""## Die Zeitangaben sind nicht belastbar

**{len(betroffen)} der {len(lasten)} Messungen** liefen unter Fremdlast (loadavg bis
{max(lasten):.1f}; belastbar wäre unter {FREMDLAST:.0f}). Jede betroffene Zeile in
`laeufe.jsonl` trägt `dauer_unter_fremdlast: true` und den `loadavg` des Augenblicks; ihre
Sekundenangabe misst zum guten Teil die Auslastung der Maschine, nicht die Engine.

Für das Gegenlesen spielt das keine Rolle: beurteilt wird, **was** eine Engine erkennt, und
das ändert sich unter Last nicht — nur **wie schnell** sie es tut.

"""
        if betroffen
        else ""
    )
    return f"""# OCR-Gegenlesen {datum}

## Öffnen

Doppelklick auf `gegenlesen.html` (Safari genügt). Kein Server, keine Netzverbindung, die
Seite lädt nichts nach. Alle Bilder liegen als `seite-NN.png` daneben.

## Was zu beurteilen ist

Für jede der {len(seiten)} Seiten stehen {len(engines)} OCR-Ergebnisse untereinander:
{", ".join(f"`{e}`" for e in engines)}. Links daneben das Bild, das die OCR gesehen hat.

Entscheidend sind **nicht** Rechtschreibung oder Zeilenumbrüche, sondern die Felder, nach
denen dieser Assistent gefragt wird und die er wörtlich zitieren muss:

* **Beträge** — stimmt jede Ziffer, Komma und Tausenderpunkt? `1.240,00` statt `1240,00`
  ist noch hinnehmbar, `1.249,00` nicht.
* **Daten und Fristen** — Rechnungsdatum, Zahlungsziel, Vertragsbeginn.
* **Rechnungsnummern** und andere Belegnummern — eine falsche Stelle macht das Dokument
  unauffindbar.
* **Namen** — Handwerksbetrieb, Mieter, Vermieter, Straße.

Urteil je Engine:

* **{URTEILE[0]}** — die oben genannten Felder sind alle richtig gelesen.
* **{URTEILE[1]}** — der Text ist im Großen brauchbar, aber mindestens eine Zahl, ein Datum
  oder eine Belegnummer ist falsch. Das ist der schlimmere Fall als fehlender Text: ein
  falsches Zitat sieht richtig aus.
* **{URTEILE[2]}** — zu wenig oder zu kaputt, um damit zu arbeiten.

Im Freitextfeld bitte notieren, **welche** Stelle falsch ist. Ein Stichwort genügt.

Zum Schluss unten rechts **Urteile sichern** drücken — es entsteht `urteile.json` im
Download-Ordner. Die Datei bitte zurückgeben; sie enthält Urteile und Notizen, keine Bilder.

## Was das Ergebnis nicht ist

{len(seiten)} Seiten sind ein **Hinweis, keine Statistik**. Bei zehn Seiten entspricht eine
einzige Seite 10 Prozentpunkten; ein Unterschied von einer oder zwei Seiten zwischen zwei
Engines bedeutet nichts. Aussagekräftig wäre nur ein deutlicher Abstand — etwa eine Engine,
die auf acht Seiten brauchbar ist, gegen eine, die es auf drei ist.

Der Zweck ist ein anderer: die bisherigen Zahlen stammen von sauber gerenderten Seiten mit
Textebene. Ob sie auf echten Scans überhaupt gelten, ist ungemessen. Diese Runde soll zeigen,
ob die Empfehlung dort grob standhält oder grob danebenliegt — nicht, um wie viel.

{last}## Datenschutz

Dieser Ordner enthält Dokumentinhalt (Bilder und gelesenen Text) und bleibt deshalb lokal:
`beweise/ocr-scans/` steht in der `.gitignore`. In `laeufe.jsonl` steht kein Inhalt, nur
Kennzahlen.

## Ziehung

Deterministisch, Seed 42, reihum über die Dateien.

| Paket-Seite | Datei | Seite der Quelle |
|---|---|---|
{ziehung}
"""


def baue_paket(seiten: Sequence[dict], engines: Sequence[str], ordner: Path, datum: str,
               lasten: Sequence[float] = ()) -> Path:
    """Schreibt `gegenlesen.html` und `README.md`; die PNGs liegen schon dort."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / "gegenlesen.html"
    ziel.write_text(gegenlese_html(seiten, datum), encoding="utf-8")
    (ordner / "README.md").write_text(readme_text(seiten, engines, datum, lasten),
                                      encoding="utf-8")
    return ziel


# =========================================================================== Lauf


def _pruefe_engines(namen: Sequence[str]) -> tuple[str, ...]:
    """Unbekannte Namen sind ein Abbruch; fehlende Installationen werden laut uebersprungen."""
    unbekannt = [n for n in namen if n not in SCAN_ENGINES]
    if unbekannt:
        raise OcrVergleichFehler(f"Unbekannte Engine(s): {', '.join(unbekannt)}")
    verfuegbar = []
    for name in namen:
        pruefung = {"paddleocr": _paddle_leser, "vision": _vision_module}.get(name)
        if pruefung is not None:
            try:
                pruefung()
            except OcrVergleichFehler as fehler:
                print(f"[uebersprungen] Engine '{name}': {fehler}", file=sys.stderr)
                continue
        verfuegbar.append(name)
    return tuple(verfuegbar)


def messe(gezogen: Sequence[tuple[str, int]], engines: Sequence[str], dpi: int,
          ordner: Path, protokoll: Protokoll) -> tuple[list[dict], list[float]]:
    """Rendert jede gezogene Seite ins Paket und laesst jede Engine darauf laufen.

    Der Text bleibt im Speicher (er geht ins HTML), ins Protokoll gehen nur Kennzahlen.
    Ein Engine-Fehler beendet den Lauf nicht — er wird als solcher protokolliert und steht
    im Paket als Fehlermeldung statt als leeres Ergebnis, damit "nichts gelesen" und
    "abgestuerzt" unterscheidbar bleiben.
    """
    seiten: list[dict] = []
    lasten: list[float] = []  # je Messung, nicht je Lauf — siehe `readme_text`
    for nummer, (datei, quell_seite) in enumerate(gezogen, start=1):
        quelle = Path(datei)
        bildname = f"seite-{nummer:02d}.png"
        try:
            bild_fuer(quelle, quell_seite, dpi, ordner / bildname)
        except (OcrVergleichFehler, OSError) as fehler:
            protokoll.schreibe({"art": "fehler", "paket_seite": nummer, "datei": quelle.name,
                                "seite": quell_seite, "meldung": str(fehler)})
            continue
        eintrag = {"nummer": nummer, "bild": bildname, "datei": quelle.name,
                   "seite": quell_seite, "ergebnisse": []}
        for engine in engines:
            last = os.getloadavg()[0]
            lasten.append(last)
            start = time.perf_counter()
            try:
                text, konfidenz = SCAN_ENGINES[engine](ordner / bildname)
            except Exception as fehler:  # noqa: BLE001 - jede Engine darf scheitern, nie still
                protokoll.schreibe({"art": "fehler", "engine": engine, "paket_seite": nummer,
                                    "datei": quelle.name, "seite": quell_seite,
                                    "meldung": f"{type(fehler).__name__}: {fehler}"})
                eintrag["ergebnisse"].append(
                    {"engine": engine, "text": f"[Engine-Fehler: {type(fehler).__name__}]"}
                )
                continue
            protokoll.schreibe(protokollzeile(
                engine=engine, quelle=quelle, seite=quell_seite, nummer=nummer, text=text,
                konfidenz=konfidenz, sekunden=time.perf_counter() - start, loadavg=last,
            ))
            eintrag["ergebnisse"].append({"engine": engine, "text": text})
        seiten.append(eintrag)
        print(f"Seite {nummer}/{len(gezogen)} fertig")
    return seiten, lasten


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--korpus", type=Path, required=True)
    parser.add_argument("--seiten", type=int, default=STANDARD_SEITEN)
    parser.add_argument("--seed", type=int, default=STANDARD_SEED)
    parser.add_argument("--dpi", type=int, default=STANDARD_DPI)
    parser.add_argument("--engines", nargs="+", default=list(STANDARD_ENGINES))
    parser.add_argument("--ausgabe", type=Path, default=Path("beweise/ocr-scans"))
    args = parser.parse_args(argv)

    if not args.korpus.is_dir():
        raise OcrVergleichFehler("--korpus <ordner> fehlt oder ist kein Ordner")
    engines = _pruefe_engines(args.engines)
    if not engines:
        raise OcrVergleichFehler("Keine Engine verfuegbar — nichts zu messen")
    gezogen = ziehe(args.korpus, args.seiten, args.seed)
    if not gezogen:
        raise OcrVergleichFehler("Keine OCR-pflichtige Quelle im Korpus gefunden")
    datum = date.today().isoformat()
    ordner = args.ausgabe / datum
    ordner.mkdir(parents=True, exist_ok=True)
    last = os.getloadavg()[0]
    protokoll = Protokoll(ordner / "laeufe.jsonl")
    protokoll.schreibe({
        "art": "lauf", "beginn": datetime.now().isoformat(timespec="seconds"),
        "korpus": str(args.korpus), "engines": list(engines), "dpi": args.dpi,
        "seed": args.seed, "seiten_geplant": len(gezogen),
        "loadavg_beginn": round(last, 2),
        "dauer_unter_fremdlast": last >= FREMDLAST,
        "ziehung": [{"paket_seite": n, "datei": Path(d).name, "seite": s}
                    for n, (d, s) in enumerate(gezogen, start=1)],
    })
    try:
        seiten, lasten = messe(gezogen, engines, args.dpi, ordner, protokoll)
    finally:
        protokoll.schliesse()
    print(f"Paket: {baue_paket(seiten, engines, ordner, datum, lasten)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

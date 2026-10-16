"""Auswertung und Bericht des OCR-Vergleichs — liest nur `laeufe.jsonl`, misst selbst nichts.

Getrennt von `ocr_vergleich.py`, weil Messen und Beurteilen zwei Schritte sind: hier laeuft
keine Engine, kein Renderer und kein Korpus. Alles in diesem Modul arbeitet auf den bereits
geschriebenen Protokollzeilen und ist damit ohne Messlauf wiederholbar — ein Bericht laesst
sich jederzeit neu bauen (`--bericht <ordner>`), ohne eine einzige Seite erneut zu lesen.

Der Bericht enthaelt **keinen Dokumentinhalt** — nur Dateiname, Seitenzahl und Kennzahlen.
"""
from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from pathlib import Path

BRUCHSTELLEN = 10  # "Wo es bricht": so viele Seiten mit der hoechsten CER je Engine

def kennzahlen(werte: Sequence[float]) -> dict[str, float | None]:
    """Median, Mittel und P90 einer Messreihe; leere Reihe ergibt `None`."""
    if not werte:
        return {"median": None, "mittel": None, "p90": None}
    sortiert = sorted(werte)
    rang = min(len(sortiert) - 1, round(0.9 * (len(sortiert) - 1)))
    return {
        "median": statistics.median(sortiert),
        "mittel": statistics.fmean(sortiert),
        "p90": sortiert[rang],
    }



def fasse_zusammen(zeilen: Sequence[dict], engine: str) -> dict:
    """Eine Zusammenfassungszeile je Engine: CER/WER-Kennzahlen, Zahlentreue, Dauer."""
    eigene = [z for z in zeilen if z.get("engine") == engine and z.get("art") == "seite"]
    zusammen = {"art": "engine", "engine": engine, "seiten": len(eigene),
                "fehler": sum(1 for z in zeilen if z.get("engine") == engine and z.get("art") == "fehler")}
    for feld in ("cer", "wer", "wort_f1", "ngramm_f1", "ocr_sekunden", "render_sekunden"):
        werte = [z[feld] for z in eigene if z.get(feld) is not None]
        for name, wert in kennzahlen(werte).items():
            zusammen[f"{feld}_{name}"] = round(wert, 4) if wert is not None else None
    for feld in ("zahlen_gefunden", "zahlen_verfehlt", "zahlen_erfunden",
                 "daten_gefunden", "daten_verfehlt", "daten_erfunden"):
        zusammen[feld] = sum(z.get(feld, 0) for z in eigene)
    return zusammen


WENIGER_IST_BESSER = ("cer", "wer")


def paarweise(seiten: Sequence[dict], basis: str, engine: str, feld: str) -> dict:
    """Vergleich **je Seite** gegen `basis`, nicht Median gegen Median.

    Das ist die Form, die am 23.09.2026 die Entscheidung gedreht hat: die Mediane lagen in
    der dritten Nachkommastelle auseinander und behaupteten eine Rangfolge, die der
    Einzelvergleich nicht hergab (CER paarweise 73 zu 74 — ein Muenzwurf). Da alle Engines
    **dieselben** Seiten lesen, ist der gepaarte Vergleich der richtige Schnitt: er misst,
    auf wie vielen Seiten die eine Engine die andere schlaegt, statt wie hoch einzelne
    Ausreisser sind.

    `delta` ist immer als "Gewinn der neuen Engine" orientiert: bei F1 `engine - basis`,
    bei CER/WER `basis - engine`. Positiv heisst damit in jeder Zeile dasselbe.
    """
    werte: dict[str, dict[tuple[str, int], float]] = {basis: {}, engine: {}}
    for zeile in seiten:
        if zeile.get("art") == "seite" and zeile.get("engine") in werte and zeile.get(feld) is not None:
            werte[zeile["engine"]][(zeile["datei"], zeile["seite"])] = zeile[feld]
    gemeinsam = sorted(werte[basis].keys() & werte[engine].keys())
    vorzeichen = -1.0 if feld in WENIGER_IST_BESSER else 1.0
    deltas = [vorzeichen * (werte[engine][s] - werte[basis][s]) for s in gemeinsam]
    return {
        "basis": basis, "engine": engine, "feld": feld, "seiten": len(deltas),
        "besser": sum(1 for d in deltas if d > 0),
        "gleich": sum(1 for d in deltas if d == 0),
        "schlechter": sum(1 for d in deltas if d < 0),
        "delta_median": statistics.median(deltas) if deltas else None,
        "delta_mittel": statistics.fmean(deltas) if deltas else None,
    }



# ========================================================================== Bericht


def _quote(zusammen: dict, feld: str) -> str:
    gesamt = zusammen[f"{feld}_gefunden"] + zusammen[f"{feld}_verfehlt"]
    if not gesamt:
        return "—"
    anteil = 100 * zusammen[f"{feld}_gefunden"] / gesamt
    return f"{anteil:.1f} % ({zusammen[f'{feld}_gefunden']}/{gesamt})"


def _zahl(wert, nachkomma: int = 4) -> str:
    return "—" if wert is None else f"{wert:.{nachkomma}f}"


def schreibe_bericht(ordner: Path) -> Path:
    """Liest `laeufe.jsonl` und schreibt `bericht.md` — ohne jeden Dokumentinhalt."""
    zeilen = [json.loads(z) for z in (ordner / "laeufe.jsonl").read_text("utf-8").splitlines() if z]
    alle = [z for z in zeilen if z.get("art") == "seite"]
    engines = list(dict.fromkeys(z["engine"] for z in zeilen if z.get("engine")))
    seiten = gemeinsame_seiten(alle, engines)
    gemeinsam = len({(z["datei"], z["seite"]) for z in seiten})
    teile = [f"# OCR-Vergleich {ordner.name}", "",
             f"Seitenmessungen: {len(alle)} | Engines: {', '.join(engines) or '—'}",
             f"Ausgewertet werden die **{gemeinsam} Seiten, die jede Engine gemessen hat** "
             "(Schnittmenge) — sonst staenden Mediane ueber verschiedene Seitenmengen "
             "nebeneinander.", "",
             *_laeufe(zeilen),
             "## Kennzahlen je Engine", "",
             ("| Engine | Seiten | CER Median | CER P90 | WER Median | Zahlentreue | Datumstreue"
              " | Zahlen erfunden | OCR s/Seite | Render s/Seite |"),
             "|---|---|---|---|---|---|---|---|---|---|"]
    for engine in engines:
        z = fasse_zusammen(seiten, engine)
        teile.append(
            f"| {engine} | {z['seiten']} | {_zahl(z['cer_median'])} | {_zahl(z['cer_p90'])} | "
            f"{_zahl(z['wer_median'])} | {_quote(z, 'zahlen')} | {_quote(z, 'daten')} | "
            f"{z['zahlen_erfunden']} | {_zahl(z['ocr_sekunden_median'], 2)} | "
            f"{_zahl(z['render_sekunden_median'], 2)} |"
        )
    teile += (_reihenfolge(seiten, engines) + _paarweise_tabelle(seiten, engines)
              + _bruchstellen(seiten, engines) + _laufzeitprobe(zeilen, engines))
    ziel = ordner / "bericht.md"
    ziel.write_text("\n".join(teile) + "\n", encoding="utf-8")
    return ziel


def _laeufe(zeilen: Sequence[dict]) -> list[str]:
    """Messbedingungen je Lauf — damit im Bericht steht, welche Stichprobe gemessen wurde.

    Ohne diese Zeile ist "gleiche Stichprobe wie am 23.09." eine Behauptung: Seed, Seitenzahl,
    Aufloesung und Engine-Liste entscheiden, ob zwei Laeufe ueberhaupt vergleichbar sind.
    """
    laeufe = [z for z in zeilen if z.get("art") == "lauf"]
    uebernahmen = [
        f"* Uebernommen aus `{z['quelle']}`: {z['zeilen']} Seitenzeile(n) fuer "
        f"{', '.join(z['engines'])} — nicht neu gemessen, damit die Stichprobe dieselbe bleibt."
        + (f" **{z['fehlend']} Paar(e) fehlen.**" if z.get("fehlend") else "")
        for z in zeilen if z.get("art") == "uebernahme"
    ]
    if not laeufe:
        return []
    teile = ["## Messbedingungen", "",
             "| Beginn | Modus | Engines | Seiten geplant | dpi | Seed | min. Zeichen |",
             "|---|---|---|---|---|---|---|"]
    teile += [
        f"| {z.get('beginn', '—')} | {z.get('modus', '—')} | {', '.join(z.get('engines', []))} | "
        f"{z.get('seiten_geplant', '—')} | {z.get('dpi', '—')} | {z.get('seed', '—')} | "
        f"{z.get('min_zeichen', '—')} |"
        for z in laeufe
    ]
    return [*teile, "", *uebernahmen, ""] if uebernahmen else [*teile, ""]


def gemeinsame_seiten(seiten: Sequence[dict], engines: Sequence[str]) -> list[dict]:
    """Nur die Seiten, die **jede** Engine gemessen hat.

    Ohne diesen Schnitt vergliche die Tabelle Mediane ueber verschiedene Seitenmengen: der
    Lauf vom 23.09.2026 endete unter Fremdlast nach 100 von 150 Seiten, waehrend die
    uebernommenen Engines 144 Seiten mitbringen. Ein Median ueber 144 andere Seiten ist
    keine Vergleichsgroesse zu einem Median ueber 100 — auch dann nicht, wenn beide Zahlen
    in derselben Zeile stehen.

    Zugleich bleibt je Engine und Seite **genau eine** Zeile stehen (die erste). Das
    Protokoll fuehrt `pdf.name`, und der Korpus enthaelt gleichnamige Dateien in
    verschiedenen Ordnern: gemessen ohne Entdopplung standen 99 Zeilen auf 96 Schluesseln,
    waehrend die uebernommenen Engines schon entdoppelt waren. Drei doppelt gewichtete
    Seiten in der einen Spalte und nicht in der anderen sind genau die Sorte stiller
    Ungleichheit, die ein Median nicht mehr erkennen laesst.
    """
    je_seite: dict[tuple[str, int], set[str]] = {}
    for zeile in seiten:
        je_seite.setdefault((zeile["datei"], zeile["seite"]), set()).add(zeile["engine"])
    gut = {s for s, gemessen in je_seite.items() if gemessen >= set(engines)}
    behalten: list[dict] = []
    gesehen: set[tuple[str, str, int]] = set()
    for zeile in seiten:
        schluessel = (zeile["engine"], zeile["datei"], zeile["seite"])
        if (zeile["datei"], zeile["seite"]) in gut and schluessel not in gesehen:
            gesehen.add(schluessel)
            behalten.append(zeile)
    return behalten


TRAGFAEHIG = 0.3  # CER-Schwelle, unter der die Referenz als Massstab belastbar ist


def tragfaehige_seiten(seiten: Sequence[dict], engines: Sequence[str]) -> list[dict]:
    """Die Seiten, auf denen **jede** Engine eine CER <= `TRAGFAEHIG` erreicht.

    Liegt die CER bei allen Engines zugleich hoch, ist nicht die OCR schlecht, sondern die
    Referenz in anderer Reihenfolge geschrieben (Befund 23.09.2026). Diese Teilmenge ist
    also der Rest, auf dem die alte Leitkennzahl ueberhaupt trug — sie wird getrennt
    ausgewiesen, damit sichtbar bleibt, wo CER etwas misst und wo Layout.
    """
    je_seite: dict[tuple[str, int], list[dict]] = {}
    for zeile in seiten:
        je_seite.setdefault((zeile["datei"], zeile["seite"]), []).append(zeile)
    gut = {
        schluessel
        for schluessel, gruppe in je_seite.items()
        if {z["engine"] for z in gruppe} >= set(engines)
        and all(z.get("cer") is not None and z["cer"] <= TRAGFAEHIG for z in gruppe)
    }
    return [z for z in seiten if (z["datei"], z["seite"]) in gut]


def _reihenfolge(seiten: Sequence[dict], engines: Sequence[str]) -> list[str]:
    """Leitkennzahl-Tabelle: F1 ueber Wort- und Trigramm-Multimengen, reihenfolge-unabhaengig."""
    teile = [
        "", "## Reihenfolge-unabhaengige Kennzahlen (Leitkennzahl)", "",
        "F1 ueber Wort- und Zeichen-Trigramm-Multimengen — Median ueber die Seiten. Anders als",
        "CER/WER zaehlen sie eine abweichende Lesereihenfolge nicht als Fehler. CER steht zum",
        "Vergleich daneben, ist hier aber Nebenkennzahl (siehe Modul-Docstring).", "",
    ]
    for titel, gruppe in (("Alle Seiten", list(seiten)),
                          ("Tragfaehige Teilmenge (alle Engines CER <= 0,3)",
                           tragfaehige_seiten(seiten, engines))):
        teile += [f"### {titel}", "",
                  ("| Engine | Seiten | F1 Wort | F1 Trigramm | CER Median | Zahlentreue |"
                   " Zahlen erfunden | OCR s/Seite |"),
                  "|---|---|---|---|---|---|---|---|"]
        for engine in engines:
            z = fasse_zusammen(gruppe, engine)
            teile.append(
                f"| {engine} | {z['seiten']} | {_zahl(z['wort_f1_median'])} | "
                f"{_zahl(z['ngramm_f1_median'])} | {_zahl(z['cer_median'])} | "
                f"{_quote(z, 'zahlen')} | {z['zahlen_erfunden']} | "
                f"{_zahl(z['ocr_sekunden_median'], 2)} |"
            )
        teile.append("")
    return teile


BASIS_ENGINE = "tesseract"  # der heutige Produktpfad — gegen den wird verglichen


def _paarweise_tabelle(seiten: Sequence[dict], engines: Sequence[str]) -> list[str]:
    """Seite gegen Seite gegen `tesseract` — die Form, die die Entscheidung traegt."""
    gegner = [e for e in engines if e != BASIS_ENGINE]
    if BASIS_ENGINE not in engines or not gegner:
        return []
    teile = [
        "", f"## Paarweise je Seite gegen `{BASIS_ENGINE}`", "",
        "Alle Engines lesen dieselben Seiten, also wird auch je Seite verglichen. Delta ist",
        "immer als Gewinn der neuen Engine orientiert (bei CER/WER umgedreht, dort ist",
        "weniger besser). Median gegen Median steht in der Tabelle darueber.", "",
        "| Engine | Kennzahl | Seiten | Δ Median | Δ Mittel | besser | gleich | schlechter |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for engine in gegner:
        for feld in ("wort_f1", "ngramm_f1", "cer"):
            v = paarweise(seiten, BASIS_ENGINE, engine, feld)
            teile.append(
                f"| {engine} | {feld} | {v['seiten']} | {_zahl(v['delta_median'])} | "
                f"{_zahl(v['delta_mittel'])} | {v['besser']} | {v['gleich']} | {v['schlechter']} |"
            )
    return [*teile, ""]


def _bruchstellen(seiten: Sequence[dict], engines: Sequence[str]) -> list[str]:
    teile = ["", "## Wo es bricht", "",
             f"Die {BRUCHSTELLEN} Seiten mit der hoechsten CER je Engine (kein Textinhalt).", ""]
    for engine in engines:
        eigene = sorted((z for z in seiten if z["engine"] == engine and z.get("cer") is not None),
                        key=lambda z: z["cer"], reverse=True)[:BRUCHSTELLEN]
        if not eigene:
            continue
        teile += [f"### {engine}", "", "| Datei | Seite | CER | WER | Zahlen verfehlt | Zahlen erfunden |",
                  "|---|---|---|---|---|---|"]
        teile += [
            f"| {z['datei']} | {z['seite']} | {_zahl(z['cer'])} | {_zahl(z['wer'])} | "
            f"{z.get('zahlen_verfehlt', 0)} | {z.get('zahlen_erfunden', 0)} |"
            for z in eigene
        ]
        teile.append("")
    return teile


def _laufzeitprobe(zeilen: Sequence[dict], engines: Sequence[str]) -> list[str]:
    proben = [z for z in zeilen if z.get("art") == "laufzeitprobe"]
    if not proben:
        return []
    teile = ["", "## Laufzeitprobe (PDFs ohne Textebene, keine Wahrheit)", "",
             "| Engine | Seiten | OCR s/Seite Median | Seiten ohne Text | Zeichen Median |",
             "|---|---|---|---|---|"]
    for engine in engines:
        eigene = [z for z in proben if z["engine"] == engine]
        if not eigene:
            continue
        dauer = kennzahlen([z["ocr_sekunden"] for z in eigene])
        zeichen = kennzahlen([z["zeichen_ocr"] for z in eigene])
        leer = sum(1 for z in eigene if z["zeichen_ocr"] == 0)
        teile.append(f"| {engine} | {len(eigene)} | {_zahl(dauer['median'], 2)} | {leer} | "
                     f"{_zahl(zeichen['median'], 0)} |")
    return teile


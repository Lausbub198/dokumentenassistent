"""Textkennzahlen des OCR-Vergleichs — reine Funktionen ohne Zustand, ohne Ein-/Ausgabe.

Getrennt von `ocr_vergleich.py`, weil sie das Einzige sind, was ein Leser nachrechnen koennen
muss, um dem Befund zu glauben: hier steht, *wie* aus Referenz und OCR-Text eine Zahl wird.
Kein Korpus, keine Engine, kein Dateisystem — jede Funktion ist an einem Zweizeiler pruefbar
und wird es in `tests/test_ocr_vergleich.py` auch.

Fairness der Normalisierung: Referenz und OCR-Text laufen durch **dieselbe** Funktion
`normalisiere`. Sie kennt die Herkunft des Textes nicht und kann deshalb keine Engine
bevorzugen; sie entfernt nur Unterschiede, die keine Lesefehler sind (Ligatur `fi`, harte
Zeilenumbrueche, typografische gegen gerade Anfuehrungszeichen).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from datetime import date

ZEICHEN_ERSATZ = {
    "„": '"', "“": '"', "”": '"', "‟": '"', "«": '"', "»": '"',
    "‚": "'", "‘": "'", "’": "'", "‛": "'",
    "–": "-", "—": "-", "‐": "-", "‑": "-", "−": "-",
    "…": "...",
}
DATUM_PUNKT = re.compile(r"(?<!\d)(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{2,4})(?!\d)")
DATUM_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
ZAHL = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\d.,])")

def normalisiere(text: str) -> str:
    """Vergleichsform: NFKC, vereinheitlichte Anfuehrungszeichen/Striche, gefalteter Leerraum.

    Trifft Referenz und OCR-Text gleich (dieselbe Funktion, kein Herkunftswissen) und kann
    deshalb keine Engine bevorzugen. Idempotent.
    """
    gefaltet = unicodedata.normalize("NFKC", text)
    ersetzt = "".join(ZEICHEN_ERSATZ.get(zeichen, zeichen) for zeichen in gefaltet)
    return " ".join(ersetzt.split())


def levenshtein(a: Sequence, b: Sequence) -> int:
    """Editierdistanz, iterativ ueber zwei Zeilen — O(min(len)) Speicher, kein Fremdpaket.

    Arbeitet auf Zeichen (str) wie auf Wortlisten (list[str]).
    """
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    vorige = list(range(len(b) + 1))
    for i, zeichen_a in enumerate(a, start=1):
        aktuelle = [i]
        for j, zeichen_b in enumerate(b, start=1):
            aktuelle.append(
                min(
                    vorige[j] + 1,
                    aktuelle[j - 1] + 1,
                    vorige[j - 1] + (zeichen_a != zeichen_b),
                )
            )
        vorige = aktuelle
    return vorige[-1]


def cer(referenz: str, hypothese: str) -> float | None:
    """Zeichenfehlerrate = Editierdistanz / Referenzlaenge. `None`, wenn die Referenz leer ist."""
    soll, ist = normalisiere(referenz), normalisiere(hypothese)
    if not soll:
        return None
    return levenshtein(soll, ist) / len(soll)


def wer(referenz: str, hypothese: str) -> float | None:
    """Wortfehlerrate = Editierdistanz auf Wortlisten / Wortzahl der Referenz."""
    soll, ist = normalisiere(referenz).split(), normalisiere(hypothese).split()
    if not soll:
        return None
    return levenshtein(soll, ist) / len(soll)


def _f1_aus_multimengen(soll: Counter, ist: Counter, praefix: str) -> dict[str, float | None]:
    """Praezision, Ausbeute und F1 ueber die gemeinsamen Vorkommen zweier Multimengen.

    **Multimenge, nicht Menge**: ein Wort (bzw. Trigramm), das dreimal auf dem Papier steht,
    muss dreimal gelesen werden. Eine Menge wuerde `900 900 900` und `900` gleich bewerten —
    genau die Wiederholung, die bei Betraegen in Tabellen den Unterschied macht, verschwaende
    aus der Rechnung. `Counter & Counter` nimmt je Element das Minimum und zaehlt damit
    Vorkommen, nicht Typen.

    Leere Referenz -> `None` (wie `cer`: ohne Wahrheit keine Fehlerrate). Leere OCR bei
    vorhandener Referenz -> 0.0, denn nichts gelesen ist ein messbares Ergebnis.
    """
    if not soll:
        return {f"{praefix}_praezision": None, f"{praefix}_ausbeute": None, f"{praefix}_f1": None}
    gemeinsam = sum((soll & ist).values())
    praezision = gemeinsam / sum(ist.values()) if ist else 0.0
    ausbeute = gemeinsam / sum(soll.values())
    summe = praezision + ausbeute
    return {
        f"{praefix}_praezision": praezision,
        f"{praefix}_ausbeute": ausbeute,
        f"{praefix}_f1": 2 * praezision * ausbeute / summe if summe else 0.0,
    }


def wortmengen_kennzahlen(referenz: str, ocr: str) -> dict[str, float | None]:
    """Praezision, Ausbeute und F1 ueber die Wort-**Multimengen** beider Texte.

    Reihenfolge-unabhaengig und damit die Antwort auf den Befund vom 23.09.2026: auf
    mehrspaltigen Seiten und in Tabellen liest die eingebettete Textebene in anderer Folge
    als die OCR. Die Editierdistanz (CER/WER) zaehlt jede Umstellung als Fehler, obwohl jedes
    Zeichen richtig gelesen wurde. Wer dieselben Woerter in anderer Folge liefert, erreicht
    hier 1,0 — und genau das soll die Leitkennzahl nicht bestrafen.

    Normalisiert mit derselben `normalisiere` wie CER/WER (kein Herkunftswissen, keine Engine
    bevorzugt) und teilt wie `wer` am Leerraum.
    """
    return _f1_aus_multimengen(
        Counter(normalisiere(referenz).split()), Counter(normalisiere(ocr).split()), "wort"
    )


def zeichen_ngramm_kennzahlen(referenz: str, ocr: str, n: int = 3) -> dict[str, float | None]:
    """Dasselbe ueber Zeichen-n-Gramme (Vorgabe: Trigramme), ebenfalls als Multimenge.

    Faengt, was die Wortmenge komplett verwirft: `Rechnung` gegen `Rechnunq` ist dort ein
    Totalausfall (F1 0), hier bleiben sechs von acht Trigrammen stehen. Wort- und
    Trigramm-F1 zusammen trennen "andere Reihenfolge" (beide hoch) von "falsch gelesen"
    (beide niedrig) und von "Teilwortfehler" (Wort niedrig, Trigramm hoch).

    Texte kuerzer als `n` liefern keine n-Gramme; eine solche Referenz ergibt `None`.
    """
    def gramme(text: str) -> Counter:
        fest = normalisiere(text)
        return Counter(fest[i : i + n] for i in range(len(fest) - n + 1))

    return _f1_aus_multimengen(gramme(referenz), gramme(ocr), "ngramm")


def datumsangaben(text: str) -> tuple[str, ...]:
    """Alle gueltigen Datumsangaben in ISO-Form, in Textreihenfolge.

    Erkennt `14.08.2026`, `1.9.26` (zweistellig -> 2000er) und `2026-08-14`. Syntaktisch
    passende, aber unmoegliche Werte (`32.13.2026`) sind keine Datumsangaben.
    """
    treffer: list[tuple[int, str]] = []
    for fund in DATUM_PUNKT.finditer(text):
        tag, monat, jahr = (int(teil) for teil in fund.groups())
        iso = _als_iso(jahr, monat, tag)
        if iso:
            treffer.append((fund.start(), iso))
    for fund in DATUM_ISO.finditer(text):
        jahr, monat, tag = (int(teil) for teil in fund.groups())
        iso = _als_iso(jahr, monat, tag)
        if iso:
            treffer.append((fund.start(), iso))
    return tuple(iso for _pos, iso in sorted(treffer))


def _als_iso(jahr: int, monat: int, tag: int) -> str | None:
    jahr = jahr + 2000 if jahr < 100 else jahr
    try:
        return date(jahr, monat, tag).isoformat()
    except ValueError:
        return None


def zahlen(text: str) -> tuple[str, ...]:
    """Alle Zahlen in Vergleichsform, in Textreihenfolge; Datumsangaben bleiben aussen vor.

    Deutsche Schreibweise wird aufgeloest: `1.240,00` -> `1240.00`, `0,5` -> `0.5`. Die
    Vergleichsform ist eine Zeichenkette, keine Zahl — `900` und `900,00` gelten als
    verschiedene Nennungen, weil auf dem Papier verschieden viel steht.
    """
    ohne_datum = _ersetze_datumsangaben(text)
    return tuple(_zahlform(fund.group()) for fund in ZAHL.finditer(ohne_datum))


def _ersetze_datumsangaben(text: str) -> str:
    """Gueltige Datumsangaben durch Leerzeichen ersetzen, damit `14.08.2026` nicht als
    drei Zahlen zaehlt. Positionen bleiben erhalten (gleiche Laenge)."""

    def leeren(fund: re.Match) -> str:
        teile = [int(teil) for teil in fund.groups()]
        jahr, monat, tag = teile if fund.re is DATUM_ISO else (teile[2], teile[1], teile[0])
        return " " * len(fund.group()) if _als_iso(jahr, monat, tag) else fund.group()

    return DATUM_ISO.sub(leeren, DATUM_PUNKT.sub(leeren, text))


def _zahlform(roh: str) -> str:
    return roh.replace(".", "").replace(",", ".")


def zahlentreue(referenz: str, hypothese: str) -> dict[str, int]:
    """Zahlen- und Datumstreue als Multimengen-Vergleich.

    `*_gefunden` zaehlt Nennungen der Referenz, die im OCR-Text stehen; `*_verfehlt` die
    fehlenden; `*_erfunden` Nennungen im OCR-Text, die in der Referenz nicht vorkommen.
    Mehrfachnennungen zaehlen einzeln (Multimenge), weil eine zweimal genannte Summe
    zweimal richtig gelesen werden muss.
    """
    ergebnis: dict[str, int] = {}
    for name, auslesen in (("zahlen", zahlen), ("daten", datumsangaben)):
        soll = Counter(auslesen(normalisiere(referenz)))
        ist = Counter(auslesen(normalisiere(hypothese)))
        gemeinsam = soll & ist
        ergebnis[f"{name}_gefunden"] = sum(gemeinsam.values())
        ergebnis[f"{name}_verfehlt"] = sum((soll - ist).values())
        ergebnis[f"{name}_erfunden"] = sum((ist - soll).values())
    return ergebnis

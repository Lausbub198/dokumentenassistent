"""Seitenrand bereinigen, bevor Seiten zu Fundstellen werden (06.10.2026).

Seitenübergreifende Chunks tragen sonst Kopf-/Fußzeilen und Seitenzahlen mitten in den Absatz.
Gezählt im privaten Bestand (nur Text-PDFs): 19 von 69 mehrseitigen Dokumenten mit wiederkehrenden
Kopf-/Fußzeilen (250 Zeilen), dazu 293 Seitenzahl-Zeilen. Am Produktindex nachgeprüft: in vier der
acht Goldfälle mit Auslesefehler steckten 2–4 fremde Wörter im Zielabsatz.

Regeln, je Dokument, ohne Wissen über den Bestand:
- Rand = die ersten und letzten `RAND_ZEILEN` nicht leeren Zeilen einer Seite.
- Eine Randzeile fällt weg, wenn sie (Ziffern vereinheitlicht) auf mindestens der Hälfte der Seiten,
  wenigstens aber auf drei, am Rand steht.
- Eine Randzeile, die nur eine Seitenzahl ist („Seite 2 von 5“, „- 2 -“, „2/5“, „2“), fällt in
  mehrseitigen Dokumenten immer weg.
- Silbentrennung am Zeilenende wird zusammengeführt („Woh-“ + „nung“), außer vor Bindewörtern
  („Haus-“ + „und Grundbesitz“).
Nichts außerhalb des Rands wird angefasst; Seitennummern und Metadaten bleiben unverändert.
"""
from __future__ import annotations

import dataclasses
import re
from collections import Counter

from dokumentenassistent.typen import Seite

RAND_ZEILEN = 2
_SEITENZAHL = re.compile(r'(?:-\s*)?\d{1,3}(?:\s*-)?|seite\s+\d{1,3}(?:\s*(?:von|/)\s*\d{1,3})?|\d{1,3}\s*/\s*\d{1,3}',
                         re.IGNORECASE)
_BINDEWOERTER = ('und', 'oder', 'bis', 'sowie', 'als', 'wie', 'bzw')
_TRENNUNG = re.compile(r'([a-zäöüß]{2,})-[ \t]*\n[ \t]*(?!(?:' + '|'.join(_BINDEWOERTER) + r')\b)([a-zäöüß])')


def _schluessel(zeile: str) -> str:
    return re.sub(r'\d+', '#', re.sub(r'\s+', ' ', zeile.strip()))


def _rand_indizes(zeilen: list[str]) -> list[int]:
    belegt = [i for i, z in enumerate(zeilen) if z.strip()]
    return sorted(set(belegt[:RAND_ZEILEN] + belegt[-RAND_ZEILEN:]))


def _wiederkehrend(seiten_zeilen: list[list[str]]) -> set[str]:
    zaehler: Counter[str] = Counter()
    for zeilen in seiten_zeilen:
        zaehler.update({_schluessel(zeilen[i]) for i in _rand_indizes(zeilen)})
    grenze = max(3, -(-len(seiten_zeilen) // 2))
    return {k for k, n in zaehler.items() if n >= grenze and len(k) >= 4}


def _ohne_rand(zeilen: list[str], wiederkehrend: set[str]) -> str:
    weg = {i for i in _rand_indizes(zeilen)
           if _schluessel(zeilen[i]) in wiederkehrend or _SEITENZAHL.fullmatch(zeilen[i].strip())}
    return '\n'.join(z for i, z in enumerate(zeilen) if i not in weg)


def bereinige_seiten(seiten: tuple[Seite, ...]) -> tuple[Seite, ...]:
    """Kopf-/Fußzeilen und Seitenzahlen am Seitenrand entfernen, Silbentrennung zusammenführen."""
    seiten_zeilen = [s.text.split('\n') for s in seiten]
    mehrseitig = sum(bool(s.text.strip()) for s in seiten) >= 2
    wiederkehrend = _wiederkehrend(seiten_zeilen) if mehrseitig else set()
    raus = []
    for seite, zeilen in zip(seiten, seiten_zeilen):
        text = _ohne_rand(zeilen, wiederkehrend) if mehrseitig else seite.text
        text = _TRENNUNG.sub(r'\1\2', text)
        raus.append(seite if text == seite.text else dataclasses.replace(seite, text=text))
    return tuple(raus)

"""M8 — deterministische Zitatprüfung.

Entscheidet, ob ein vom Modell behaupteter Beleg wörtlich in seiner
Fundstelle steht. Kein Modell, keine Heuristik über "ähnlich genug" —
nur Substring-Vergleich nach fester Normalisierung.
"""
from __future__ import annotations

import re
from typing import Mapping

from dokumentenassistent.typen import Beleg, Feld, Fundstelle

_TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN = str.maketrans(
    {
        "„": '"',  # „
        "“": '"',  # “
        "”": '"',  # ”
        "‚": "'",  # ‚
        "‘": "'",  # ‘
        "’": "'",  # ’
    }
)


def normalisiere(text: str) -> str:
    """lower, Whitespace-Folgen zu einem Leerzeichen, gerade Anführungszeichen, strip."""
    text = text.translate(_TYPOGRAFISCHE_ANFUEHRUNGSZEICHEN).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def pruefe_beleg(beleg: Beleg, fundstellen: Mapping[str, Fundstelle]) -> bool:
    """True nur, wenn die Fundstelle existiert und der normalisierte Wortlaut darin steht."""
    fundstelle = fundstellen.get(beleg.fundstelle_id)
    if fundstelle is None:
        return False
    wortlaut = normalisiere(beleg.wortlaut)
    if not wortlaut:
        return False
    return wortlaut in normalisiere(fundstelle.text)


_WERT_OHNE_WORTLAUTPRUEFUNG = frozenset({"datum"})  # ISO-Datum vs. "14.05.2025" im Text


def pruefe_wert(feld: Feld) -> bool:
    """Der Wert muss nicht leer sein und — außer bei Datumsfeldern — im zitierten Wortlaut stehen.

    Verhindert, dass ein Modell einen gültigen Wortlaut zitiert und daneben einen
    erfundenen Wert setzt („rechnungsnummer: unbekannt" zu „Vertragsnummer 2024-MV-77").
    """
    if feld.wert is None or not normalisiere(feld.wert):
        return False
    if feld.name in _WERT_OHNE_WORTLAUTPRUEFUNG or feld.beleg is None:
        return feld.beleg is not None
    return normalisiere(feld.wert) in normalisiere(feld.beleg.wortlaut)


def pruefe_felder(felder: tuple[Feld, ...], fundstellen: Mapping[str, Fundstelle]) -> tuple[Feld, ...]:
    """Neues Tupel: gültige Felder unverändert, ungültige zu Feld(wert=None, beleg=None, status='unklar')."""
    geprueft = []
    for feld in felder:
        if feld.beleg is not None and pruefe_beleg(feld.beleg, fundstellen) and pruefe_wert(feld):
            geprueft.append(feld)
        else:
            geprueft.append(Feld(name=feld.name, wert=None, beleg=None, status="unklar"))
    return tuple(geprueft)

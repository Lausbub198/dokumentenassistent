"""Belegte Einordnungsmetadaten als schwaches, optionales Suchsignal.

Der Bonus wirkt auf Kosinus-Scores vor dem Reranking. Kein Kandidat wird entfernt.
`gewicht=0` erhält die ursprüngliche Rangliste bytegenau für Vergleichsmessungen.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from dokumentenassistent.suche import Rangliste
from dokumentenassistent.typen import Fundstelle, Vorschlag

_JAHR = re.compile(r"\b(?:19|20)\d{2}\b")
_WORT = re.compile(r"[\wäöüß]+", re.IGNORECASE)
_ALLGEMEIN = frozenset({"gmbh", "mbh", "ag", "kg", "und", "der", "die", "das", "von"})


def _tokens(text: str) -> frozenset[str]:
    return frozenset(w.casefold() for w in _WORT.findall(text) if len(w) >= 4)


def _signale(frage: str, vorschlag: Vorschlag) -> int:
    frage_tokens = _tokens(frage)
    frage_jahre = set(_JAHR.findall(frage))
    signale = 0
    if vorschlag.typ and frage_tokens.intersection(_tokens(vorschlag.typ)):
        signale += 1
    for feld in vorschlag.felder:
        if feld.status != "belegt" or not feld.wert:
            continue
        if feld.name == "datum" and frage_jahre.intersection(_JAHR.findall(feld.wert)):
            signale += 1
        elif feld.name == "aussteller" and frage_tokens.intersection(_tokens(feld.wert) - _ALLGEMEIN):
            signale += 1
    return min(signale, 3)


def bonus_rang(
    frage: str,
    rangliste: Rangliste,
    fundstellen_je_id: Mapping[str, Fundstelle],
    vorschlaege_je_hash: Mapping[str, Vorschlag],
    gewicht: float,
) -> Rangliste:
    """Addiert `gewicht` je passendem Typ, belegtem Datum oder Aussteller.

    Fehlende/unklare Felder geben keinen Bonus. Die Eingangsmenge bleibt erhalten;
    ein abweichendes Jahr ist kein Negativsignal.
    """
    if gewicht < 0:
        raise ValueError("Metadaten-Gewicht darf nicht negativ sein")
    if gewicht == 0 or not frage.strip() or not rangliste:
        return rangliste
    bewertet = []
    for position, (id_, score) in enumerate(rangliste):
        fundstelle = fundstellen_je_id.get(id_)
        vorschlag = vorschlaege_je_hash.get(fundstelle.datei_hash) if fundstelle else None
        bonus = gewicht * _signale(frage, vorschlag) if vorschlag else 0.0
        bewertet.append((id_, score + bonus, position))
    bewertet.sort(key=lambda eintrag: (-eintrag[1], eintrag[2]))
    return tuple((id_, score) for id_, score, _ in bewertet)

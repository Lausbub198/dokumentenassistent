"""Orte für private Messdaten — nie im Repository.

Die Mess- und Vergleichsskripte (``praefix_test``, ``embedding_vergleich``, ``gold_*`` und andere)
lesen echte Unterlagen und Fragenlisten. Die gehören nicht in ein öffentliches Repo und haben
deshalb keinen festen Ort. Jeden der fünf Ordner setzt man über eine Umgebungsvariable; ohne
Angabe gilt ein Unterordner von ``~/dokass-privat``.

    DOKASS_BESTAND      echte Unterlagen für Messläufe
    DOKASS_ARBEIT       Arbeitsordner (Einordnung) zum Bestand
    DOKASS_FRAGEN       Fragenlisten (golden*.json)
    DOKASS_LAEUFE       Protokolle und Zwischenstände der Läufe
    DOKASS_GERMANQUAD   GermanQuAD-Korpus
"""
from __future__ import annotations

import os
from pathlib import Path

_WURZEL = Path.home() / "dokass-privat"


def _ort(variable: str, unterordner: str) -> Path:
    gesetzt = os.environ.get(variable)
    return Path(gesetzt).expanduser() if gesetzt else _WURZEL / unterordner


BESTAND = _ort("DOKASS_BESTAND", "bestand")
ARBEIT = _ort("DOKASS_ARBEIT", "arbeit")
FRAGEN = _ort("DOKASS_FRAGEN", "fragen")
LAEUFE = _ort("DOKASS_LAEUFE", "laeufe")
GERMANQUAD = _ort("DOKASS_GERMANQUAD", "germanquad")

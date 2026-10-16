"""Gemeinsame Datentypen. Alle Module tauschen ausschließlich diese Typen aus.

Unveränderlich (frozen): Ein Modul erzeugt neue Objekte, es verändert keine.
Datei-Originale werden nie angefasst; `Datei.pfad` ist nur ein Verweis.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["sicher", "unklar", "konflikt", "duplikat", "ocr_unsicher"]
# belegt = Wert mit geprüftem Zitat · unklar = behauptet, aber Zitat/Wert hält nicht ·
# fehlt = das Modell hat für dieses Profilfeld nichts geliefert (kein gebrochener Beleg)
FeldStatus = Literal["belegt", "unklar", "fehlt"]
KonfliktVorschlag = Literal["ersetzt", "verschiedene_sachverhalte", "nicht_entscheidbar"]
KonfliktEntscheidung = Literal["ersetzt", "verschiedene_sachverhalte", "nicht_entscheidbar", "eigener_wert"]
AntwortStatus = Literal["gefunden", "nicht_gefunden", "widerspruechlich"]


class DokumentenassistentFehler(Exception):
    """Basisklasse aller fachlichen Fehler des Werkzeugs."""


@dataclass(frozen=True)
class Datei:
    hash: str  # SHA-256 hex
    pfad: Path  # Originalpfad, wird nie verändert
    name: str
    groesse: int


@dataclass(frozen=True)
class Seite:
    nummer: int  # 1-basiert
    text: str
    per_ocr: bool
    sicherheit: float | None  # 0.0–1.0, nur bei OCR
    extraktor: str | None = None
    extraktor_version: str | None = None


@dataclass(frozen=True)
class SeitenSpanne:
    seite: int
    start: int
    ende: int


@dataclass(frozen=True)
class Fundstelle:
    id: str  # document hash + page + paragraph + text hash; display name separate
    datei_hash: str
    datei_name: str
    seite: int
    absatz: int
    text: str
    spannen: tuple[SeitenSpanne, ...] = ()

    @property
    def seiten(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(span.seite for span in self.spannen)) if self.spannen else (self.seite,)


@dataclass(frozen=True)
class Beleg:
    fundstelle_id: str
    wortlaut: str  # muss wörtlich im Fundstellen-Text stehen


@dataclass(frozen=True)
class Feld:
    name: str
    wert: str | None
    beleg: Beleg | None
    status: FeldStatus


@dataclass(frozen=True)
class Profil:
    zweck: str
    kategorien: tuple[str, ...]
    dokumenttypen: tuple[str, ...]
    felder: tuple[str, ...]  # z. B. ("datum", "aussteller", "betrag", "rechnungsnummer")
    namensschema: str  # z. B. "{datum}_{typ}_{aussteller}"
    eigentuemer: str | None = None  # wessen Bestand: entscheidet ein- vs. ausgehend


@dataclass(frozen=True)
class Vorschlag:
    datei_hash: str
    datei_name: str
    kategorie: str | None
    typ: str | None
    felder: tuple[Feld, ...]
    zielname: str | None
    status: Status
    begruendung: str = ""


@dataclass(frozen=True)
class Konflikt:
    id: str
    feld: str
    hash_a: str
    hash_b: str
    wert_a: str
    wert_b: str
    beleg_a: Beleg
    beleg_b: Beleg
    vorschlag: KonfliktVorschlag
    entscheidung: KonfliktEntscheidung | None = None
    eigener_wert: str | None = None


@dataclass(frozen=True)
class Belegkarte:
    fundstelle: Fundstelle
    wortlaut: str


@dataclass(frozen=True)
class Stuetzungspruefung:
    """Separate from source identity and conflict status; no implicit entailment."""

    status: Literal['unterstuetzt', 'widersprochen', 'ungeprueft'] = 'ungeprueft'
    verfahren: str = 'keine_semantische_pruefung'

    def __post_init__(self):
        if self.status not in {'unterstuetzt', 'widersprochen', 'ungeprueft'}:
            raise ValueError('Unbekannter Stützungsstatus')
        if not self.verfahren.strip() or (
            self.status != 'ungeprueft' and self.verfahren == 'keine_semantische_pruefung'
        ):
            raise ValueError('Stützungsurteil benötigt ein dokumentiertes Prüfverfahren')


@dataclass(frozen=True)
class Antwort:
    """`gefunden` means accepted context citations, not verified answer content."""
    status: AntwortStatus
    text: str
    karten: tuple[Belegkarte, ...]
    stuetzung: Stuetzungspruefung = Stuetzungspruefung()
    # Gesetzt, wenn die Antwort nicht in der eingestellten Sprache ist (sprache.py).
    sprachhinweis: str | None = None

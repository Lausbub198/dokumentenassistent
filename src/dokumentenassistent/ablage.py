"""Kopien bestätigter Vorschläge in die Zielablage. Originale werden nie
bewegt, umbenannt, überschrieben oder gelöscht — es entstehen ausschließlich
Kopien (shutil.copy2, byte- und mtime-gleich)."""
from __future__ import annotations

import shutil
from pathlib import Path

from dokumentenassistent.typen import DokumentenassistentFehler, Datei, Vorschlag


class AblageFehler(DokumentenassistentFehler):
    """Fachlicher Fehler bei der Ablage einer Kopie."""


def _pruefe_status(vorschlag: Vorschlag) -> None:
    if vorschlag.status != "sicher":
        raise AblageFehler(f"Vorschlag mit Status '{vorschlag.status}' ist unklar oder nicht bestätigt")


def _pruefe_zielname(vorschlag: Vorschlag) -> str:
    if not vorschlag.zielname:
        raise AblageFehler("Zielname fehlt")
    return vorschlag.zielname


def _pruefe_kategorie(vorschlag: Vorschlag) -> str:
    kategorie = vorschlag.kategorie
    if not kategorie or "/" in kategorie or "\\" in kategorie or ".." in kategorie:
        raise AblageFehler(f"Kategorie ist ungültig: {kategorie!r}")
    return kategorie


def _pruefe_original(datei: Datei) -> None:
    if not datei.pfad.exists():
        raise AblageFehler(f"Original nicht gefunden: {datei.pfad}")


def _pruefe_ziel_ausserhalb_quelle(quellordner: Path, zielablage: Path) -> None:
    ziel_resolved = zielablage.resolve()
    quelle_resolved = quellordner.resolve()
    if ziel_resolved == quelle_resolved or quelle_resolved in ziel_resolved.parents:
        raise AblageFehler("Zielablage darf nicht innerhalb des Quellordners liegen")


def _freier_pfad(zielordner: Path, zielname: str) -> Path:
    ziel = zielordner / zielname
    if not ziel.exists():
        return ziel
    stamm = Path(zielname).stem
    endung = Path(zielname).suffix
    zaehler = 2
    while True:
        kandidat = zielordner / f"{stamm} ({zaehler}){endung}"
        if not kandidat.exists():
            return kandidat
        zaehler += 1


def lege_ab(datei: Datei, vorschlag: Vorschlag, zielablage: Path) -> Path:
    """Kopiert `datei.pfad` nach `zielablage/<kategorie>/<zielname>`.

    Nur Vorschläge mit Status "sicher" werden abgelegt. Bei Namenskollision
    wird ein Suffix " (2)", " (3)" … vor die Dateiendung gesetzt. Das
    Original wird nie verändert — es entsteht ausschließlich eine Kopie
    (shutil.copy2, byte- und mtime-gleich).
    """
    _pruefe_status(vorschlag)
    zielname = _pruefe_zielname(vorschlag)
    kategorie = _pruefe_kategorie(vorschlag)
    _pruefe_original(datei)
    _pruefe_ziel_ausserhalb_quelle(datei.pfad.parent, zielablage)

    zielordner = zielablage / kategorie
    ziel_resolved = zielordner.resolve()
    zielablage_resolved = zielablage.resolve()
    if zielablage_resolved != ziel_resolved and zielablage_resolved not in ziel_resolved.parents:
        raise AblageFehler("Zielpfad liegt nicht unter der Zielablage")

    zielordner.mkdir(parents=True, exist_ok=True)
    zielpfad = _freier_pfad(zielordner, zielname)
    shutil.copy2(datei.pfad, zielpfad)
    return zielpfad

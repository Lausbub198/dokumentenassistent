"""Ordnererfassung und Duplikatserkennung."""
from __future__ import annotations

import hashlib
from pathlib import Path

from dokumentenassistent.typen import Datei


def erfasse_ordner(quelle: Path) -> tuple[Datei, ...]:
    """Rekursiv alle Dateien im Ordner erfassen, sortiert nach Pfad.

    Versteckte Dateien und Ordner (Punkt-Prefix in irgendeinem Pfadteil unterhalb
    der Quelle, z. B. `.dokumentenassistent/`) werden übersprungen.
    """
    if not quelle.exists():
        raise FileNotFoundError(f"Ordner nicht gefunden: {quelle}")

    dateien = []
    for pfad in sorted(quelle.rglob("*")):
        if not pfad.is_file():
            continue
        if any(teil.startswith(".") for teil in pfad.relative_to(quelle).parts):
            continue

        hash_val = _berechne_sha256(pfad)
        datei = Datei(
            hash=hash_val,
            pfad=pfad,
            name=pfad.name,
            groesse=pfad.stat().st_size,
        )
        dateien.append(datei)

    return tuple(dateien)


def finde_duplikate(dateien: tuple[Datei, ...]) -> dict[str, tuple[Path, ...]]:
    """Finde bitgleiche Duplikate nach SHA-256-Hash.

    Nur Hashes mit mehr als einer Datei werden zurückgegeben.
    Wert: tuple der Pfade für diesen Hash.
    """
    hashes: dict[str, list[Path]] = {}
    for datei in dateien:
        if datei.hash not in hashes:
            hashes[datei.hash] = []
        hashes[datei.hash].append(datei.pfad)

    return {h: tuple(pfade) for h, pfade in hashes.items() if len(pfade) > 1}


def _berechne_sha256(pfad: Path) -> str:
    """Berechne SHA-256-Hash der Datei."""
    hasher = hashlib.sha256()
    with pfad.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

"""Original-Dokument öffnen: nur Dateien aus dem Index und unterhalb der Quelle (10.10.2026)."""

from pathlib import Path
from types import SimpleNamespace

from dokumentenassistent.dokument import pfad_im_bestand


def _werkstatt(quelle: Path, pfad: Path | None):
    datei = SimpleNamespace(pfad=pfad) if pfad else None
    return SimpleNamespace(quelle=quelle, index=SimpleNamespace(datei=lambda h: datei))


def test_datei_im_quellordner_wird_geliefert(tmp_path):
    (tmp_path / "Quelle").mkdir()
    f = tmp_path / "Quelle" / "Rechnung.pdf"
    f.write_bytes(b"%PDF")
    assert pfad_im_bestand(_werkstatt(tmp_path / "Quelle", f), "h") == f.resolve()


def test_datei_ausserhalb_der_quelle_nicht(tmp_path):
    (tmp_path / "Quelle").mkdir()
    fremd = tmp_path / "geheim.txt"
    fremd.write_text("x")
    assert pfad_im_bestand(_werkstatt(tmp_path / "Quelle", fremd), "h") is None


def test_unbekannter_hash_nicht(tmp_path):
    assert pfad_im_bestand(_werkstatt(tmp_path, None), "h") is None

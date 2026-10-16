import pytest
from pathlib import Path
from dokumentenassistent.ablage import lege_ab, AblageFehler
from dokumentenassistent.typen import Datei, Vorschlag


def _setup(tmp_path, status="sicher", zielname="2025-05-14_Rechnung_Krause.pdf", kategorie="Wohnung Nord"):
    q = tmp_path / "Quelle"; q.mkdir(); orig = q / "Rechnung (2).pdf"; orig.write_bytes(b"%PDF original")
    d = Datei("h1", orig, orig.name, 13)
    v = Vorschlag("h1", orig.name, kategorie, "Rechnung", (), zielname, status)
    return d, v, tmp_path / "Ziel"

def test_M10_G1_kopie_liegt_unter_kategorie_und_zielname(tmp_path):
    d, v, z = _setup(tmp_path)
    assert lege_ab(d, v, z) == z / "Wohnung Nord" / "2025-05-14_Rechnung_Krause.pdf"

def test_M10_G2_kopie_ist_byteidentisch(tmp_path):
    d, v, z = _setup(tmp_path)
    assert lege_ab(d, v, z).read_bytes() == b"%PDF original"

def test_M10_G3_original_bleibt_am_platz_und_unveraendert(tmp_path):
    d, v, z = _setup(tmp_path); vorher = (d.pfad.read_bytes(), d.pfad.stat().st_mtime_ns)
    lege_ab(d, v, z)
    assert (d.pfad.exists(), d.pfad.read_bytes(), d.pfad.stat().st_mtime_ns) == (True, *vorher)

def test_M10_G4_zielablage_wird_angelegt(tmp_path):
    d, v, z = _setup(tmp_path); lege_ab(d, v, z)
    assert (z / "Wohnung Nord").is_dir()

def test_M10_G5_namenskollision_bekommt_suffix(tmp_path):
    d, v, z = _setup(tmp_path); lege_ab(d, v, z)
    assert lege_ab(d, v, z).name == "2025-05-14_Rechnung_Krause (2).pdf"

def test_M10_B1_unklarer_vorschlag_wird_nicht_abgelegt(tmp_path):
    d, v, z = _setup(tmp_path, status="unklar")
    with pytest.raises(AblageFehler, match="unklar"):
        lege_ab(d, v, z)

def test_M10_B2_ohne_zielname_keine_ablage(tmp_path):
    d, v, z = _setup(tmp_path, zielname=None)
    with pytest.raises(AblageFehler, match="Zielname"):
        lege_ab(d, v, z)

def test_M10_B3_ziel_innerhalb_quelle_wird_abgelehnt(tmp_path):
    d, v, _ = _setup(tmp_path)
    with pytest.raises(AblageFehler, match="Quellordner"):
        lege_ab(d, v, d.pfad.parent / "Ziel")

def test_M10_B4_fehlendes_original_ergibt_ablagefehler(tmp_path):
    d, v, z = _setup(tmp_path); d.pfad.unlink()
    with pytest.raises(AblageFehler, match="Original"):
        lege_ab(d, v, z)

def test_M10_B5_kategorie_mit_pfadtrenner_wird_abgelehnt(tmp_path):
    d, v, z = _setup(tmp_path, kategorie="../raus")
    with pytest.raises(AblageFehler, match="Kategorie"):
        lege_ab(d, v, z)

def test_M10_B6_kategorie_ist_nur_punktpunkt_wird_abgelehnt(tmp_path):
    d, v, z = _setup(tmp_path, kategorie="..")
    with pytest.raises(AblageFehler, match="Kategorie"):
        lege_ab(d, v, z)

import pytest
from pathlib import Path
from dokumentenassistent.erfassen import erfasse_ordner, finde_duplikate


def _mach(tmp_path, name, inhalt=b"abc"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(inhalt)
    return p


def test_M2_G1_liefert_alle_dateien_rekursiv(tmp_path):
    _mach(tmp_path, "a.pdf")
    _mach(tmp_path, "unter/b.jpg")
    assert [d.name for d in erfasse_ordner(tmp_path)] == ["a.pdf", "b.jpg"]


def test_M2_G2_hash_ist_sha256_des_inhalts(tmp_path):
    _mach(tmp_path, "a.pdf", b"abc")
    assert erfasse_ordner(tmp_path)[0].hash == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_M2_G3_bitgleiche_dateien_werden_als_duplikat_gemeldet(tmp_path):
    _mach(tmp_path, "Dokument1.pdf", b"xyz")
    _mach(tmp_path, "Dokument1 Kopie.pdf", b"xyz")
    dups = finde_duplikate(erfasse_ordner(tmp_path))
    assert len(next(iter(dups.values()))) == 2


def test_M2_G4_aehnliche_aber_nicht_bitgleiche_dateien_sind_keine_duplikate(tmp_path):
    _mach(tmp_path, "a.pdf", b"xyz")
    _mach(tmp_path, "b.pdf", b"xyz ")
    assert finde_duplikate(erfasse_ordner(tmp_path)) == {}


def test_M2_G5_originale_bleiben_unveraendert(tmp_path):
    p = _mach(tmp_path, "a.pdf", b"abc")
    vorher = p.stat().st_mtime_ns
    erfasse_ordner(tmp_path)
    assert (p.exists(), p.read_bytes(), p.stat().st_mtime_ns) == (True, b"abc", vorher)


def test_M2_B1_leerer_ordner_ergibt_leeres_tupel(tmp_path):
    assert erfasse_ordner(tmp_path) == ()


def test_M2_B2_nicht_existierender_ordner_ergibt_fehler(tmp_path):
    with pytest.raises(FileNotFoundError):
        erfasse_ordner(tmp_path / "gibts_nicht")


def test_M2_B3_versteckte_dateien_werden_uebersprungen(tmp_path):
    _mach(tmp_path, ".DS_Store")
    _mach(tmp_path, "a.pdf")
    assert [d.name for d in erfasse_ordner(tmp_path)] == ["a.pdf"]


def test_M2_B4_dateien_in_versteckten_ordnern_werden_uebersprungen(tmp_path):
    _mach(tmp_path, ".dokumentenassistent/index.sqlite"); _mach(tmp_path, "a.pdf")
    assert [d.name for d in erfasse_ordner(tmp_path)] == ["a.pdf"]

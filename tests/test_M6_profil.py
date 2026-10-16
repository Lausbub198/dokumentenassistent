import pytest
from dokumentenassistent.profil import schlage_profil_vor, waehle_stichprobe, speichere_profil, lade_profil, ProfilFehler
from dokumentenassistent.provider import SchemaFehler
from tests.conftest import fs

GUT = {"kategorien": ["Wohnung Nord", "Wohnung Süd", "Einkommen"], "dokumenttypen": ["Rechnung", "Vertrag", "Bescheid"],
       "felder": ["datum", "aussteller", "betrag", "rechnungsnummer"], "namensschema": "{datum}_{typ}_{aussteller}"}

def test_M6_G1_vorschlag_wird_zu_profil(fake_provider):
    p = schlage_profil_vor("Steuer 2025", (fs("a#S1#A1", "Rechnung Heizung"),), fake_provider([GUT]))
    assert p.kategorien == ("Wohnung Nord", "Wohnung Süd", "Einkommen")

def test_M6_G2_zweck_und_stichprobe_stehen_im_prompt(fake_provider):
    prov = fake_provider([GUT])
    schlage_profil_vor("Steuer 2025", (fs("a#S1#A1", "Rechnung Heizung"),), prov)
    assert "Steuer 2025" in prov.aufrufe[0][1] and "Rechnung Heizung" in prov.aufrufe[0][1]

def test_M6_G3_stichprobe_nimmt_hoechstens_n_dateien():
    je = {f"h{i}": (fs(f"d{i}#S1#A1", "x", datei=f"d{i}"),) for i in range(8)}
    assert len({f.datei_hash for f in waehle_stichprobe(je, n_dateien=5)}) == 5

def test_M6_G4_stichprobe_nimmt_hoechstens_n_absaetze_je_datei():
    je = {"h1": tuple(fs(f"d#S1#A{i}", "x", absatz=i) for i in range(1, 10))}
    assert len(waehle_stichprobe(je, n_absaetze=4)) == 4

def test_M6_G5_profil_roundtrip_yaml(tmp_path, fake_provider):
    p = schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([GUT]))
    speichere_profil(p, tmp_path / "profil.yaml")
    assert lade_profil(tmp_path / "profil.yaml") == p

def test_M6_B1_leere_kategorien_ergeben_profilfehler(fake_provider):
    with pytest.raises(ProfilFehler, match="Kategorien"):
        schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "kategorien": []}]))

def test_M6_B2_schemafehler_wird_zu_profilfehler(fake_provider):
    with pytest.raises(ProfilFehler):
        schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([SchemaFehler("kaputt")]))

def test_M6_B3_namensschema_ohne_platzhalter_ergibt_profilfehler(fake_provider):
    with pytest.raises(ProfilFehler, match="Namensschema"):
        schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "namensschema": "rechnung"}]))

def test_M6_B4_namensschema_mit_unbekanntem_feld_ergibt_profilfehler(fake_provider):
    with pytest.raises(ProfilFehler, match="kunde"):
        schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "namensschema": "{kunde}"}]))

def test_M6_B5_leere_stichprobe_ergibt_profilfehler(fake_provider):
    with pytest.raises(ProfilFehler, match="Stichprobe"):
        schlage_profil_vor("z", (), fake_provider([GUT]))

def test_M6_B6_doppelte_kategorien_werden_dedupliziert(fake_provider):
    p = schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "kategorien": ["Nord", "Nord", "Süd"]}]))
    assert p.kategorien == ("Nord", "Süd")

def test_M6_B7_fehlende_profil_datei_ergibt_profilfehler(tmp_path):
    with pytest.raises(ProfilFehler):
        lade_profil(tmp_path / "nein.yaml")


# --- Eigentümer (Befund Lasttest 19.09.: Eingangs-/Ausgangsrechnung ohne „wer bin ich" nicht unterscheidbar)

def test_M6_G7_eigentuemer_aus_der_antwort_landet_im_profil(fake_provider):
    p = schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "eigentuemer": "Malerbetrieb Hoffmann GmbH"}]))
    assert p.eigentuemer == "Malerbetrieb Hoffmann GmbH"


def test_M6_G8_ohne_eigentuemer_bleibt_none(fake_provider):
    assert schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([GUT])).eigentuemer is None


def test_M6_G9_eigentuemer_ueberlebt_yaml_roundtrip(tmp_path, fake_provider):
    p = schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "eigentuemer": "Hoffmann"}]))
    speichere_profil(p, tmp_path / "profil.yaml")
    assert lade_profil(tmp_path / "profil.yaml").eigentuemer == "Hoffmann"


def test_M6_B8_leerer_eigentuemer_wird_none(fake_provider):
    assert schlage_profil_vor("z", (fs("a#S1#A1", "x"),), fake_provider([{**GUT, "eigentuemer": "  "}])).eigentuemer is None

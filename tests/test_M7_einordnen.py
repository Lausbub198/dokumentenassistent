import pytest
from pathlib import Path
from dokumentenassistent.einordnen import ordne_ein, baue_zielname
from dokumentenassistent.typen import Datei, Profil, Feld, Beleg
from dokumentenassistent.provider import SchemaFehler
from tests.conftest import fs

P = Profil("Steuer", ("Wohnung Nord", "Wohnung Süd"), ("Rechnung", "Vertrag"), ("datum", "aussteller", "betrag", "rechnungsnummer"), "{datum}_{typ}_{aussteller}")
D = Datei(hash="h_Rechnung (2).pdf", pfad=Path("Rechnung (2).pdf"), name="Rechnung (2).pdf", groesse=1)
FS = (fs("Rechnung (2).pdf#S1#A1", "Rechnung Nr. 2025-0815 vom 14.05.2025\nHeizung Sanitär Krause GmbH"),
      fs("Rechnung (2).pdf#S1#A3", "Rechnungsbetrag 1.240,00 EUR", absatz=3))


def _feld(name, wert, fid, wortlaut): return {"name": name, "wert": wert, "fundstelle_id": fid, "wortlaut": wortlaut}
GUT = {"kategorie": "Wohnung Nord", "typ": "Rechnung", "begruendung": "Heizungsrechnung",
       "felder": [_feld("datum", "2025-05-14", "Rechnung (2).pdf#S1#A1", "14.05.2025"),
                  _feld("aussteller", "Krause", "Rechnung (2).pdf#S1#A1", "Krause GmbH"),
                  _feld("betrag", "1.240,00 EUR", "Rechnung (2).pdf#S1#A3", "1.240,00 EUR"),
                  _feld("rechnungsnummer", "2025-0815", "Rechnung (2).pdf#S1#A1", "2025-0815")]}


def test_M7_G1_vollstaendig_belegt_ist_sicher(fake_provider):
    assert ordne_ein(D, FS, P, fake_provider([GUT])).status == "sicher"


def test_M7_G2_zielname_folgt_schema(fake_provider):
    assert ordne_ein(D, FS, P, fake_provider([GUT])).zielname == "2025-05-14_Rechnung_Krause.pdf"


def test_M7_G3_jedes_feld_traegt_beleg(fake_provider):
    v = ordne_ein(D, FS, P, fake_provider([GUT]))
    assert all(f.beleg is not None for f in v.felder)


def test_M7_G4_nur_fundstellen_ids_stehen_im_prompt(fake_provider):
    prov = fake_provider([GUT]); ordne_ein(D, FS, P, prov)
    assert "Rechnung (2).pdf#S1#A3" in prov.aufrufe[0][1]


def test_M7_G5_profilkategorien_stehen_im_prompt(fake_provider):
    prov = fake_provider([GUT]); ordne_ein(D, FS, P, prov)
    assert "Wohnung Süd" in prov.aufrufe[0][1]


def test_M7_B1_kategorie_ausserhalb_profil_wird_unklar(fake_provider):
    v = ordne_ein(D, FS, P, fake_provider([{**GUT, "kategorie": "Auto"}]))
    assert (v.kategorie, v.status) == (None, "unklar")


def test_M7_B2_erfundener_beleg_macht_feld_unklar_und_vorschlag_unklar(fake_provider):
    schlecht = {**GUT, "felder": GUT["felder"][:2] + [_feld("betrag", "1.420,00 EUR", "Rechnung (2).pdf#S1#A3", "1.420,00 EUR")] + GUT["felder"][3:]}
    v = ordne_ein(D, FS, P, fake_provider([schlecht]))
    betrag = next(f for f in v.felder if f.name == "betrag")
    assert (betrag.status, v.status) == ("unklar", "unklar")


def test_M7_B3_erfundene_fundstellen_id_macht_feld_unklar(fake_provider):
    schlecht = {**GUT, "felder": [_feld("datum", "2025-05-14", "Rechnung (2).pdf#S7#A1", "14.05.2025")] + GUT["felder"][1:]}
    assert next(f for f in ordne_ein(D, FS, P, fake_provider([schlecht])).felder if f.name == "datum").status == "unklar"


def test_M7_B4_fehlendes_schemafeld_faellt_auf_originalnamen_zurueck(fake_provider):
    # Plan-Korrektur 19.09. (Lasttest): nicht geliefertes Feld -> Originalname statt kein Zielname
    ohne_datum = {**GUT, "felder": GUT["felder"][1:]}
    assert ordne_ein(D, FS, P, fake_provider([ohne_datum])).zielname == "Rechnung (2)_Rechnung_Krause.pdf"


def test_M7_B5_ocr_unsicher_ueberstimmt_sicher(fake_provider):
    assert ordne_ein(D, FS, P, fake_provider([GUT]), ocr_unsicher=True).status == "ocr_unsicher"


def test_M7_B6_schemafehler_ergibt_unklar_mit_begruendung(fake_provider):
    v = ordne_ein(D, FS, P, fake_provider([SchemaFehler("kein json")]))
    assert (v.status, "kein json" in v.begruendung) == ("unklar", True)


def test_M7_B7_zielname_ohne_verbotene_zeichen():
    f = (Feld("datum", "2025-05-14", Beleg("x", "y"), "belegt"), Feld("aussteller", "Krause/Söhne: GmbH", Beleg("x", "y"), "belegt"))
    assert "/" not in baue_zielname(P, "Wohnung Nord", "Rechnung", f, ".pdf") and ":" not in baue_zielname(P, "Wohnung Nord", "Rechnung", f, ".pdf")


def test_M7_B8_keine_fundstellen_ergibt_unklar_ohne_modellaufruf(fake_provider):
    prov = fake_provider([]); v = ordne_ein(D, (), P, prov)
    assert (v.status, prov.aufrufe) == ("unklar", [])


def test_M7_G6_nicht_geliefertes_feld_ist_fehlt_und_verhindert_sicher_nicht(fake_provider):
    ohne_nummer = {**GUT, "felder": GUT["felder"][:3]}
    v = ordne_ein(D, FS, P, fake_provider([ohne_nummer]))
    nummer = next(f for f in v.felder if f.name == "rechnungsnummer")
    assert (nummer.status, v.status) == ("fehlt", "sicher")


def test_M7_G7_formal_mitgeliefertes_leeres_feld_ist_fehlt(fake_provider):
    leer = {**GUT, "felder": GUT["felder"][:3] + [_feld("rechnungsnummer", "unbekannt", "", "")]}
    v = ordne_ein(D, FS, P, fake_provider([leer]))
    nummer = next(f for f in v.felder if f.name == "rechnungsnummer")
    assert (nummer.status, v.status) == ("fehlt", "sicher")


def test_M7_B9_platzhalterwert_mit_wortlaut_bleibt_unklar(fake_provider):
    schlecht = {**GUT, "felder": GUT["felder"][:3] + [_feld("rechnungsnummer", "unbekannt", "Rechnung (2).pdf#S1#A1", "Rechnung Nr. 2025-0815")]}
    assert ordne_ein(D, FS, P, fake_provider([schlecht])).status == "unklar"


def test_M7_G8_leeres_feld_mit_schema_erzwungener_id_ist_fehlt(fake_provider):
    leer = {**GUT, "felder": GUT["felder"][:3] + [_feld("rechnungsnummer", "", "Rechnung (2).pdf#S1#A1", "")]}
    v = ordne_ein(D, FS, P, fake_provider([leer]))
    assert (next(f for f in v.felder if f.name == "rechnungsnummer").status, v.status) == ("fehlt", "sicher")


# --- Eigentümer und Zielname-Fallback (Befunde Lasttest 19.09.)

import dataclasses as _dc

def test_M7_G9_eigentuemer_steht_im_prompt(fake_provider):
    prov = fake_provider([GUT]); ordne_ein(D, FS, _dc.replace(P, eigentuemer="Malerbetrieb Hoffmann GmbH"), prov)
    assert "Malerbetrieb Hoffmann GmbH" in prov.aufrufe[0][1]


def test_M7_G10_ohne_eigentuemer_kein_eigentuemer_hinweis_im_prompt(fake_provider):
    prov = fake_provider([GUT]); ordne_ein(D, FS, P, prov)
    assert "Eigentümer" not in prov.aufrufe[0][1]


def test_M7_G11_fehlender_aussteller_faellt_auf_originalnamen_zurueck(fake_provider):
    ohne_aussteller = {**GUT, "felder": [GUT["felder"][0], GUT["felder"][2], GUT["felder"][3]]}
    v = ordne_ein(D, FS, P, fake_provider([ohne_aussteller]))
    assert (v.zielname, v.status) == ("2025-05-14_Rechnung_Rechnung (2).pdf", "sicher")


def test_M7_B10_unklarer_beleg_bekommt_keinen_fallback(fake_provider):
    schlecht = {**GUT, "felder": [GUT["felder"][0], _feld("aussteller", "Krause", "Rechnung (2).pdf#S1#A3", "Krause GmbH")] + GUT["felder"][2:]}
    v = ordne_ein(D, FS, P, fake_provider([schlecht]))
    assert (v.zielname, v.status) == (None, "unklar")


# --- Kontext-Budget (Befund 20.09.: Ollama kuerzt still bei num_ctx; 30-Seiten-Vertrag wurde zum Fragment)

def _lange_fundstellen(n: int):
    return tuple(fs(f"Vertrag.pdf#S{i}#A1", " ".join(f"wort{i}_{k}" for k in range(300)), datei="Vertrag.pdf", seite=i) for i in range(1, n + 1))


def test_M7_G12_budget_nimmt_nur_die_ersten_absaetze(fake_provider):
    prov = fake_provider([GUT]); ordne_ein(D, _lange_fundstellen(30), P, prov, max_woerter=2400)
    assert "Vertrag.pdf#S8#A1" in prov.aufrufe[0][1] and "Vertrag.pdf#S9#A1" not in prov.aufrufe[0][1]


def test_M7_G13_budget_steht_in_der_begruendung(fake_provider):
    v = ordne_ein(D, _lange_fundstellen(30), P, fake_provider([GUT]), max_woerter=2400)
    assert "8 von 30" in v.begruendung


def test_M7_G14_kurze_datei_ohne_budget_hinweis(fake_provider):
    v = ordne_ein(D, FS, P, fake_provider([GUT]), max_woerter=2400)
    assert "von" not in v.begruendung or "Absätzen" not in v.begruendung


def test_fuellsatz_als_wert_macht_unklar():
    # Echter Fall 10.10.2026: Untitled.pdf, Datum „nicht im Dokument enthalten“, Status war „sicher“.
    from dokumentenassistent.einordnen import _wert_unplausibel
    from dokumentenassistent.typen import Feld
    assert _wert_unplausibel(Feld(name="datum", wert="nicht im Dokument enthalten", beleg=None, status="belegt"))
    assert _wert_unplausibel(Feld(name="datum", wert="30.04.", beleg=None, status="belegt"))
    assert not _wert_unplausibel(Feld(name="datum", wert="2025-04-30", beleg=None, status="belegt"))
    assert not _wert_unplausibel(Feld(name="aussteller", wert="Farben Meister GmbH", beleg=None, status="belegt"))


def test_vollstaendige_daten_werden_normalisiert_nicht_bestraft():
    # Lab-Nachmessung 10.10.2026: TT.MM.JJJJ und „TT. Monat JJJJ“ sind korrekte Daten.
    from dokumentenassistent.einordnen import normalisiere_datum
    assert normalisiere_datum("12.03.2025") == "2025-03-12"
    assert normalisiere_datum("3. März 2025") == "2025-03-03"
    assert normalisiere_datum("2025-03-12") == "2025-03-12"
    assert normalisiere_datum("30.04.") == "30.04."
    assert normalisiere_datum("2025-03") == "2025-03"

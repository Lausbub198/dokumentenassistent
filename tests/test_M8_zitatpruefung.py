from dokumentenassistent.typen import Beleg, Feld
from dokumentenassistent.zitatpruefung import pruefe_beleg, pruefe_felder, normalisiere


def test_M8_G1_wortlaut_im_absatz_ist_gueltig(fundstellen_rechnung):
    assert pruefe_beleg(Beleg("Rechnung (2).pdf#S1#A3", "1.240,00 EUR"), fundstellen_rechnung) is True


def test_M8_G2_gross_klein_und_whitespace_sind_egal(fundstellen_rechnung):
    assert pruefe_beleg(Beleg("Rechnung (2).pdf#S1#A3", "rechnungsbetrag   1.240,00"), fundstellen_rechnung) is True


def test_M8_G3_belegtes_feld_bleibt_belegt(fundstellen_rechnung):
    f = Feld("betrag", "1.240,00 EUR", Beleg("Rechnung (2).pdf#S1#A3", "1.240,00 EUR"), "belegt")
    assert pruefe_felder((f,), fundstellen_rechnung)[0].status == "belegt"


def test_M8_G4_normalisiere_ersetzt_typografische_anfuehrungszeichen():
    assert normalisiere("„Heizung“") == '"heizung"'


def test_M8_B1_erfundene_id_ist_ungueltig(fundstellen_rechnung):
    assert pruefe_beleg(Beleg("Rechnung (2).pdf#S9#A9", "1.240,00 EUR"), fundstellen_rechnung) is False


def test_M8_B2_wortlaut_nicht_im_absatz_ergibt_unklar(fundstellen_rechnung):
    f = Feld("betrag", "1.420,00 EUR", Beleg("Rechnung (2).pdf#S1#A3", "1.420,00 EUR"), "belegt")
    g = pruefe_felder((f,), fundstellen_rechnung)[0]
    assert (g.status, g.wert, g.beleg) == ("unklar", None, None)


def test_M8_B3_wortlaut_aus_anderem_absatz_ist_ungueltig(fundstellen_rechnung):
    assert pruefe_beleg(Beleg("Rechnung (2).pdf#S1#A1", "1.240,00 EUR"), fundstellen_rechnung) is False


def test_M8_B4_leerer_wortlaut_ist_ungueltig(fundstellen_rechnung):
    assert pruefe_beleg(Beleg("Rechnung (2).pdf#S1#A3", "   "), fundstellen_rechnung) is False


def test_M8_B5_feld_ohne_beleg_wird_unklar(fundstellen_rechnung):
    f = Feld("betrag", "1.240,00 EUR", None, "belegt")
    assert pruefe_felder((f,), fundstellen_rechnung)[0].status == "unklar"


def test_M8_B6_pruefung_veraendert_eingabe_nicht(fundstellen_rechnung):
    f = Feld("betrag", "9", Beleg("x#S1#A1", "9"), "belegt")
    pruefe_felder((f,), fundstellen_rechnung)
    assert f.status == "belegt"


def test_M8_B7_wert_ausserhalb_des_wortlauts_ergibt_unklar(fundstellen_rechnung):
    f = Feld("rechnungsnummer", "unbekannt", Beleg("Rechnung (2).pdf#S1#A1", "Rechnung Nr. 2025-0815"), "belegt")
    assert pruefe_felder((f,), fundstellen_rechnung)[0].status == "unklar"


def test_M8_B8_leerer_wert_ergibt_unklar(fundstellen_rechnung):
    f = Feld("betrag", "", Beleg("Rechnung (2).pdf#S1#A3", "1.240,00 EUR"), "belegt")
    assert pruefe_felder((f,), fundstellen_rechnung)[0].status == "unklar"


def test_M8_G5_datum_darf_iso_sein_obwohl_wortlaut_deutsch_ist(fundstellen_rechnung):
    f = Feld("datum", "2025-06-30", Beleg("Rechnung (2).pdf#S2#A1", "Zahlbar bis 30.06.2025"), "belegt")
    assert pruefe_felder((f,), fundstellen_rechnung)[0].status == "belegt"

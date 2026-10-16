import pytest
from dokumentenassistent.konflikte import finde_konflikte, entscheide, erklaerung
from dokumentenassistent.typen import Vorschlag, Feld, Beleg


def _v(h, name, betrag, nr, datum, aussteller="Krause", kat="Wohnung Nord"):
    b = lambda w: Beleg(f"{name}#S1#A1", w)
    return Vorschlag(h, name, kat, "Rechnung", (Feld("datum", datum, b(datum), "belegt"), Feld("aussteller", aussteller, b(aussteller), "belegt"),
                     Feld("betrag", betrag, b(betrag), "belegt"), Feld("rechnungsnummer", nr, b(nr), "belegt")), f"{datum}_R.pdf", "sicher")


A = _v("hA", "Rechnung (2).pdf", "1.240,00 EUR", "2025-0815", "2025-05-14")
B = _v("hB", "Rechnung (3).pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02")
TEXTE = {"hA": "Rechnung Nr. 2025-0815 …", "hB": "Korrekturrechnung zu Rechnung Nr. 2025-0815 …"}


def test_M9_G1_korrekturrechnung_wird_konflikt():
    assert len(finde_konflikte((A, B), TEXTE)) == 1


def test_M9_G2_konflikt_traegt_beide_werte_und_belege():
    k = finde_konflikte((A, B), TEXTE)[0]
    assert (k.feld, {k.wert_a, k.wert_b}) == ("betrag", {"1.240,00 EUR", "1.180,00 EUR"})


def test_M9_G3_spaeteres_datum_ergibt_vorschlag_ersetzt():
    assert finde_konflikte((A, B), TEXTE)[0].vorschlag == "ersetzt"


def test_M9_G4_entscheidung_erzeugt_neuen_konflikt_mit_entscheidung():
    k = finde_konflikte((A, B), TEXTE)[0]; e = entscheide(k, "verschiedene_sachverhalte")
    assert (e.entscheidung, k.entscheidung) == ("verschiedene_sachverhalte", None)


def test_M9_G5_eigener_wert_wird_gespeichert():
    k = finde_konflikte((A, B), TEXTE)[0]
    assert entscheide(k, "eigener_wert", "1.200,00 EUR").eigener_wert == "1.200,00 EUR"


def test_M9_G6_erklaerung_nutzt_provider_und_entscheidet_nicht(fake_provider):
    prov = fake_provider(text_antworten=["Die zweite Rechnung korrigiert die erste."])
    k = finde_konflikte((A, B), TEXTE)[0]
    assert (erklaerung(k, prov), k.entscheidung) == ("Die zweite Rechnung korrigiert die erste.", None)


def test_M9_G7_gleiche_rechnungsnummer_reicht_auch_ohne_textverweis():
    B2 = _v("hB", "Rechnung (3).pdf", "1.180,00 EUR", "2025-0815", "2025-06-02")
    assert len(finde_konflikte((A, B2), {"hA": "", "hB": ""})) == 1


def test_M9_B1_gleicher_betrag_ist_kein_konflikt():
    B2 = _v("hB", "x.pdf", "1.240,00 EUR", "2025-0815", "2025-06-02")
    assert finde_konflikte((A, B2), TEXTE) == ()


def test_M9_B2_anderer_aussteller_ist_kein_konflikt():
    B2 = _v("hB", "x.pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02", aussteller="Müller")
    assert finde_konflikte((A, B2), TEXTE) == ()


def test_M9_B3_andere_kategorie_ist_kein_konflikt():
    B2 = _v("hB", "x.pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02", kat="Wohnung Süd")
    assert finde_konflikte((A, B2), TEXTE) == ()


def test_M9_B4_ohne_datum_ist_vorschlag_nicht_entscheidbar():
    A2 = _v("hA", "Rechnung (2).pdf", "1.240,00 EUR", "2025-0815", None)
    assert finde_konflikte((A2, B), TEXTE)[0].vorschlag == "nicht_entscheidbar"


def test_M9_B5_ungueltige_entscheidung_ergibt_fehler():
    k = finde_konflikte((A, B), TEXTE)[0]
    with pytest.raises(ValueError, match="Entscheidung"):
        entscheide(k, "spaeteres_gewinnt")


def test_M9_B6_eigener_wert_ohne_wert_ergibt_fehler():
    k = finde_konflikte((A, B), TEXTE)[0]
    with pytest.raises(ValueError, match="eigener Wert"):
        entscheide(k, "eigener_wert")


def test_M9_B7_unklare_vorschlaege_werden_nicht_verglichen():
    A2 = Vorschlag("hA", "a.pdf", None, None, (), None, "unklar")
    assert finde_konflikte((A2, B), TEXTE) == ()


def test_M9_G8_kurzform_desselben_ausstellers_ist_konflikt():
    """Gesamttest 06.10.2026: aus dem PaddleOCR-Scan las das Modell 'Krause GmbH', aus dem PDF
    'Heizung Sanitär Krause GmbH' — die exakte Gleichheit ließ den Konflikt durch."""
    A2 = _v("hA", "Scan_0043.pdf", "1.240,00 EUR", "2025-0815", "2025-05-14", aussteller="Krause GmbH")
    B2 = _v("hB", "Rechnung (3).pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02",
            aussteller="Heizung Sanitär Krause GmbH")
    assert len(finde_konflikte((A2, B2), TEXTE)) == 1


def test_M9_G9_schreibvarianten_desselben_ausstellers_sind_konflikt():
    A2 = _v("hA", "a.pdf", "1.240,00 EUR", "2025-0815", "2025-05-14", aussteller="Krause GmbH & Co. KG")
    B2 = _v("hB", "b.pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02", aussteller="krause  GmbH & Co KG")
    assert len(finde_konflikte((A2, B2), TEXTE)) == 1


def test_M9_B8_nur_gleiche_rechtsform_ist_kein_konflikt():
    A2 = _v("hA", "a.pdf", "1.240,00 EUR", "2025-0815", "2025-05-14", aussteller="Krause GmbH")
    B2 = _v("hB", "b.pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02", aussteller="Müller GmbH")
    assert finde_konflikte((A2, B2), TEXTE) == ()


def test_M9_B9_kurzes_allerweltswort_reicht_nicht():
    A2 = _v("hA", "a.pdf", "1.240,00 EUR", "2025-0815", "2025-05-14", aussteller="Bau GmbH")
    B2 = _v("hB", "b.pdf", "1.180,00 EUR", "2025-0815-K", "2025-06-02", aussteller="Müller Bau GmbH")
    assert finde_konflikte((A2, B2), TEXTE) == ()

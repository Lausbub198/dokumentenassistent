"""Metadaten sind ein begrenzter Ranking-Bonus, kein Suchfilter."""
from dokumentenassistent.retrieval_metadaten import bonus_rang
from dokumentenassistent.typen import Feld, Vorschlag
from tests.conftest import fs


ALT = fs("alt.pdf#S1#A1", "Zahlung im Folgejahr", datei="alt.pdf")
NEU = fs("neu.pdf#S1#A1", "Zahlung im gesuchten Jahr", datei="neu.pdf")
FUNDSTELLEN = {ALT.id: ALT, NEU.id: NEU}
RANG = ((ALT.id, 0.62), (NEU.id, 0.60))


def vorschlag(fundstelle, datum=None, typ=None, aussteller=None):
    felder = tuple(
        Feld(name=name, wert=wert, beleg=None, status="belegt")
        for name, wert in (("datum", datum), ("aussteller", aussteller)) if wert
    )
    return Vorschlag(datei_hash=fundstelle.datei_hash, datei_name=fundstelle.datei_name,
                     kategorie=None, typ=typ, felder=felder, zielname=None, status="unklar")


def test_bonus_null_laesst_dense_rang_und_scores_unveraendert():
    meta = {NEU.datei_hash: vorschlag(NEU, datum="2025-01-10")}
    assert bonus_rang("Zahlung 2025", RANG, FUNDSTELLEN, meta, gewicht=0.0) == RANG


def test_passendes_jahr_kann_kandidaten_nach_vorn_bringen_ohne_zu_filtern():
    meta = {ALT.datei_hash: vorschlag(ALT, datum="2024-12-30"),
            NEU.datei_hash: vorschlag(NEU, datum="2025-01-10")}
    ergebnis = bonus_rang("Zahlung 2025", RANG, FUNDSTELLEN, meta, gewicht=0.05)
    assert [id_ for id_, _ in ergebnis] == [NEU.id, ALT.id]
    assert len(ergebnis) == len(RANG)


def test_abweichendes_jahr_entfernt_keinen_kandidaten():
    meta = {ALT.datei_hash: vorschlag(ALT, datum="2024-12-30")}
    assert bonus_rang("Zahlung 2025", RANG, FUNDSTELLEN, meta, gewicht=0.05) == RANG


def test_typ_und_aussteller_geben_bonus_nur_bei_frage_treffer():
    meta = {NEU.datei_hash: vorschlag(NEU, typ="Rechnung", aussteller="Musterwerke")}
    ergebnis = bonus_rang("Rechnung der Musterwerke", RANG, FUNDSTELLEN, meta, gewicht=0.02)
    assert ergebnis[0][0] == NEU.id
    assert bonus_rang("Vertrag ohne Namen", RANG, FUNDSTELLEN, meta, gewicht=0.02) == RANG


def test_unbelegtes_feld_und_gleichstand_aendern_nichts():
    unsicher = Feld(name="datum", wert="2025-01-10", beleg=None, status="unklar")
    v = Vorschlag(datei_hash=NEU.datei_hash, datei_name=NEU.datei_name,
                  kategorie=None, typ=None, felder=(unsicher,), zielname=None, status="unklar")
    gleichstand = ((ALT.id, 0.60), (NEU.id, 0.60))
    assert bonus_rang("Zahlung 2025", gleichstand, FUNDSTELLEN,
                      {NEU.datei_hash: v}, gewicht=0.05) == gleichstand

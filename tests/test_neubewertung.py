from dokumentenassistent import neubewertung as nb


def test_woerter_fuehrt_trennung_zusammen_und_ignoriert_satzzeichen():
    assert nb.woerter("Die Woh- nung, hell.") == ["die", "wohnung", "hell"]


def test_deckung_toleriert_eingeschobene_kopfzeile():
    gold = nb.woerter("Die Kaution beträgt drei Monatsmieten und ist zu verzinsen.")
    chunk = nb.woerter("Die Kaution beträgt drei Hausverwaltung Sommer Seite 2 Monatsmieten und ist zu verzinsen.")
    assert nb.deckung(gold, chunk) == 1.0
    assert nb.deckung(gold, nb.woerter("Die Miete ist im Voraus zu zahlen.")) < nb.MINDESTANTEIL

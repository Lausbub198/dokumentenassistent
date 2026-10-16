from dokumentenassistent import gold_bereinigung as gb

ZIEL = 'Die monatliche Miete beträgt gemäß § 3 des Vertrags 750,00 EUR zuzüglich Nebenkosten.'


def frage(ziel=ZIEL, wert='750,00 EUR', nr=1):
    return {'nr': nr, 'status': 'gefunden', 'zielabsatz': ziel, 'wortlaut_enthaelt': wert}


def test_gold_ok_aber_ueber_chunks_wird_auf_chunk_mit_sollwert_gekuerzt():
    b = gb.klassifiziere(frage(), ['Vorwort. Die monatliche Miete beträgt gemäß § 3',
                                   'des Vertrags 750,00 EUR zuzüglich Nebenkosten. Kaution.'])
    assert b.klasse == 'gold_ok' and b.ueber_chunks
    assert b.ersatz == 'des Vertrags 750,00 EUR zuzüglich Nebenkosten.'


def test_gold_schreibweise_ohne_ueberstehende_woerter():
    b = gb.klassifiziere(frage('Die „Miete“ beträgt 750,00 EUR – monatlich.'),
                         ['Vorher. DIE "MIETE" BETRÄGT 750,00 EUR - MONATLICH. Danach folgt Text.'])
    assert b.klasse == 'gold_schreibweise' and not b.ueber_chunks
    assert b.ersatz == 'DIE "MIETE" BETRÄGT 750,00 EUR - MONATLICH.'


def test_erstes_und_letztes_zeichen_bleiben_erhalten():
    b = gb.klassifiziere(frage('Er zahlt 750,00 EUR laut § 3 Abs. 2 des Mietvertrags vom 1. Mai.'),
                         ['Kopf. Er zahlt 750,00 EUR laut 8 3 Abs. 2 des Mietvertrags vom 1. Mai. Weiter im Text.'])
    assert b.klasse == 'auslesefehler'
    assert b.ersatz == 'Er zahlt 750,00 EUR laut 8 3 Abs. 2 des Mietvertrags vom 1. Mai.'


def test_nur_case_ist_gold_schreibweise():
    b = gb.klassifiziere(frage('Mietbeginn 1. Mai, Miete 750,00 EUR'), ['Text. mietbeginn 1. Mai, miete 750,00 EUR x'])
    assert b.klasse == 'gold_schreibweise' and b.ersatz == 'mietbeginn 1. Mai, miete 750,00 EUR'


def test_auslesefehler_paragraphenzeichen_als_ziffer():
    kaputt = ZIEL.replace('§ 3', '8 3')
    b = gb.klassifiziere(frage(), [f'Anfang. {kaputt} Ende des Absatzes.'])
    assert b.klasse == 'auslesefehler' and b.ersatz == kaputt


def test_anderer_betrag_wird_nicht_ersetzt():
    b = gb.klassifiziere(frage(), [ZIEL.replace('750,00', '705,00')])
    assert b.klasse == 'unklar' and b.ersatz is None


def test_gleichnamige_dateien_eine_genuegt():
    b = gb.befund(frage(), [['Nichts Passendes hier.'], [f'X. {ZIEL.replace("§", "S")} Y.']])
    assert b.klasse == 'auslesefehler' and '750,00 EUR' in b.ersatz


def test_neues_gold_laesst_original_und_andere_felder_unveraendert():
    gold = {'zweck': 'x', 'fragen': [frage('alt', nr=1), frage('bleibt', nr=2), frage('ok', nr=3)]}
    befunde = [gb.Befund(1, 'auslesefehler', 0.9, False, 'neu 750,00 EUR'),
               gb.Befund(2, 'unklar', 0.2, False, None),
               gb.Befund(3, 'gold_ok', 1.0, True, 'Teil 750,00 EUR')]
    neu = gb.neues_gold(gold, befunde, 'abc')
    assert gold['fragen'][0]['zielabsatz'] == 'alt'
    f1, f2, f3 = neu['fragen']
    assert f1['zielabsatz'] == 'neu 750,00 EUR' and f1['zielabsatz_alt'] == 'alt'
    assert f1['wortlaut_enthaelt'] == '750,00 EUR' and f1['status'] == 'gefunden'
    assert f2 == gold['fragen'][1]
    assert f3['zielabsatz'] == 'Teil 750,00 EUR' and f3['zielabsatz_ueber_chunks']
    b = neu['bereinigung']
    assert b['ersetzt'] == [1, 3] and b['auslesefehler'] == [1] and b['unklar'] == [2] and b['ueber_chunks'] == [3]

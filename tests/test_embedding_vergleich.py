from dokumentenassistent import embedding_vergleich as ev


def test_anweisung_nur_wenn_verlangt():
    assert ev.frage_text('Wie hoch?', False) == 'Wie hoch?'
    assert ev.frage_text('Wie hoch?', True).startswith('Instruct: ') and ev.frage_text('Wie hoch?', True).endswith('Query:Wie hoch?')


def test_auswertung_zaehlt_pool_und_paarung():
    fragen = [{'nr': 1, 'status': 'gefunden'}, {'nr': 2, 'status': 'gefunden'}, {'nr': 3, 'status': 'nicht_gefunden'}]
    z = lambda d, k20, k50: {'dense_rang': d, 'kontext_pool20': k20, 'kontext_pool50': k50,
                             'rang1_pool20': False, 'rang1_pool50': False, 'max_score': 0.5}
    je = {'e06': {1: z(5, True, True), 2: z(30, False, True), 3: z(None, False, False)},
          'e8': {'1': z(3, True, True), '2': z(12, True, True), '3': z(None, False, False)}}
    b = ev.auswerten(fragen, je)
    assert b['e06']['dense_top20'] == 1 and b['e06']['dense_top50'] == 2 and b['e06']['kontext_pool50'] == 2
    assert b['e8']['pool20_gewinne_vs_e06'] == [2] and b['e8']['pool20_verluste_vs_e06'] == []

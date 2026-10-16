from dokumentenassistent import docling_pilot as dp

ELEMENTE = [('titel', 'Mietvertrag'), ('text', 'Zwischen A und B.'), ('ueberschrift', '§ 5 Kaution'),
            ('text', 'Die Kaution beträgt 2.250,00 EUR und ist fällig.'), ('ueberschrift', '§ 6 Schluss')]


def test_ueberschriften_vor_dem_zielabsatz():
    assert dp.ueberschrift_vor(ELEMENTE, 'Die Kaution beträgt 2.250,00 EUR', '2.250,00 EUR') == \
        ['Mietvertrag', '§ 5 Kaution']


def test_fallback_auf_sollwert_und_leer_wenn_nichts_gefunden():
    assert dp.ueberschrift_vor(ELEMENTE, 'ganz anderer Text', '2.250,00 EUR') == ['Mietvertrag', '§ 5 Kaution']
    assert dp.ueberschrift_vor(ELEMENTE, 'nicht da', 'auch nicht') == []


def test_enthalten_trennt_exakt_und_locker():
    assert dp.enthalten('Die „Miete“', 'x die "MIETE" y') == {'exakt': False, 'locker': True}
    assert dp.enthalten('a  b', 'x a b y') == {'exakt': True, 'locker': True}
    assert dp.enthalten('', 'x') == {'exakt': False, 'locker': False}

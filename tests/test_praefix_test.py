from dokumentenassistent import praefix_test as pt
from dokumentenassistent.typen import Fundstelle

META = {'typ': 'Mietvertrag', 'kategorie': 'Verträge', 'datum': '2019-05-01', 'aussteller': 'Hausverwaltung'}


def test_praefix_je_arm():
    assert pt.praefix('A', 'w/v.pdf', META, 'Kopf') == ''
    assert pt.praefix('B', 'w/v.pdf', META, 'Kopf') == 'Dokument: w/v.pdf\n\n'
    c = pt.praefix('C', 'w/v.pdf', META, 'Kopf')
    assert c.startswith('typ: Mietvertrag; kategorie: Verträge; datum: 2019-05-01') and 'w/v.pdf' not in c
    d = pt.praefix('D', 'w/v.pdf', META, 'Kopf')
    assert d.startswith('Dokument: w/v.pdf\ntyp: Mietvertrag')
    assert pt.praefix('E', 'w/v.pdf', META, 'Kopf') == 'Dokumentanfang: Kopf\n\n'
    assert pt.praefix('C', None, None, '') == ''


def test_ueberschrift_regeln_allgemein():
    for ja in ('§ 5 Kaution', '§§ 3a Nebenkosten', 'Art. 3 Geltungsbereich', 'Artikel 12 Haftung',
               '2. Leistungsumfang', '2.1 Zahlungsbedingungen', 'IV. Schlussbestimmungen', 'a) Allgemeines',
               'ALLGEMEINE GESCHÄFTSBEDINGUNGEN', 'RECHNUNG'):
        assert pt.ist_ueberschrift(ja), ja
    for nein in ('1. Januar 2020', 'Datum: 01.02.2020', '1.250,00 EUR', 'Die Kaution beträgt drei Monatsmieten.',
                 '§ 5 Die Kaution ist zu Beginn des Mietverhältnisses in voller Höhe und ohne Abzug zu zahlen',
                 'Seite 2', '12345', 'EUR', 'Mit freundlichen Grüßen,', '3. Die Zahlung erfolgt monatlich;'):
        assert not pt.ist_ueberschrift(nein), nein


def test_abschnitt_ist_letzte_ueberschrift_davor_ausser_chunk_beginnt_mit_einer():
    fs = [Fundstelle('1', 'h', 'x', 1, 0, 'MIETVERTRAG\nZwischen A und B wird vereinbart.'),
          Fundstelle('2', 'h', 'x', 1, 1, 'Weiterer Text ohne Kopf.\n§ 5 Kaution\nDie Kaution beträgt X.'),
          Fundstelle('3', 'h', 'x', 2, 0, 'Sie ist fällig zu Beginn.'),
          Fundstelle('4', 'h', 'x', 2, 1, '§ 6 Schluss\nText.'),
          Fundstelle('5', 'g', 'y', 1, 0, 'Anderes Dokument ohne Kopf.')]
    assert pt.abschnitte(fs) == {'1': '', '2': 'MIETVERTRAG', '3': '§ 5 Kaution', '4': '', '5': ''}


def test_praefix_mit_abschnitt():
    assert pt.praefix('F', 'w/v.pdf', META, 'Kopf', '§ 5 Kaution') == 'Abschnitt: § 5 Kaution\n\n'
    assert pt.praefix('H', 'w/v.pdf', META, 'Kopf', '§ 5 Kaution') == 'Dokument: w/v.pdf\nAbschnitt: § 5 Kaution\n\n'
    assert pt.praefix('G', 'w/v.pdf', META, 'Kopf', '').startswith('Dokument: w/v.pdf\ntyp:')
    assert pt.praefix('F', 'w/v.pdf', META, 'Kopf', '') == ''


def test_kopf_sind_die_ersten_woerter_in_dokumentreihenfolge():
    fs = [Fundstelle('b', 'h', 'x', 2, 0, 'drei vier'), Fundstelle('a', 'h', 'x', 1, 0, 'eins zwei')]
    assert pt.koepfe(fs) == {'h': 'eins zwei drei vier'}


def _r(treffer, score, dense=5, rerank=1):
    return {'kontexttreffer': treffer, 'max_score': score, 'zielchunk_rang_dense': dense,
            'zielchunk_rang_reranked': rerank if treffer else None}


def test_auswertung_leitet_schwelle_ab_und_zaehlt_gewinne_verluste():
    fragen = [{'nr': 1, 'status': 'gefunden'}, {'nr': 2, 'status': 'gefunden'},
              {'nr': 3, 'status': 'nicht_gefunden'}]
    je_arm = {'A': {1: _r(True, 0.6), 2: _r(True, 0.45), 3: _r(False, 0.4)},
              'B': {1: _r(False, 0.6, dense=30), 2: _r(True, 0.55), 3: _r(False, 0.52)}}
    b = pt.auswerten(fragen, je_arm)
    assert b['A']['kontexttreffer_mit_schwelle'] == 1 and b['A']['kontexttreffer_ohne_schwelle'] == 2
    assert b['A']['positiv_an_schwelle'] == [2] and b['A']['negativ_an_schwelle_gestoppt'] == 1
    assert b['B']['gewinne_vs_A'] == [2] and b['B']['verluste_vs_A'] == [1]
    assert b['B']['negativ_an_schwelle_gestoppt'] == 0

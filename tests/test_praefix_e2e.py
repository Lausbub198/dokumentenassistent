import numpy as np

from dokumentenassistent import praefix_e2e as pe
from dokumentenassistent.typen import Fundstelle

FS = [Fundstelle(f'{"a" * 64}#S1#A{i}', 'a' * 64, 'Vertrag.pdf', 1, i, t)
      for i, t in enumerate(['Kopf', 'Die Kaution beträgt 750,00 EUR.', 'Sonstiges'])]
FRAGE = {'nr': 1, 'status': 'gefunden', 'datei': 'Vertrag.pdf', 'wortlaut_enthaelt': '750,00 EUR'}


class Reranker:
    def bewerte(self, frage, texte):
        return [1.0 if 'Kaution' in t else 0.0 for t in texte]


def test_kontext_schwelle_und_reranking():
    m = np.eye(3, dtype=np.float32)
    assert pe.kontext('q', [0.4, 0.1, 0.1], FS, [f.text for f in FS], m, Reranker(), 0.95) is None
    assert pe.kontext('q', [1.0, 0.5, 0.2], FS, [f.text for f in FS], m, Reranker(), 0.1, k=2) == [1, 0]


def test_bewerte_zitat_zielabsatz_und_abweisung():
    ziel = {FS[1].id}
    ok = pe.bewerte(FRAGE, f'Die Kaution beträgt 750,00 EUR [{FS[1].id}].', FS, ziel)
    assert ok['zitat_zielabsatz'] and ok['beleg_whitespace'] and ok['antwort_enthaelt_wert'] and not ok['abgewiesen']
    falsch = pe.bewerte(FRAGE, f'Steht im Kopf [{FS[0].id}].', FS, ziel)
    assert falsch['quellen_id_gueltig'] and not falsch['zitat_zielabsatz']
    ng = pe.bewerte(FRAGE, 'nicht gefunden', FS, ziel)
    assert ng['abgewiesen'] and not ng['antwort_enthaelt_wert']
    assert pe.bewerte(FRAGE, None, [], ziel)['an_schwelle']


def test_auswertung_gepaart():
    zeilen = [{'arm': 'A', 'nr': 1, 'status': 'gefunden', 'zitat_zielabsatz': True, 'sekunden': 1},
              {'arm': 'B', 'nr': 1, 'status': 'gefunden', 'zitat_zielabsatz': False, 'sekunden': 1},
              {'arm': 'A', 'nr': 2, 'status': 'gefunden', 'zitat_zielabsatz': False, 'sekunden': 1},
              {'arm': 'B', 'nr': 2, 'status': 'gefunden', 'zitat_zielabsatz': True, 'sekunden': 1},
              {'arm': 'A', 'nr': 3, 'status': 'nicht_gefunden', 'abgewiesen': True, 'an_schwelle': True, 'sekunden': 0},
              {'arm': 'B', 'nr': 3, 'status': 'nicht_gefunden', 'abgewiesen': False, 'sekunden': 1}]
    b = pe.auswerten(zeilen, ('A', 'B'))
    assert b['gepaart_zitat_zielabsatz'] == {'gewinne': [2], 'verluste': [1]}
    assert b['A']['negativ_abgewiesen'] == 1 and b['B']['negativ_abgewiesen'] == 0
    assert b['A']['negativ_an_schwelle'] == 1


def test_auswertung_ein_arm_ohne_paarung():
    zeilen = [{'arm': 'B', 'nr': 1, 'status': 'gefunden', 'zitat_zielabsatz': True, 'sekunden': 1}]
    b = pe.auswerten(zeilen, ('B',))
    assert b['B']['zitat_zielabsatz'] == 1 and 'gepaart_zitat_zielabsatz' not in b

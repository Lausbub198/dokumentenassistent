from dokumentenassistent import antwortstufe as ab
from dokumentenassistent.typen import Fundstelle

K = [{'id': 'a', 'score': 0.9}, {'id': 'b', 'score': 0.5}, {'id': 'c', 'score': 0.44}, {'id': 'd', 'score': 0.1}]


def test_auswahl_top_n_und_dynamisch():
    assert [c['id'] for c in ab.auswahl(K, top_n=2)] == ['a', 'b']
    assert [c['id'] for c in ab.auswahl(K, dynamisch=True)] == ['a', 'b']  # 0,5 × 0,9 = 0,45
    assert [c['id'] for c in ab.auswahl([{'id': 'x', 'score': 3.0}, {'id': 'y', 'score': -2.0}], dynamisch=True)] == ['x']
    assert ab.auswahl([], dynamisch=True) == []


def test_dedupe_nur_innerhalb_derselben_datei():
    fs = {'a': Fundstelle('a', 'h', 'x', 1, 0, 'Die Miete beträgt 750 EUR im Monat'),
          'b': Fundstelle('b', 'h', 'x', 1, 1, 'Die Miete beträgt 750 EUR im Monat netto'),
          'c': Fundstelle('c', 'g', 'y', 1, 0, 'Die Miete beträgt 750 EUR im Monat'),
          'd': Fundstelle('d', 'h', 'x', 2, 0, 'Kaution drei Monatsmieten')}
    sel = [{'id': i} for i in 'abcd']
    assert [c['id'] for c in ab.dedupe(sel, fs)] == ['a', 'c', 'd']


def test_zitat_zuerst_ersetzt_nur_die_anweisung():
    top = (Fundstelle('a', 'h', 'x', 1, 0, 'Text'),)
    p = ab.prompt(top, 'Frage?', True)
    assert 'Kopiere zuerst wörtlich' in p and p.endswith('Frage: Frage?\nAntwort:')
    assert 'Kopiere zuerst' not in ab.prompt(top, 'Frage?', False)


def _z(nr, mehrfach=False, status='gefunden', abgewiesen=False):
    return {'nr': nr, 'status': status, 'mehrfach': mehrfach, 'streng': mehrfach, 'wert_in_antwort': mehrfach,
            'abgewiesen': abgewiesen, 'chunks': 5, 'sekunden': 10.0}


def test_robustheit_zaehlt_gleiche_ergebnisse():
    a = [_z(1, True), _z(2, False), _z(3, status='nicht_gefunden', abgewiesen=True)]
    b = [_z(1, True), _z(2, True), _z(3, status='nicht_gefunden', abgewiesen=True)]
    r = ab.gleich_je_frage(a, b)
    assert r == {'positiv_gleich': 1, 'positiv': 2, 'negativ_gleich': 1, 'negativ': 1,
                 'negativ_in_beiden_abgewiesen': 1, 'kippt': [2], 'in_beiden': [1]}


def test_vergleich_gate_und_umgekehrt_nicht_als_eigene_zeile():
    basis = [_z(n, n <= 2) for n in range(1, 11)] + [_z(99, status='nicht_gefunden', abgewiesen=True)]
    besser = [_z(n, n <= 8) for n in range(1, 11)] + [_z(99, status='nicht_gefunden', abgewiesen=True)]
    laeufe = {'b0': basis, 'b0-umgekehrt': basis, 'top5': besser, 'top5-umgekehrt': besser}
    v = ab.vergleiche(laeufe, 'b0')
    assert set(v) == {'b0', 'top5'}
    assert v['top5']['gegen_basis'] == {'gewinne': [3, 4, 5, 6, 7, 8], 'verluste': [], 'netto': 6}
    assert v['top5']['gate']['bestanden'] is True
    assert v['top5']['robustheit']['positiv_gleich'] == 10
    tabelle = ab.als_tabelle(v, 'b0')
    assert '| top5 | 8 |' in tabelle and 'Basis' in tabelle and '✔' in tabelle


def test_gate_nicht_bestanden_ohne_umkehrlauf_der_variante():
    basis = [_z(n, n <= 2) for n in range(1, 11)]
    besser = [_z(n, n <= 8) for n in range(1, 11)]
    v = ab.vergleiche({'b0': basis, 'b0-umgekehrt': basis, 'top5': besser}, 'b0')
    assert v['top5']['gate'] == {'bestanden': False, 'grund': 'kein Umkehr-Lauf'}


def test_gate_auf_in_beiden_korrekt_und_dritte_reihenfolge():
    basis = [_z(n, n <= 4) for n in range(1, 11)]
    var = [_z(n, n <= 10) for n in range(1, 11)]
    var_um = [_z(n, n <= 9) for n in range(1, 11)]
    var_gem = [_z(n, n <= 7) for n in range(1, 11)]
    v = ab.vergleiche({'b0': basis, 'b0-umgekehrt': basis, 'k': var, 'k-umgekehrt': var_um, 'k-gemischt': var_gem}, 'b0')
    assert set(v) == {'b0', 'k'}
    assert len(v['k']['robustheit']['in_beiden']) == 9 and v['k']['robustheit']['kippt'] == [10]
    assert v['k']['in_allen_drei'] == 7
    assert v['k']['gegen_basis']['netto'] == 5 and v['k']['gate']['bestanden'] is True


def test_ordne_umgekehrt_und_gemischt_deterministisch():
    assert ab.ordne([1, 2, 3], 7, umgekehrt=True) == [3, 2, 1]
    a, b = ab.ordne(list(range(10)), 7, mischen=True), ab.ordne(list(range(10)), 7, mischen=True)
    assert a == b and sorted(a) == list(range(10)) and a != list(range(10))
    assert ab.ordne([1, 2, 3], 7) == [1, 2, 3]


class _Prov:
    def __init__(self, nummern=None, texte=()):
        self.nummern, self.texte, self.prompts = nummern, list(texte), []

    def generate_json(self, prompt, schema):
        self.prompts.append(prompt)
        return {'nummern': self.nummern}

    def generate_text(self, prompt):
        self.prompts.append(prompt)
        return self.texte.pop(0)


def test_llm_auswahl_filtert_ungueltige_nummern():
    fs = [Fundstelle(c, 'h', 'x', 1, i, c) for i, c in enumerate('abcdefg')]
    assert [f.id for f in ab.llm_auswahl(_Prov([3, 99, 3, 1, 0, 'x', 2, 4, 5, 6]), 'q', fs)] == ['c', 'a', 'b', 'd', 'e']
    assert ab.llm_auswahl(_Prov([]), 'q', fs) == []


def test_kaskade_fasst_nur_ohne_gueltiges_zitat_nach():
    import argparse
    fs = {c: Fundstelle(c, 'h', 'x', 1, i, f'Text {c}') for i, c in enumerate('abcde')}
    eintrag = {'kontext': [{'id': c, 'score': s} for c, s in zip('abcde', (0.9, 0.2, 0.1, 0.05, 0.01))]}
    a = argparse.Namespace(umgekehrt=False, mischen=False, llm_auswahl=False, top_n=20, dynamisch=True,
                           dedupe=False, zitat_zuerst=False, kaskade=True)
    top, text, stufe = ab.beantworte({'nr': 1, 'frage': 'q'}, eintrag, a, _Prov(texte=['nicht gefunden', 'X [c]']), fs)
    assert stufe == 2 and [f.id for f in top] == list('abcde') and text == 'X [c]'
    top, text, stufe = ab.beantworte({'nr': 1, 'frage': 'q'}, eintrag, a, _Prov(texte=['Y [a]']), fs)
    assert stufe == 1 and [f.id for f in top] == ['a']


class _ProvPruef(_Prov):
    def __init__(self, texte, belegt):
        super().__init__(texte=texte)
        self.belegt_antwort = belegt

    def generate_json(self, prompt, schema):
        self.prompts.append(prompt)
        return {'belegt': self.belegt_antwort}


def _ns(**k):
    import argparse
    basis = dict(umgekehrt=False, mischen=False, llm_auswahl=False, top_n=20, dynamisch=True, dedupe=False,
                 zitat_zuerst=False, kaskade=True, stufe2_streng=False, stufe2_pruefung=False)
    return argparse.Namespace(**{**basis, **k})


FS = {c: Fundstelle(c, 'h', 'x', 1, i, f'Text {c}') for i, c in enumerate('abc')}
EINTRAG = {'kontext': [{'id': c, 'score': s} for c, s in zip('abc', (0.9, 0.1, 0.05))]}


def test_stufe2_streng_nur_im_nachgriff():
    prov = _Prov(texte=['nicht gefunden', 'X [b]'])
    ab.beantworte({'nr': 1, 'frage': 'q'}, EINTRAG, _ns(stufe2_streng=True), prov, FS)
    assert 'genau den erfragten Vorgang' not in prov.prompts[0]
    assert 'genau den erfragten Vorgang' in prov.prompts[1]
    assert prov.prompts[1].index('genau den erfragten') < prov.prompts[1].index('Absätze:')


def test_stufe2_pruefung_verwirft_unbelegte_antwort():
    top, text, stufe = ab.beantworte({'nr': 1, 'frage': 'q'}, EINTRAG, _ns(stufe2_pruefung=True),
                                     _ProvPruef(['nicht gefunden', 'X [b]'], 'nein'), FS)
    assert stufe == 2 and text == 'nicht gefunden'
    top, text, stufe = ab.beantworte({'nr': 1, 'frage': 'q'}, EINTRAG, _ns(stufe2_pruefung=True),
                                     _ProvPruef(['nicht gefunden', 'X [b]'], 'ja'), FS)
    assert text == 'X [b]'
    prov = _ProvPruef(['Y [a]'], 'nein')  # Stufe 1 wird nie geprüft
    top, text, stufe = ab.beantworte({'nr': 1, 'frage': 'q'}, EINTRAG, _ns(stufe2_pruefung=True), prov, FS)
    assert stufe == 1 and text == 'Y [a]' and len(prov.prompts) == 1

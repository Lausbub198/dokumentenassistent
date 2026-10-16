from dokumentenassistent import gold_mehrfach as gm
from dokumentenassistent.typen import Fundstelle


def test_kurze_sollwerte():
    assert gm.kurz('2019') and gm.kurz('3') and gm.kurz('12.05.') and gm.kurz('EUR')
    assert not gm.kurz('750,00 EUR') and not gm.kurz('Hausverwaltung Nord')


def test_entscheidungen_lesen(tmp_path):
    p = tmp_path / 's.md'
    p.write_text('<!-- 3:aaaaaaaaaaaaaaaa -->\n- [x] trägt die Antwort   - [ ] trägt nicht\n'
                 '<!-- 4:bbbbbbbbbbbbbbbb -->\n- [ ] trägt die Antwort   - [X] trägt nicht\n'
                 '<!-- 5:cccccccccccccccc -->\n- [x] trägt die Antwort   - [x] trägt nicht\n'
                 '<!-- 6:dddddddddddddddd -->\n- [ ] trägt die Antwort   - [ ] trägt nicht\n', encoding='utf-8')
    assert gm.lies_entscheidungen(p) == {(3, 'a' * 16): True, (4, 'b' * 16): False}
    assert gm.lies_entscheidungen(tmp_path / 'fehlt.md') == {}


class _Index:
    def __init__(self, fs):
        self.fs = fs

    def dateien(self):
        from dokumentenassistent.typen import Datei
        from pathlib import Path
        return (Datei('h' * 64, Path('/x/Vertrag.pdf'), 'Vertrag.pdf', 1),)

    def fundstellen(self, h):
        return self.fs


def test_akzeptiert_regel_und_nutzer_entscheidung_schlaegt_regel(monkeypatch):
    gold = Fundstelle('g', 'h' * 64, 'Vertrag.pdf', 1, 0, 'Die Miete beträgt 750,00 EUR.')
    wert = Fundstelle('w', 'h' * 64, 'Vertrag.pdf', 2, 0, 'Neue Miete: 750,00 EUR ab Mai.')
    fremd = Fundstelle('f', 'x' * 64, 'Anderes.pdf', 1, 0, '750,00 EUR')
    ohne = Fundstelle('o', 'h' * 64, 'Vertrag.pdf', 3, 0, 'Kaution drei Monatsmieten.')
    fragen = [{'nr': 1, 'status': 'gefunden', 'datei': 'Vertrag.pdf', 'wortlaut_enthaelt': '750,00 EUR',
               'zielabsatz': 'Die Miete beträgt 750,00 EUR.'}]
    ix = _Index([gold, wert, ohne])
    mf = gm.Mehrfach(fragen, ix, {})
    assert mf.akzeptiert(1, gold) and mf.akzeptiert(1, wert)
    assert not mf.akzeptiert(1, fremd) and not mf.akzeptiert(1, ohne)
    mf2 = gm.Mehrfach(fragen, ix, {(1, gm.texthash(wert.text)): False, (1, gm.texthash(fremd.text)): True})
    assert not mf2.akzeptiert(1, wert) and mf2.akzeptiert(1, fremd)

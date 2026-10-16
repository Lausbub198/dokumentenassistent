from dokumentenassistent import werkstatt as wm
from dokumentenassistent.provider import Sucheinstellungen
from tests.conftest import FakeProvider


def test_frage_reicht_kaskaden_schalter_an_suche_durch(tmp_path, monkeypatch):
    gesehen = {}

    def fake_suche(text, paare, provider, **kw):
        gesehen.update(kw)
        from dokumentenassistent.typen import Antwort
        return Antwort(status='nicht_gefunden', text='nicht gefunden', karten=())

    monkeypatch.setattr(wm, 'suche', fake_suche)
    e = Sucheinstellungen(top_n=20, schwelle=0.0, kontextauswahl='dynamisch', kaskade=True, kaskade_stufe2='pruefung')
    w = wm.Werkstatt(tmp_path / 'q', tmp_path / 'z', FakeProvider(), arbeitsordner=tmp_path / 'w', sucheinstellungen=e)
    w.frage('Wie hoch ist die Miete?')
    assert (gesehen['schwelle'], gesehen['kontextauswahl'], gesehen['kaskade'], gesehen['kaskade_stufe2'], gesehen['top_n']) \
        == (0.0, 'dynamisch', True, 'pruefung', 20)
    gesehen.clear()
    wm.Werkstatt(tmp_path / 'q2', tmp_path / 'z2', FakeProvider(), arbeitsordner=tmp_path / 'w2').frage('x')
    assert 'schwelle' not in gesehen and gesehen['kaskade'] is False and gesehen['kontextauswahl'] == 'fest'

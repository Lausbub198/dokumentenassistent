from pathlib import Path

from dokumentenassistent import praefix_test
from dokumentenassistent.provider import Sucheinstellungen
from dokumentenassistent.suche import VORVERARBEITUNG, pfad_praefix, suche
from dokumentenassistent.typen import Datei, Fundstelle
from dokumentenassistent.werkstatt import Werkstatt
from tests.conftest import FakeProvider
from tests.test_M11_suche import F_HEIZ, F_MIET, FRAGE_HEIZ, FakeReranker, _paare


class _MerkProvider(FakeProvider):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.eingebettet: list[str] = []

    def embed(self, texte):
        self.eingebettet.extend(texte)
        return super().embed(texte)


def test_praefix_format_gleich_wie_in_der_messung():
    assert pfad_praefix('Wohnung Nord/Vertrag.pdf') == praefix_test.praefix('B', 'Wohnung Nord/Vertrag.pdf', None, '')
    assert pfad_praefix('') == ''


def test_reranker_sieht_praefix_prompt_nicht():
    reranker = FakeReranker({})
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    praefixe = {F_HEIZ.datei_hash: 'Dokument: Heizung/Rechnung (2).pdf\n\n', F_MIET.datei_hash: 'Dokument: X\n\n'}
    suche(FRAGE_HEIZ, _paare(), prov, reranker=reranker, kontext_praefix=praefixe)
    assert any(t.startswith('Dokument: Heizung/') and t.endswith(F_HEIZ.text) for t in reranker.aufrufe[0][1])
    assert 'Dokument:' not in prov.aufrufe[0][1]


def _werkstatt(tmp_path, praefix, provider):
    quelle = tmp_path / 'q'
    (quelle / 'Nord').mkdir(parents=True)
    pdf = quelle / 'Nord' / 'a.pdf'
    pdf.write_bytes(b'x')
    w = Werkstatt(quelle, tmp_path / 'z', provider, arbeitsordner=tmp_path / 'w',
                  sucheinstellungen=Sucheinstellungen(kontext_praefix=praefix))
    w.index.registriere(Datei('h1', pdf, 'a.pdf', 1), 'unklar')
    w.index.speichere_fundstellen((Fundstelle('a.pdf#S1#A1', 'h1', 'a.pdf', 1, 1, 'Betrag 10 EUR'),))
    return w


def test_einbetten_mit_praefix_und_eigener_herkunft(tmp_path):
    prov = _MerkProvider()
    w = _werkstatt(tmp_path, 'pfad', prov)
    w._bette_nach_ein()
    assert prov.eingebettet == ['Dokument: Nord/a.pdf\n\nBetrag 10 EUR']
    rev = prov.embedding_revision()
    assert len(w.index.durchsuchbare_fundstellen(modell_revision=rev, vorverarbeitung=VORVERARBEITUNG['pfad'])) == 1
    assert w.index.durchsuchbare_fundstellen(modell_revision=rev, vorverarbeitung='raw-v1') == ()


def test_wechsel_des_praefix_mischt_keine_vektoren(tmp_path):
    prov = _MerkProvider()
    ohne = _werkstatt(tmp_path, 'keiner', prov)
    ohne._bette_nach_ein()
    assert prov.eingebettet == ['Betrag 10 EUR']
    mit = Werkstatt(ohne.quelle, tmp_path / 'z', prov, arbeitsordner=tmp_path / 'w',
                    sucheinstellungen=Sucheinstellungen(kontext_praefix='pfad'))
    rev = prov.embedding_revision()
    # Vor dem Neu-Einbetten findet die Präfix-Suche nichts – die alten Vektoren zählen nicht mit.
    assert mit.index.durchsuchbare_fundstellen(modell_revision=rev, vorverarbeitung=VORVERARBEITUNG['pfad']) == ()
    assert len(mit.index.fundstellen_ohne_embedding(modell_revision=rev, vorverarbeitung=VORVERARBEITUNG['pfad'])) == 1
    mit._bette_nach_ein()
    assert prov.eingebettet[-1] == 'Dokument: Nord/a.pdf\n\nBetrag 10 EUR'


def test_datei_ausserhalb_der_quelle_nutzt_den_dateinamen(tmp_path):
    w = Werkstatt(tmp_path / 'q', tmp_path / 'z', FakeProvider(), arbeitsordner=tmp_path / 'w',
                  sucheinstellungen=Sucheinstellungen(kontext_praefix='pfad'))
    w.index.registriere(Datei('h2', Path('/anderswo/b.pdf'), 'b.pdf', 1), 'unklar')
    assert w._praefixe() == {'h2': 'Dokument: b.pdf\n\n'}


def test_einbetten_in_bloecken_abbruch_verliert_nur_einen_block(tmp_path):
    class Bricht(_MerkProvider):
        def __init__(self):
            super().__init__(); self.aufrufe_embed = 0

        def embed(self, texte):
            self.aufrufe_embed += 1
            if self.aufrufe_embed == 2:
                raise RuntimeError('Zeitlimit')
            return super().embed(texte)

    prov = Bricht()
    w = _werkstatt(tmp_path, 'keiner', prov)
    w.EMBED_BLOCK = 2
    w.index.speichere_fundstellen(tuple(Fundstelle(f'a.pdf#S1#A{i}', 'h1', 'a.pdf', 1, i, f'Text {i}') for i in range(2, 6)))
    import pytest
    with pytest.raises(RuntimeError):
        w._bette_nach_ein()
    rev = prov.embedding_revision()
    assert len(w.index.durchsuchbare_fundstellen(modell_revision=rev)) == 2  # erster Block gespeichert
    w._bette_nach_ein()  # Fortsetzung bettet nur den Rest ein
    assert len(w.index.durchsuchbare_fundstellen(modell_revision=rev)) == 5

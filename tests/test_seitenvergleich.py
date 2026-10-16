import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from dokumentenassistent.index import Index
from dokumentenassistent.typen import Datei, Fundstelle, Seite


def _fixture(tmp_path):
    quelle = tmp_path / 'quelle'
    quelle.mkdir()
    ix = Index(quelle)
    for n in (1, 2):
        pfad = quelle / f'dokument{n}.md'
        pfad.write_text(f'privater Text {n}', encoding='utf-8')
        ix.registriere(Datei(str(n) * 64, pfad, pfad.name, pfad.stat().st_size), 'unklar')
    gold = tmp_path / 'gold.json'
    gold.write_text(json.dumps({'fragen': [
        {'nr': 1, 'status': 'gefunden', 'frage': 'Wo steht Teil zweiter?', 'datei': 'DOKUMENT1.MD',
         'wortlaut_enthaelt': 'Teil\nzweiter', 'zielabsatz': 'Erster Teil zweiter Teil'},
        {'nr': 2, 'status': 'nicht_gefunden', 'frage': 'Unbekannt?', 'datei': None,
         'wortlaut_enthaelt': None, 'zielabsatz': None},
    ]}), encoding='utf-8')
    return quelle, gold


def test_strukturvergleich_nutzt_extraktion_einmal_und_schreibt_nur_in_private_ausgabe(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    aufrufe = []

    def extraktor(pfad, _ocr):
        aufrufe.append(pfad)
        return (Seite(1, 'Erster Teil', False, None),
                Seite(2, 'zweiter Teil', False, None))

    monkeypatch.setattr(modul, 'lies_seiten', extraktor)
    ziel = tmp_path / 'privat'
    bericht = modul.strukturvergleich(quelle, gold, ziel)
    assert len(aufrufe) == 2
    assert bericht['dokumente']['verarbeitet'] == 2
    assert bericht['fragen']['positiv'] == 1
    assert bericht['fragen']['negativ'] == 1
    assert bericht['vektoren'] == {'baseline': 0, 'seitenuebergreifend': 0}
    assert bericht['wortlaut_exakt'] == {'baseline': 0, 'seitenuebergreifend': 1}
    assert bericht['veraenderte_fragen'] == [1]
    assert 'privater Text' not in (ziel / 'bericht.json').read_text()
    assert 'dokument1.md' not in (ziel / 'bericht.json').read_text()
    assert len(Index(ziel / 'baseline').fundstellen('1' * 64)) == 2
    neu = Index(ziel / 'seitenuebergreifend').fundstellen('1' * 64)
    assert len(neu) == 1 and neu[0].seiten == (1, 2)


def test_strukturvergleich_verweigert_vorhandenes_ziel(tmp_path):
    from dokumentenassistent.seitenvergleich import strukturvergleich

    quelle, gold = _fixture(tmp_path)
    ziel = tmp_path / 'privat'
    ziel.mkdir()
    with pytest.raises(FileExistsError):
        strukturvergleich(quelle, gold, ziel)


def test_fortsetzung_prueft_hashes_und_extrahiert_fertige_dateien_nicht_erneut(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    ziel = tmp_path / 'privat'
    aufrufe = []

    def extraktor(pfad, _ocr):
        aufrufe.append(pfad)
        return (Seite(1, 'Text', False, None),)

    monkeypatch.setattr(modul, 'lies_seiten', extraktor)
    original = modul.strukturvergleich(quelle, gold, ziel)
    assert len(aufrufe) == 2
    assert modul.strukturvergleich(quelle, gold, ziel, resume=True) == original
    assert len(aufrufe) == 2
    (quelle / 'dokument1.md').write_text('veraendert', encoding='utf-8')
    with pytest.raises(ValueError, match='Manifest'):
        modul.strukturvergleich(quelle, gold, ziel, resume=True)


def test_private_ausgabe_im_git_baum_wird_verweigert(tmp_path):
    from dokumentenassistent.seitenvergleich import strukturvergleich

    quelle, gold = _fixture(tmp_path)
    gitbaum = tmp_path / 'gitbaum'
    gitbaum.mkdir()
    (gitbaum / '.git').mkdir()
    with pytest.raises(ValueError, match='Git-Baum'):
        strukturvergleich(quelle, gold, gitbaum / 'lauf')


def test_fortsetzung_verweigert_fehlende_oder_veraenderte_ab_ergebnisse(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    ziel = tmp_path / 'privat'
    monkeypatch.setattr(modul, 'lies_seiten', lambda *_: (Seite(1, 'Text', False, None),))
    modul.strukturvergleich(quelle, gold, ziel)
    baseline_db = ziel / 'baseline' / '.dokumentenassistent' / 'index.sqlite'
    with sqlite3.connect(baseline_db) as db:
        db.execute("UPDATE fundstellen SET text='manipuliert'")
    with pytest.raises(ValueError, match='Ergebnis'):
        modul.strukturvergleich(quelle, gold, ziel, resume=True)
    baseline_db.unlink()
    with pytest.raises(ValueError, match='Ergebnis'):
        modul.strukturvergleich(quelle, gold, ziel, resume=True)


def test_retrievalvergleich_nutzt_einen_fragevektor_fuer_beide_arme_und_misst_kontext(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    monkeypatch.setattr(modul, 'lies_seiten', lambda pfad, _: (
        Seite(1, 'Erster Teil' if pfad.name == 'dokument1.md' else 'Anderes Thema', False, None),
        Seite(2, 'zweiter Teil' if pfad.name == 'dokument1.md' else 'ohne Antwort', False, None)))
    struktur = tmp_path / 'struktur'
    modul.strukturvergleich(quelle, gold, struktur)

    class Provider:
        def __init__(self):
            self.queries = 0
            self.revision = 'test-digest-1'

        def embedding_revision(self):
            return self.revision

        def embed(self, texte):
            if any('?' in text for text in texte):
                self.queries += 1
            return [[-1., 0.] if text == 'Unbekannt?' else
                    [0., 1.] if 'Anderes' in text or 'ohne Antwort' in text else
                    [1., 0.] for text in texte]

    class Reranker:
        modell_name = 'BAAI/bge-reranker-v2-m3'
        revision = 'test-reranker-1'

        def bewerte(self, frage, texte):
            return [1. if 'zweiter Teil' in text else 0. for text in texte]

    provider = Provider()
    privat = tmp_path / 'retrieval'
    bericht = modul.retrievalvergleich(struktur, gold, privat, provider, Reranker(),
                                        erwartet=(1, 1))
    assert provider.queries == 1
    assert bericht['fragen'] == {'positiv': 1, 'negativ': 1}
    assert bericht['gewinne'] == [1]
    assert bericht['verluste'] == []
    assert bericht['negative_blockiert'] == {'baseline': 1, 'seitenuebergreifend': 1}
    assert bericht['kontexttreffer'] == {'baseline': 0, 'seitenuebergreifend': 1}
    assert bericht['zielabsatz_auswertbar'] == {'baseline': 0, 'seitenuebergreifend': 1}
    assert bericht['zielabsatz_nicht_im_index'] == {'baseline': [1], 'seitenuebergreifend': []}
    assert bericht['ranking_verluste'] == {'baseline': [], 'seitenuebergreifend': []}
    assert bericht['schwelle_blockiert'] == {'baseline': [], 'seitenuebergreifend': []}
    assert 'Wo steht' not in (privat / 'bericht.json').read_text()
    resultate = json.loads((privat / 'ergebnisse.json').read_text())['resultate']
    assert len(resultate) == 2
    assert resultate['1']['baseline']['zielchunk_rang_dense'] is None
    assert resultate['1']['seitenuebergreifend']['zielchunk_rang_dense'] == 1
    assert resultate['1']['seitenuebergreifend']['zielchunk_rang_reranked'] == 1
    assert modul.retrievalvergleich(struktur, gold, privat, provider, Reranker(),
                                     erwartet=(1, 1), resume=True) == bericht
    assert provider.queries == 1
    provider.revision = 'test-digest-2'
    with pytest.raises(ValueError, match='Revision|Manifest'):
        modul.retrievalvergleich(struktur, gold, privat, provider, Reranker(),
                                 erwartet=(1, 1), resume=True)
    provider.revision = 'test-digest-1'
    andere_revision = Reranker()
    andere_revision.revision = 'test-reranker-2'
    with pytest.raises(ValueError, match='Revision|Manifest'):
        modul.retrievalvergleich(struktur, gold, privat, provider, andere_revision,
                                 erwartet=(1, 1), resume=True)
    manifestpfad = privat / 'manifest.json'
    manifest = json.loads(manifestpfad.read_text())
    manifest['auswertung_code_sha256'] = 'alte-auswertung'
    manifestpfad.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Manifest'):
        modul.retrievalvergleich(struktur, gold, privat, provider, Reranker(),
                                 erwartet=(1, 1), resume=True)
    erneuert = modul.retrievalvergleich(struktur, gold, privat, provider, Reranker(),
                                        erwartet=(1, 1), resume=True, recompute=True)
    assert erneuert['kontexttreffer'] == bericht['kontexttreffer']
    assert provider.queries == 1
    assert list(privat.glob('ergebnisse.alt-*.json'))


def test_retrievalvergleich_verweigert_veraenderte_strukturkopie(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    monkeypatch.setattr(modul, 'lies_seiten', lambda *_: (Seite(1, 'Text', False, None),))
    struktur = tmp_path / 'struktur'
    modul.strukturvergleich(quelle, gold, struktur)
    db = struktur / 'baseline' / '.dokumentenassistent' / 'index.sqlite'
    with sqlite3.connect(db) as verbindung:
        verbindung.execute("UPDATE fundstellen SET text='manipuliert'")
    with pytest.raises(ValueError, match='Struktur|Hash'):
        modul.retrievalvergleich(struktur, gold, tmp_path / 'retrieval', object(), object(),
                                 erwartet=(1, 1))


def test_bereinigtes_gold_nur_mit_passender_herkunft(tmp_path, monkeypatch):
    import hashlib
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    monkeypatch.setattr(modul, 'lies_seiten', lambda *_: (Seite(1, 'Text', False, None),))
    struktur = tmp_path / 'struktur'
    modul.strukturvergleich(quelle, gold, struktur)
    daten = json.loads(gold.read_text())
    abgeleitet, fremd = tmp_path / 'v2.json', tmp_path / 'fremd.json'
    basis = hashlib.sha256(gold.read_bytes()).hexdigest()
    abgeleitet.write_text(json.dumps({**daten, 'bereinigung': {'basis_sha256': basis}}))
    fremd.write_text(json.dumps({**daten, 'bereinigung': {'basis_sha256': '0' * 64}}))
    assert modul._pruefe_struktur(struktur, abgeleitet)['gold_sha256'] == basis
    with pytest.raises(ValueError, match='Gold-Hash'):
        modul._pruefe_struktur(struktur, fremd)


def test_retrievalvergleich_prueft_15_negative_und_retrieval_kopie(tmp_path, monkeypatch):
    import dokumentenassistent.seitenvergleich as modul

    quelle, gold = _fixture(tmp_path)
    daten = json.loads(gold.read_text())
    daten['fragen'].extend({'nr': nr, 'status': 'nicht_gefunden', 'frage': f'Unbekannt {nr}?',
                           'datei': None, 'wortlaut_enthaelt': None, 'zielabsatz': None}
                          for nr in range(3, 17))
    gold.write_text(json.dumps(daten))
    monkeypatch.setattr(modul, 'lies_seiten', lambda *_: (Seite(1, 'Antworttext', False, None),))
    struktur = tmp_path / 'struktur'
    modul.strukturvergleich(quelle, gold, struktur)

    class Provider:
        def embedding_revision(self):
            return 'test-digest'

        def embed(self, texte):
            return [[-1., 0.] if '?' in t else [1., 0.] for t in texte]

    class Reranker:
        modell_name = 'BAAI/bge-reranker-v2-m3'
        revision = 'test-reranker-1'

        def bewerte(self, frage, texte):
            return [1.] * len(texte)

    privat = tmp_path / 'retrieval'
    bericht = modul.retrievalvergleich(struktur, gold, privat, Provider(), Reranker(),
                                        erwartet=(1, 15))
    assert bericht['negative_blockiert'] == {'baseline': 15, 'seitenuebergreifend': 15}
    assert len(json.loads((privat / 'ergebnisse.json').read_text())['resultate']) == 16
    with sqlite3.connect(privat / 'baseline' / '.dokumentenassistent' / 'index.sqlite') as db:
        db.execute("UPDATE fundstellen SET text='manipuliert'")
    with pytest.raises(ValueError, match='Retrieval-Struktur-Hash'):
        modul.retrievalvergleich(struktur, gold, privat, Provider(), Reranker(),
                                 erwartet=(1, 15), resume=True)


def test_retrieval_gate_prueft_nur_den_besten_score_nicht_jeden_kandidaten(tmp_path):
    from dokumentenassistent.seitenvergleich import _messe_frage

    datei = Datei('a' * 64, tmp_path / 'dokument.md', 'dokument.md', 1)
    fundstellen = [Fundstelle('ablenkung', datei.hash, datei.name, 1, 1, 'Ablenkung'),
                   Fundstelle('ziel', datei.hash, datei.name, 1, 2, 'Gold-Wortlaut')]

    class IndexStub:
        def dateien(self):
            return (datei,)

        def fundstellen(self, hash_):
            return tuple(fundstellen)

    class Reranker:
        def bewerte(self, frage, texte):
            return [1.] * len(texte)

    matrix = np.asarray([[1., 0.], [0.4, (1 - 0.4 ** 2) ** 0.5]], dtype=np.float32)
    frage = {'nr': 1, 'status': 'gefunden', 'frage': 'Welche Angabe?',
             'datei': datei.name, 'wortlaut_enthaelt': 'Gold-Wortlaut',
             'zielabsatz': 'Gold-Wortlaut'}
    messung = _messe_frage(frage, [1., 0.], IndexStub(), fundstellen, matrix, Reranker())
    assert messung['zielchunk_rang_dense'] == 2
    assert messung['kontexttreffer'] is True
    assert messung['kontext_chunks'] == 2


def test_retrieval_zielrang_ignoriert_gleichen_wert_ohne_stuetzenden_absatz(tmp_path):
    from dokumentenassistent.seitenvergleich import _messe_frage

    datei = Datei('a' * 64, tmp_path / 'dokument.md', 'dokument.md', 1)
    fundstellen = [
        Fundstelle('falscher-wert', datei.hash, datei.name, 1, 1,
                   '21 Stellplätze sind vorgesehen.'),
        Fundstelle('richtiger-absatz', datei.hash, datei.name, 2, 1,
                   'Im Haus B werden 21 Eigentumswohnungen entstehen.'),
    ]

    class IndexStub:
        def dateien(self):
            return (datei,)

        def fundstellen(self, hash_):
            return tuple(fundstellen)

    class Reranker:
        def bewerte(self, frage, texte):
            return [1.] * len(texte)

    matrix = np.asarray([[1., 0.], [0.4, (1 - 0.4 ** 2) ** 0.5]], dtype=np.float32)
    frage = {'nr': 1, 'status': 'gefunden', 'frage': 'Wie viele Wohnungen in Haus B?',
             'datei': datei.name, 'wortlaut_enthaelt': '21',
             'zielabsatz': 'Im Haus B werden 21 Eigentumswohnungen entstehen.'}
    messung = _messe_frage(frage, [1., 0.], IndexStub(), fundstellen, matrix, Reranker())
    assert messung['zielchunk_rang_dense'] == 2
    assert messung['zielchunk_rang_reranked'] == 2
    assert messung['zielabsatz_im_index'] is True


def test_retrieval_markiert_fehlenden_zielabsatz_als_nicht_auswertbar(tmp_path):
    from dokumentenassistent.seitenvergleich import _messe_frage

    datei = Datei('a' * 64, tmp_path / 'dokument.md', 'dokument.md', 1)
    fundstelle = Fundstelle('nur-wert', datei.hash, datei.name, 1, 1,
                           '21 Stellplätze sind vorgesehen.')

    class IndexStub:
        def dateien(self):
            return (datei,)

        def fundstellen(self, hash_):
            return (fundstelle,)

    class Reranker:
        def bewerte(self, frage, texte):
            return [1.] * len(texte)

    frage = {'nr': 1, 'status': 'gefunden', 'frage': 'Wie viele Wohnungen in Haus B?',
             'datei': datei.name, 'wortlaut_enthaelt': '21',
             'zielabsatz': 'Im Haus B werden 21 Eigentumswohnungen entstehen.'}
    messung = _messe_frage(frage, [1., 0.], IndexStub(), [fundstelle],
                          np.asarray([[1., 0.]], dtype=np.float32), Reranker())
    assert messung['zielabsatz_im_index'] is False
    assert messung['zielchunk_rang_dense'] is None
    assert messung['kontexttreffer'] is False


def test_retrieval_meldet_schwellenblockade_separat_vom_rankingverlust(tmp_path):
    from dokumentenassistent.seitenvergleich import _messe_frage

    datei = Datei('a' * 64, tmp_path / 'dokument.md', 'dokument.md', 1)
    fundstelle = Fundstelle('ziel', datei.hash, datei.name, 1, 1, 'Gold-Wortlaut')

    class IndexStub:
        def dateien(self):
            return (datei,)

        def fundstellen(self, hash_):
            return (fundstelle,)

    class Reranker:
        def bewerte(self, frage, texte):
            return [1.] * len(texte)

    frage = {'nr': 1, 'status': 'gefunden', 'frage': 'Welche Angabe?',
             'datei': datei.name, 'wortlaut_enthaelt': 'Gold-Wortlaut',
             'zielabsatz': 'Gold-Wortlaut'}
    matrix = np.asarray([[0.4, (1 - 0.4 ** 2) ** 0.5]], dtype=np.float32)
    messung = _messe_frage(frage, [1., 0.], IndexStub(), [fundstelle], matrix, Reranker())
    assert messung['zielchunk_rang_dense'] == 1
    assert messung['schwelle_blockiert'] is True
    assert messung['kontexttreffer'] is False

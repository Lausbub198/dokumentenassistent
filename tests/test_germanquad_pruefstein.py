import json

from dokumentenassistent import germanquad_pruefstein as gp
from dokumentenassistent.typen import Antwort, Belegkarte, Fundstelle


def test_stichprobe_fest_und_sortiert():
    gold = [{'nr': i} for i in range(1, 501)]
    a, b = gp.stichprobe(gold), gp.stichprobe(gold)
    assert a == b and len(a) == 200 and [f['nr'] for f in a] == sorted(f['nr'] for f in a)
    assert len(gp.stichprobe(gold[:50])) == 50


def test_vorbereiten_schreibt_absatzdateien_und_gold(tmp_path, monkeypatch):
    tabellen = {'corpus.arrow': [{'_id': 'c1', 'text': 'Berlin ist die Hauptstadt.'}],
                'queries.arrow': [{'_id': 'q1', 'text': 'Was ist die Hauptstadt?'}],
                'qrels.arrow': [{'query-id': 'q1', 'corpus-id': 'c1'}]}
    import dokumentenassistent.germanquad as g
    monkeypatch.setattr(g, '_spalten', lambda pfad, namen: tabellen[pfad.name])
    assert gp.vorbereiten(tmp_path / 'quelle', tmp_path / 'ziel') == {'absaetze': 1, 'fragen': 1}
    assert (tmp_path / 'ziel/bestand/c1.txt').read_text() == 'Berlin ist die Hauptstadt.'
    gold = json.loads((tmp_path / 'ziel/gold.json').read_text())['fragen']
    assert gold == [{'nr': 1, 'frage': 'Was ist die Hauptstadt?', 'status': 'gefunden', 'datei': 'c1.txt'}]


def test_antworten_absatzgenau_und_wiederaufnehmbar(tmp_path):
    f = Fundstelle('c1.txt#S1#A1', 'h', 'c1.txt', 1, 1, 'Berlin')

    class W:
        def frage(self, text):
            return Antwort('gefunden', 'Berlin [x]', (Belegkarte(f, f.text),)) if text == 'a' else \
                Antwort('nicht_gefunden', 'nicht gefunden', ())
    fragen = [{'nr': 1, 'frage': 'a', 'datei': 'c1.txt'}, {'nr': 2, 'frage': 'b', 'datei': 'c2.txt'}]
    aus = tmp_path / 'a.jsonl'
    assert gp.antworten(W(), fragen, aus)['korrekt'] == 1
    assert gp.antworten(None, fragen, aus) == {'fragen': 2, 'korrekt': 1, 'abgewiesen': 1, 'sekunden_median': 0.0}


def test_fragen_werden_in_bloecken_eingebettet():
    """Ein Aufruf mit allen 2204 Fragen wurde von Ollama mit HTTP 400 abgelehnt (03./04.10.2026)."""
    aufrufe = []

    class P:
        def embed(self, texte):
            aufrufe.append(len(texte))
            return [[float(len(t))] for t in texte]
    texte = [str(i) for i in range(70)]
    assert gp.einbetten_in_bloecken(P(), texte) == [[float(len(t))] for t in texte]
    assert aufrufe == [32, 32, 6]

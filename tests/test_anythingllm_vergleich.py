import json

import httpx

from dokumentenassistent import anythingllm_vergleich as av

FRAGE = {'nr': 1, 'frage': 'Wie hoch ist die Miete?', 'status': 'gefunden', 'datei': 'ordner/Vertrag.pdf',
         'wortlaut_enthaelt': '750,00 EUR', 'zielabsatz': 'Die Miete beträgt 750,00 EUR monatlich.'}
META = '<document_metadata>\nsourceDocument: Vertrag.pdf\n</document_metadata>\n\n'


def test_konfiguration_meldet_abweichungen():
    ok = dict(av.SOLL)
    assert av.pruefe_konfiguration(ok) == []
    falsch = {**ok, 'LLMProvider': 'lmstudio'}
    assert av.pruefe_konfiguration(falsch) == ["LLMProvider: 'lmstudio' statt 'ollama'"]


def test_treffer_drei_masse_und_metadaten_header_ignoriert():
    treffer = [
        {'titel': 'Anderes.pdf', 'text': 'Die Miete beträgt 750,00 EUR monatlich.'},
        {'titel': 'Vertrag.pdf', 'text': META + 'Kaution 3 Monatsmieten.'},
        {'titel': 'Vertrag.pdf', 'text': META + 'Stand: 750,00 EUR'},
        {'titel': 'Vertrag.pdf', 'text': META + 'Die Miete  beträgt\n750,00 EUR monatlich.'},
    ]
    assert av.bewerte_treffer(FRAGE, treffer) == {'rang_datei': 2, 'rang_wortlaut': 3, 'rang_zielabsatz': 4}


def test_wert_wird_nicht_im_dateinamen_gefunden():
    frage = {**FRAGE, 'wortlaut_enthaelt': 'Vertrag.pdf'}
    assert av.bewerte_treffer(frage, [{'titel': 'Vertrag.pdf', 'text': META + 'x'}])['rang_wortlaut'] is None


def test_antwort_abweisung_und_wert():
    quelle = [{'titel': 'Vertrag.pdf', 'text': 'Die Miete beträgt 750,00 EUR monatlich.'}]
    ok = av.bewerte_antwort(FRAGE, 'Die Miete liegt bei 750,00 EUR.', quelle)
    assert ok['antwort_enthaelt_wert'] and not ok['abgewiesen'] and ok['kontext_rang_zielabsatz'] == 1
    assert av.bewerte_antwort(FRAGE, av.ABGEWIESEN, quelle)['abgewiesen']
    leer = av.bewerte_antwort(FRAGE, '750,00 EUR', [])
    assert leer['abgewiesen'] and not leer['antwort_enthaelt_wert']
    # Anderer Betrag zählt nicht als Treffer
    assert not av.bewerte_antwort(FRAGE, '705,00 EUR', quelle)['antwort_enthaelt_wert']


def test_api_schluessel_env_vor_datenbank(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / 'a.db'
    with sqlite3.connect(db) as v:
        v.execute('CREATE TABLE api_keys (secret TEXT, createdAt TEXT)')
        v.executemany('INSERT INTO api_keys VALUES (?, ?)', [('alt', '2026-01-01'), ('neu', '2026-09-01')])
    monkeypatch.delenv('ANYTHINGLLM_API_KEY', raising=False)
    assert av.api_schluessel(db) == 'neu'
    monkeypatch.setenv('ANYTHINGLLM_API_KEY', 'env')
    assert av.api_schluessel(db) == 'env'
    monkeypatch.delenv('ANYTHINGLLM_API_KEY')
    assert av.api_schluessel(tmp_path / 'fehlt.db') is None


def test_konfigurieren_sichert_nur_einmal_und_zuruecksetzen_stellt_her(tmp_path):
    gesendet, stand = [], {'settings': {'LLMProvider': 'lmstudio', 'DisableTelemetry': False,
                                        'OllamaLLMModelPref': None}}

    def handler(request):
        if request.method == 'GET':
            return httpx.Response(200, json=stand)
        werte = json.loads(request.content)
        gesendet.append(werte)
        stand['settings'].update(werte)
        return httpx.Response(200, json={'newValues': werte, 'error': None})

    api = av.Api('x', client=httpx.Client(base_url='http://t/api', transport=httpx.MockTransport(handler)))
    av.konfigurieren(api, tmp_path)
    av.konfigurieren(api, tmp_path)  # zweiter Aufruf darf die Sicherung nicht überschreiben
    assert gesendet[0] == av.EINSTELLUNGEN
    vorher = json.loads((tmp_path / 'einstellungen-vorher.json').read_text())
    assert vorher['LLMProvider'] == 'lmstudio' and vorher['DisableTelemetry'] is False
    av.zuruecksetzen(api, tmp_path)
    assert gesendet[-1]['LLMProvider'] == 'lmstudio' and gesendet[-1]['DisableTelemetry'] == 'false'
    assert 'OllamaLLMModelPref' not in gesendet[-1]  # war vorher nicht gesetzt


def test_einlesen_ueberspringt_serverfehler_einer_datei(tmp_path, monkeypatch):
    from dokumentenassistent.typen import Datei
    dateien = []
    for n in (1, 2):
        p = tmp_path / f'd{n}.pdf'
        p.write_bytes(b'x')
        dateien.append(Datei(str(n) * 64, p, p.name, 1))
    monkeypatch.setattr(av, '_registrierte_dateien', lambda quelle: tuple(dateien))

    def handler(request):
        if request.url.path.endswith('/workspaces'):
            return httpx.Response(200, json={'workspaces': []})
        if request.url.path.endswith('/document/upload'):
            if b'd1.pdf' in request.content:
                return httpx.Response(500)
            return httpx.Response(200, json={'success': True, 'documents': [{'location': 'x/d2.json'}]})
        return httpx.Response(200, json={})

    api = av.Api('x', client=httpx.Client(base_url='http://t/api', transport=httpx.MockTransport(handler)))
    privat = tmp_path / 'p'
    privat.mkdir()
    ergebnis = av.einlesen(api, tmp_path, privat)
    assert ergebnis == {'hochgeladen': 1, 'fehler_hashes': ['1' * 64]}


def test_messen_ist_wiederaufnehmbar(tmp_path):
    aufrufe = []

    def handler(request):
        aufrufe.append(request.url.path)
        if request.url.path.endswith('/vector-search'):
            return httpx.Response(200, json={'results': [
                {'text': META + FRAGE['zielabsatz'], 'metadata': {'title': 'Vertrag.pdf'}, 'score': 0.61}]})
        return httpx.Response(200, json={'textResponse': '750,00 EUR', 'error': None,
                                         'sources': [{'title': 'Vertrag.pdf', 'text': FRAGE['zielabsatz']}]})

    api = av.Api('x', client=httpx.Client(base_url='http://t/api', transport=httpx.MockTransport(handler)))
    neg = {'nr': 2, 'frage': 'Gibt es einen Garagenvertrag?', 'status': 'nicht_gefunden'}
    assert av.messen(api, [FRAGE, neg], tmp_path) == 4
    assert av.messen(api, [FRAGE, neg], tmp_path) == 0
    assert sum(p.endswith('/vector-search') for p in aufrufe) == 2
    zeilen = [json.loads(z) for z in (tmp_path / 'ergebnisse.jsonl').read_text().splitlines()]
    bericht = av.auswerten(zeilen)
    assert bericht['standard']['kontext_zielabsatz'] == 1
    assert bericht['standard']['antwort_enthaelt_wert'] == 1
    assert bericht['standard']['negativ_korrekt_abgewiesen'] == 0
    assert bericht['retrieval_ohne_llm_top20']['rang_zielabsatz'] == {'top1': 1, 'top4': 1, 'top20': 1}
    assert '750,00' not in json.dumps(bericht)  # keine Antworttexte im Bericht

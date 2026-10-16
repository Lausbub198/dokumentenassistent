import io
import json

import pytest

from dokumentenassistent import provider as p


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _chat(inhalt, gesendet=None):
    def f(req, timeout=0):
        if gesendet is not None:
            gesendet['url'], gesendet['body'] = req.full_url, json.loads(req.data)
        return _Resp(json.dumps({'choices': [{'message': {'content': inhalt}}]}).encode())
    return f


def _prov():
    return p.LmStudioProvider('http://ollama', 'qwen3-embedding:4b', 'gemma-mlx', llm_host='http://lms:1234',
                              max_antwort_tokens=1024)


def test_text_geht_an_lm_studio_chat_mit_temperatur_null_und_grenze(monkeypatch):
    g = {}
    monkeypatch.setattr(p.urllib.request, 'urlopen', _chat('Die Miete beträgt 750 EUR [a].', g))
    assert _prov().generate_text('Frage?') == 'Die Miete beträgt 750 EUR [a].'
    assert g['url'] == 'http://lms:1234/v1/chat/completions'
    assert (g['body']['model'], g['body']['temperature'], g['body']['max_tokens']) == ('gemma-mlx', 0, 1024)
    assert g['body']['messages'] == [{'role': 'system', 'content': 'Antworte ausschließlich auf Deutsch.'},
                                     {'role': 'user', 'content': 'Frage?'}]


def test_json_sendet_schema_und_hat_keine_tokengrenze(monkeypatch):
    g = {}
    monkeypatch.setattr(p.urllib.request, 'urlopen', _chat('{"kategorie": "Nord"}', g))
    assert _prov().generate_json('x', {'type': 'object'}) == {'kategorie': 'Nord'}
    assert g['body']['response_format']['json_schema']['schema'] == {'type': 'object'}
    assert 'max_tokens' not in g['body']


def test_embedding_bleibt_bei_ollama(monkeypatch):
    g = {}
    def f(req, timeout=0):
        g['url'] = req.full_url
        return _Resp(json.dumps({'embeddings': [[0.1]]}).encode())
    monkeypatch.setattr(p.urllib.request, 'urlopen', f)
    assert _prov().embed(['a']) == [[0.1]]
    assert g['url'] == 'http://ollama/api/embed'


def test_ungueltiges_json_ergibt_schemafehler(monkeypatch):
    monkeypatch.setattr(p.urllib.request, 'urlopen', _chat('kein json'))
    with pytest.raises(p.SchemaFehler):
        _prov().generate_json('x', {'type': 'object'})


def test_lm_studio_nicht_erreichbar_nennt_lm_studio(monkeypatch):
    def f(req, timeout=0): raise ConnectionRefusedError()
    monkeypatch.setattr(p.urllib.request, 'urlopen', f)
    with pytest.raises(p.ProviderFehler, match='LM Studio'):
        _prov().generate_text('x')


def test_lade_modelle_waehlt_die_laufzeit(tmp_path):
    basis = 'host: http://h\nembedding: e\nllm: l\n'
    (tmp_path / 'a.yaml').write_text(basis)
    (tmp_path / 'b.yaml').write_text(basis + 'llm_laufzeit: lmstudio\nllm_host: http://lms:1234\n')
    (tmp_path / 'c.yaml').write_text(basis + 'llm_laufzeit: vllm\n')
    assert type(p.lade_modelle(tmp_path / 'a.yaml')) is p.OllamaProvider
    b = p.lade_modelle(tmp_path / 'b.yaml')
    assert (type(b), b.llm_host, b.host) == (p.LmStudioProvider, 'http://lms:1234', 'http://h')
    with pytest.raises(p.ProviderFehler, match='llm_laufzeit'):
        p.lade_modelle(tmp_path / 'c.yaml')

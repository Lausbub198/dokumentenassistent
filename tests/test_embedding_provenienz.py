import json
import pytest

from dokumentenassistent.provider import OllamaProvider, ProviderFehler
from dokumentenassistent.werkstatt import Werkstatt
from tests.conftest import FakeProvider
from tests.test_M1_provider import _Resp
from tests.test_M5_index import D, F


@pytest.mark.parametrize('response', [[], [[1, 2], [2, 1]], [[float('nan'), 1]], [[0, 0]]])
def test_incomplete_or_bad_embedding_batch_never_persists(tmp_path, response):
    class BadProvider(FakeProvider):
        def embed(self, texts):
            return response
    w = Werkstatt(tmp_path/'q', tmp_path/'z', BadProvider(), arbeitsordner=tmp_path/'work')
    w.index.registriere(D, 'unklar')
    w.index.speichere_fundstellen((F,))
    with pytest.raises(ValueError):
        w._bette_nach_ein()
    assert not w.index.durchsuchbare_fundstellen()


def test_interrupted_embedding_keeps_previous_index(tmp_path):
    class Interrupted(FakeProvider):
        def embed(self, texts):
            raise TimeoutError('synthetic timeout')
    w = Werkstatt(tmp_path/'q', tmp_path/'z', Interrupted(), arbeitsordner=tmp_path/'work')
    w.index.registriere(D, 'unklar')
    w.index.speichere_fundstellen((F,))
    with pytest.raises(TimeoutError):
        w._bette_nach_ein()
    assert w.index.fundstellen_ohne_embedding() == (F,)


def test_model_changed_during_embedding_discards_batch(tmp_path):
    class Changing(FakeProvider):
        def embed(self, texts):
            result = super().embed(texts)
            self.dim += 1
            return result
    w = Werkstatt(tmp_path/'q', tmp_path/'z', Changing(), arbeitsordner=tmp_path/'work')
    w.index.registriere(D, 'unklar')
    w.index.speichere_fundstellen((F,))
    with pytest.raises(ValueError, match='Modell'):
        w._bette_nach_ein()
    assert not w.index.durchsuchbare_fundstellen()


def test_model_revision_is_actual_digest_and_detects_replaced_tag(monkeypatch):
    digest = ['sha256:one']
    def respond(req, timeout=0):
        assert req.full_url == 'http://local/api/tags'
        return _Resp(json.dumps({'models':[{'name':'embed:latest', 'digest':digest[0]}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen', respond)
    p = OllamaProvider('http://local', 'embed', 'llm')
    assert p.embedding_revision() == 'sha256:one'
    digest[0] = 'sha256:two'
    assert p.embedding_revision() == 'sha256:two'


def test_unknown_model_revision_fails_closed(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **kw: _Resp(b'{"models":[]}'))
    with pytest.raises(ProviderFehler):
        OllamaProvider('http://local', 'missing', 'llm').embedding_revision()


def test_embed_disables_silent_truncation(monkeypatch):
    payloads = []
    def respond(req, timeout=0):
        payloads.append(json.loads(req.data))
        return _Resp(b'{"embeddings":[[1,2]]}')
    monkeypatch.setattr('urllib.request.urlopen', respond)
    OllamaProvider('http://local', 'embed', 'llm').embed(['synthetic text'])
    assert payloads[0]['truncate'] is False

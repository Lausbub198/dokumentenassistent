import io, json, pytest
from pathlib import Path
from dokumentenassistent import provider as p

class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False

def _fake_urlopen(antwort: dict, status=200):
    def f(req, timeout=0):
        if status != 200:
            raise p.urllib.error.HTTPError(req.full_url, status, "boom", {}, None)
        return _Resp(json.dumps(antwort).encode())
    return f

def test_M1_G1_embed_liefert_je_text_einen_vektor(monkeypatch):
    monkeypatch.setattr(p.urllib.request, "urlopen", _fake_urlopen({"embeddings": [[0.1, 0.2], [0.3, 0.4]]}))
    prov = p.OllamaProvider("http://x", "e", "l")
    assert prov.embed(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]

def test_M1_G2_generate_json_parst_response(monkeypatch):
    monkeypatch.setattr(p.urllib.request, "urlopen", _fake_urlopen({"response": '{"kategorie": "Wohnung Nord"}'}))
    prov = p.OllamaProvider("http://x", "e", "l")
    assert prov.generate_json("frage", {"type": "object"}) == {"kategorie": "Wohnung Nord"}

def test_M1_G3_generate_json_sendet_schema_als_format(monkeypatch):
    gesendet = {}
    def f(req, timeout=0):
        gesendet.update(json.loads(req.data)); return _Resp(b'{"response": "{}"}')
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    p.OllamaProvider("http://x", "e", "l").generate_json("x", {"type": "object"})
    assert gesendet["format"] == {"type": "object"}

def test_M1_G4_lade_modelle_liest_yaml(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: bge-m3\nllm: qwen3.5:9b\nthink: low\n")
    prov = p.lade_modelle(tmp_path / "modelle.yaml")
    assert (prov.host, prov.embed_modell, prov.llm_modell) == ("http://h", "bge-m3", "qwen3.5:9b")

def test_M1_B1_server_nicht_erreichbar_ergibt_providerfehler(monkeypatch):
    def f(req, timeout=0): raise ConnectionRefusedError()
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    with pytest.raises(p.ProviderFehler, match="nicht erreichbar"):
        p.OllamaProvider("http://x", "e", "l").embed(["a"])

def test_M1_B2_http_fehler_ergibt_providerfehler(monkeypatch):
    monkeypatch.setattr(p.urllib.request, "urlopen", _fake_urlopen({}, status=500))
    with pytest.raises(p.ProviderFehler, match="500"):
        p.OllamaProvider("http://x", "e", "l").generate_text("a")

def test_M1_B3_kein_json_in_response_ergibt_schemafehler(monkeypatch):
    monkeypatch.setattr(p.urllib.request, "urlopen", _fake_urlopen({"response": "Klar, hier: kategorie=Nord"}))
    with pytest.raises(p.SchemaFehler):
        p.OllamaProvider("http://x", "e", "l").generate_json("x", {"type": "object"})

def test_M1_B4_leere_textliste_ergibt_leere_liste_ohne_aufruf(monkeypatch):
    def f(req, timeout=0): raise AssertionError("darf nicht aufgerufen werden")
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    assert p.OllamaProvider("http://x", "e", "l").embed([]) == []

def test_M1_B5_yaml_ohne_llm_ergibt_providerfehler(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: bge-m3\n")
    with pytest.raises(p.ProviderFehler, match="llm"):
        p.lade_modelle(tmp_path / "modelle.yaml")


def test_M1_G5_kontext_wird_als_num_ctx_gesendet(monkeypatch):
    gesendet = {}
    def f(req, timeout=0):
        gesendet.update(json.loads(req.data)); return _Resp(b'{"response": "x"}')
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    p.OllamaProvider("http://x", "e", "l", kontext=16384).generate_text("a")
    assert gesendet["options"]["num_ctx"] == 16384


def test_M1_G6_ohne_kontext_kein_num_ctx(monkeypatch):
    gesendet = {}
    def f(req, timeout=0):
        gesendet.update(json.loads(req.data)); return _Resp(b'{"response": "x"}')
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    p.OllamaProvider("http://x", "e", "l").generate_text("a")
    assert "num_ctx" not in gesendet["options"]


def test_M1_G7_lade_modelle_liest_kontext(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: e\nllm: l\nkontext: 8192\n")
    assert p.lade_modelle(tmp_path / "modelle.yaml").kontext == 8192


def test_M1_G7b_lade_modelle_liest_timeout(tmp_path):
    """Anlass 24.09.2026: Der Produktpfad lief mit dem Standard 120 s, waehrend ein gemessener
    Profilaufruf 245 s brauchte (beweise/last/2026-09-24/, unter Last). Der Lauf ueber echte
    Dokumente brach deshalb mit ProviderFehler ab. Der Messpfad (lasttest.py) setzte laengst 900 s.
    """
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: e\nllm: l\ntimeout: 900\n")
    assert p.lade_modelle(tmp_path / "modelle.yaml").timeout == 900


def test_M1_G7c_lade_modelle_ohne_timeout_behaelt_standard(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: e\nllm: l\n")
    assert p.lade_modelle(tmp_path / "modelle.yaml").timeout == 120


def test_M1_G7d_lade_provider_suche_erbt_timeout(tmp_path):
    (tmp_path / "modelle.yaml").write_text(
        "host: http://h\nembedding: e\nllm: l\nllm_suche: s\ntimeout: 600\n")
    assert p.lade_provider_suche(tmp_path / "modelle.yaml").timeout == 600


def test_M1_G8_lade_provider_suche_fehlt_ergibt_none(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: e\nllm: l\n")
    assert p.lade_provider_suche(tmp_path / "modelle.yaml") is None


def test_M1_G9_lade_provider_suche_gleich_llm_ergibt_none(tmp_path):
    (tmp_path / "modelle.yaml").write_text("host: http://h\nembedding: e\nllm: l\nllm_suche: l\n")
    assert p.lade_provider_suche(tmp_path / "modelle.yaml") is None


def test_M1_G10_lade_provider_suche_verschieden_liefert_provider(tmp_path):
    (tmp_path / "modelle.yaml").write_text(
        "host: http://h\nembedding: e\nllm: l\nllm_suche: s\nthink: low\nkontext: 8192\n"
    )
    prov = p.lade_provider_suche(tmp_path / "modelle.yaml")
    assert prov is not None
    assert (prov.host, prov.embed_modell, prov.llm_modell, prov.think, prov.kontext) == (
        "http://h", "e", "s", "low", 8192,
    )


# --------------------------------------------------------- Sucheinstellungen (R12)
# sentence-transformers wird in den Tests nie geladen: entweder fehlt der Schlüssel
# `reranker`, oder `CrossEncoderReranker` ist durch einen Fake ersetzt.

_BASIS = "host: http://h\nembedding: e\nllm: l\n"


def test_M1_G11_sucheinstellungen_ohne_schluessel_sind_das_heutige_verhalten(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS)
    e = p.lade_sucheinstellungen(tmp_path / "modelle.yaml")
    assert (e.reranker, e.rerank_k, e.top_n) == (None, 20, 8)


def test_chunking_einstellung_liest_seitenuebergreifend_strikt(tmp_path):
    konfig = tmp_path / 'modelle.yaml'
    konfig.write_text(_BASIS + 'seitenuebergreifend: true\n')
    assert p.lade_seitenuebergreifend(konfig) is True
    konfig.write_text(_BASIS + 'seitenuebergreifend: false\n')
    assert p.lade_seitenuebergreifend(konfig) is False
    konfig.write_text(_BASIS)
    assert p.lade_seitenuebergreifend(konfig) is False
    konfig.write_text(_BASIS + 'seitenuebergreifend: "true"\n')
    with pytest.raises(p.ProviderFehler, match='seitenuebergreifend'):
        p.lade_seitenuebergreifend(konfig)
    konfig.write_text(_BASIS + 'seitenuebergreifend: [\n')
    with pytest.raises(p.ProviderFehler, match='modelle.yaml'):
        p.lade_seitenuebergreifend(konfig)


def test_M1_G12_sucheinstellungen_lesen_reranker_rerank_k_top_n(tmp_path, monkeypatch):
    gebaut = {}

    class FakeCrossEncoder:
        def __init__(self, modell, geraet=None):
            gebaut.update(modell=modell, geraet=geraet)

        def bewerte(self, frage, texte):
            return [0.0] * len(texte)

    monkeypatch.setattr(p, "CrossEncoderReranker", FakeCrossEncoder)
    (tmp_path / "modelle.yaml").write_text(
        _BASIS + "reranker: BAAI/bge-reranker-v2-m3\nrerank_k: 30\nrerank_geraet: mps\ntop_n: 12\n"
    )
    e = p.lade_sucheinstellungen(tmp_path / "modelle.yaml")
    assert (type(e.reranker), e.rerank_k, e.top_n) == (FakeCrossEncoder, 30, 12)
    assert gebaut == {"modell": "BAAI/bge-reranker-v2-m3", "geraet": "mps"}


def test_M1_G13_sucheinstellungen_geraet_weggelassen_bedeutet_automatisch(tmp_path, monkeypatch):
    gebaut = {}

    class FakeCrossEncoder:
        def __init__(self, modell, geraet=None):
            gebaut.update(modell=modell, geraet=geraet)

    monkeypatch.setattr(p, "CrossEncoderReranker", FakeCrossEncoder)
    (tmp_path / "modelle.yaml").write_text(_BASIS + "reranker: BAAI/bge-reranker-v2-m3\n")
    p.lade_sucheinstellungen(tmp_path / "modelle.yaml")
    assert gebaut["geraet"] is None  # None -> CrossEncoderReranker wählt mps/cpu selbst


# ----------------------------------------------- abnahme_protokoll (23.09.2026, Anlass R13)


def test_M1_G14_abnahme_protokoll_ohne_schluessel_ist_knapp(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS)
    assert p.lade_abnahme_protokoll(tmp_path / "modelle.yaml") == "knapp"


def test_M1_G15_abnahme_protokoll_liest_knapp_explizit(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS + "abnahme_protokoll: knapp\n")
    assert p.lade_abnahme_protokoll(tmp_path / "modelle.yaml") == "knapp"


def test_M1_G16_abnahme_protokoll_liest_voll(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS + "abnahme_protokoll: voll\n")
    assert p.lade_abnahme_protokoll(tmp_path / "modelle.yaml") == "voll"


def test_M1_B6_abnahme_protokoll_unbekannter_wert_ergibt_providerfehler(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS + "abnahme_protokoll: halb\n")
    with pytest.raises(p.ProviderFehler, match="abnahme_protokoll"):
        p.lade_abnahme_protokoll(tmp_path / "modelle.yaml")


def test_M1_B7_abnahme_protokoll_datei_fehlt_ergibt_providerfehler(tmp_path):
    with pytest.raises(p.ProviderFehler, match="nicht gefunden"):
        p.lade_abnahme_protokoll(tmp_path / "modelle.yaml")


def test_M1_B2_reranker_gesetzt_aber_extra_fehlt_wirft_beim_start(tmp_path, monkeypatch):
    """Kein stiller Verzicht: fehlt sentence-transformers, bricht das Laden der Einstellungen ab."""
    import builtins

    echter_import = builtins.__import__

    def gesperrter_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("No module named 'sentence_transformers'")
        return echter_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", gesperrter_import)
    (tmp_path / "modelle.yaml").write_text(_BASIS + "reranker: BAAI/bge-reranker-v2-m3\n")
    with pytest.raises(p.RerankerFehler) as exc:
        p.lade_sucheinstellungen(tmp_path / "modelle.yaml")
    assert "uv sync --extra reranker" in str(exc.value)


# ------------------------------------------------------- OCR-Engine (24.09.2026, Anlass R14)
#
# `paddleocr` wird hier NICHT installiert vorausgesetzt und NICHT importiert: geprüft wird die
# Verfügbarkeitsprobe `auslesen.paddleocr_vorhanden`, nicht das Paket.


def _paddle_da(monkeypatch, vorhanden: bool) -> None:
    from dokumentenassistent import auslesen

    monkeypatch.setattr(auslesen, "paddleocr_vorhanden", lambda: vorhanden)


def test_M1_G17_ocr_ohne_schluessel_ist_paddleocr_mit_drehung(tmp_path, monkeypatch):
    _paddle_da(monkeypatch, True)
    (tmp_path / "modelle.yaml").write_text(_BASIS)
    e = p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")
    assert (e.engine, e.drehung, e.sprache, e.schwelle) == ("paddleocr", True, "german", 0.80)


def test_M1_G18_ocr_tesseract_bekommt_die_tesseract_standardwerte(tmp_path):
    """Ein gemeinsamer Standard wäre für eine der beiden Engines falsch."""
    (tmp_path / "modelle.yaml").write_text(_BASIS + "ocr: tesseract\n")
    e = p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")
    assert (e.engine, e.sprache, e.schwelle) == ("tesseract", "deu", 0.6)


def test_M1_G19_ocr_schluessel_werden_einzeln_gelesen(tmp_path, monkeypatch):
    _paddle_da(monkeypatch, True)
    (tmp_path / "modelle.yaml").write_text(
        _BASIS + "ocr: paddleocr\nocr_drehung: false\nocr_sprache: en\nocr_schwelle: 0.95\n"
    )
    e = p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")
    assert (e.engine, e.drehung, e.sprache, e.schwelle) == ("paddleocr", False, "en", 0.95)


def test_M1_B8_ocr_unbekannte_engine_ergibt_providerfehler(tmp_path):
    (tmp_path / "modelle.yaml").write_text(_BASIS + "ocr: surya\n")
    with pytest.raises(p.ProviderFehler, match="ocr"):
        p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")


def test_M1_B9_paddleocr_gewaehlt_aber_extra_fehlt_wirft_beim_start(tmp_path, monkeypatch):
    """Kein stiller Rückfall auf Tesseract — das wäre eine andere Messlage als die eingestellte."""
    _paddle_da(monkeypatch, False)
    (tmp_path / "modelle.yaml").write_text(_BASIS + "ocr: paddleocr\n")
    with pytest.raises(p.OcrNichtVerfuegbar) as exc:
        p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")
    assert "uv sync --extra ocr-paddle" in str(exc.value)


def test_M1_B10_ocr_datei_fehlt_ergibt_providerfehler(tmp_path):
    with pytest.raises(p.ProviderFehler, match="nicht gefunden"):
        p.lade_ocr_einstellungen(tmp_path / "modelle.yaml")


def test_M1_G20_mitgelieferte_modelle_yaml_ist_lesbar(monkeypatch):
    """Die ausgelieferte Datei muss zu diesem Leser passen — sonst startet das Produkt nicht."""
    _paddle_da(monkeypatch, True)
    e = p.lade_ocr_einstellungen(Path("modelle.yaml"))
    assert (e.engine, e.drehung) == ("paddleocr", True)

def test_M1_G5_antwortgrenze_nur_fuer_freitext(monkeypatch, tmp_path):
    gesendet = []
    def f(req, timeout=0):
        gesendet.append(json.loads(req.data)); return _Resp(b'{"response": "{}"}')
    monkeypatch.setattr(p.urllib.request, "urlopen", f)
    prov = p.OllamaProvider("http://x", "e", "l", max_antwort_tokens=1024)
    prov.generate_text("frage")
    prov.generate_json("x", {"type": "object"})
    assert gesendet[0]["options"]["num_predict"] == 1024
    assert "num_predict" not in gesendet[1]["options"]
    yaml_pfad = tmp_path / "m.yaml"
    yaml_pfad.write_text("host: http://x\nembedding: e\nllm: l\nmax_antwort_tokens: 512\n")
    assert p.lade_modelle(yaml_pfad).max_antwort_tokens == 512
    assert p.OllamaProvider("http://x", "e", "l").max_antwort_tokens is None

def test_M1_G6_sucheinstellungen_kaskade_aus_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "CrossEncoderReranker", lambda modell, geraet=None: object())
    y = tmp_path / "m.yaml"
    y.write_text("reranker: x\nkontextauswahl: dynamisch\nkaskade: true\nkaskade_stufe2: pruefung\nschwelle: 0\n")
    e = p.lade_sucheinstellungen(y)
    assert (e.kontextauswahl, e.kaskade, e.kaskade_stufe2, e.schwelle) == ("dynamisch", True, "pruefung", 0.0)
    y.write_text("top_n: 5\n")
    e = p.lade_sucheinstellungen(y)
    assert (e.kontextauswahl, e.kaskade, e.kaskade_stufe2, e.schwelle) == ("fest", False, "keine", None)
    y.write_text("kontextauswahl: dynamisch\n")
    with pytest.raises(p.ProviderFehler, match="reranker"):
        p.lade_sucheinstellungen(y)
    y.write_text("reranker: x\nkaskade_stufe2: vielleicht\n")
    with pytest.raises(p.ProviderFehler, match="unbekannt"):
        p.lade_sucheinstellungen(y)

def test_M1_G7_kontext_praefix_aus_yaml(tmp_path):
    y = tmp_path / "m.yaml"
    y.write_text("kontext_praefix: pfad\n")
    assert p.lade_sucheinstellungen(y).kontext_praefix == "pfad"
    y.write_text("top_n: 5\n")
    assert p.lade_sucheinstellungen(y).kontext_praefix == "keiner"
    y.write_text("kontext_praefix: ordner\n")
    with pytest.raises(p.ProviderFehler, match="kontext_praefix"):
        p.lade_sucheinstellungen(y)

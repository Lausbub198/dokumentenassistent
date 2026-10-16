"""R11: Reranker als Eval-Variante (M4) — nur mit FakeReranker, kein sentence-transformers-Import."""
from __future__ import annotations

from dokumentenassistent.retrieval_reranker import CrossEncoderReranker, RerankerFehler, kurzname, rerank
from tests.conftest import fs


class FakeReranker:
    """Deterministischer Ersatz für den Cross-Encoder: Score je Text aus einer vorbereiteten Map."""

    def __init__(self, score_je_text: dict[str, float]):
        self.score_je_text = score_je_text
        self.aufrufe: list[tuple[str, list[str]]] = []

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        self.aufrufe.append((frage, texte))
        return [self.score_je_text[t] for t in texte]


FUNDSTELLEN = {
    "a": fs("a", "Text A", datei="a.pdf"),
    "b": fs("b", "Text B", datei="b.pdf"),
    "c": fs("c", "Text C", datei="c.pdf"),
    "d": fs("d", "Text D", datei="d.pdf"),
}


def test_R11_rerank_sortiert_top_k_nach_reranker_score():
    dense = (("a", 0.9), ("b", 0.8), ("c", 0.5))
    # Dense hat a > b > c; der Reranker sieht es umgekehrt -> c muss vorne landen.
    reranker = FakeReranker({"Text A": 0.1, "Text B": 0.5, "Text C": 0.9})
    ergebnis = rerank(dense, FUNDSTELLEN, "Frage", reranker, top_k=3)
    assert [id_ for id_, _ in ergebnis] == ["c", "b", "a"]
    assert reranker.aufrufe == [("Frage", ["Text A", "Text B", "Text C"])]


def test_R11_rerank_top_k_grenze_nur_kopf_wird_neu_sortiert():
    dense = (("a", 0.9), ("b", 0.8), ("c", 0.7), ("d", 0.6))
    reranker = FakeReranker({"Text A": 0.1, "Text B": 0.9})
    ergebnis = rerank(dense, FUNDSTELLEN, "Frage", reranker, top_k=2)
    # Kopf (a, b) neu sortiert -> b vor a; Rest (c, d) unverändert, inkl. der alten Scores.
    assert ergebnis == (("b", 0.9), ("a", 0.1), ("c", 0.7), ("d", 0.6))


def test_R11_rerank_rest_bleibt_unveraendert_auch_bei_top_k_1():
    dense = (("a", 0.9), ("b", 0.8), ("c", 0.7))
    reranker = FakeReranker({"Text A": 0.42})
    ergebnis = rerank(dense, FUNDSTELLEN, "Frage", reranker, top_k=1)
    assert ergebnis[1:] == (("b", 0.8), ("c", 0.7))
    assert reranker.aufrufe == [("Frage", ["Text A"])]


def test_R11_rerank_leere_rangliste_gibt_leer_ohne_reranker_aufruf():
    reranker = FakeReranker({})
    assert rerank((), FUNDSTELLEN, "Frage", reranker, top_k=8) == ()
    assert reranker.aufrufe == []


def test_R11_rerank_top_k_null_oder_negativ_gibt_unveraendert():
    dense = (("a", 0.9), ("b", 0.8))
    reranker = FakeReranker({})
    assert rerank(dense, FUNDSTELLEN, "Frage", reranker, top_k=0) == dense
    assert rerank(dense, FUNDSTELLEN, "Frage", reranker, top_k=-1) == dense
    assert reranker.aufrufe == []


def test_R11_kurzname_nimmt_letztes_pfadsegment_lowercase():
    assert kurzname("BAAI/bge-reranker-v2-m3") == "bge-reranker-v2-m3"
    assert kurzname("Qwen/Qwen3-Reranker-0.6B") == "qwen3-reranker-0.6b"
    assert kurzname("ohne-slash") == "ohne-slash"


def test_R11_cross_encoder_reranker_ohne_extra_wirft_klaren_fehler(monkeypatch):
    import builtins

    echter_import = builtins.__import__

    def gesperrter_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("No module named 'sentence_transformers'")
        return echter_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", gesperrter_import)
    try:
        CrossEncoderReranker("BAAI/bge-reranker-v2-m3")
        raise AssertionError("hätte RerankerFehler werfen müssen")
    except RerankerFehler as exc:
        assert "sentence-transformers" in str(exc)
        assert "uv sync --extra reranker" in str(exc)

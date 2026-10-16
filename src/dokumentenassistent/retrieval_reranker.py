"""Reranker (M4, docs/retrieval-massnahmen-2026-09-21.md). Seit 23.09.2026 nicht mehr nur
Eval-Variante: `suche.py` kann `rerank()` optional im Produktpfad aufrufen (Parameter `reranker`),
abgeschaltet per Standard. `retrieval_eval.py` misst weiterhin damit.

Hypothese war: dense@qwen3-embedding erreicht Recall@8 93 % aber Rang 1 nur 79 % (drei Fragen liegen
auf Rang 6–13, siehe docs/retrieval-befund-2026-09-21.md). Ein Cross-Encoder liest Frage und Absatz
gemeinsam (statt zwei getrennte Embeddings per Kosinus zu vergleichen) und ordnet die Top-k der
dense-Liste feiner. Gemessen bestätigt, und zwar auf beiden Korpora: malerbetrieb Stufe 200 R@1
79 -> 93 / R@8 93 -> 100 (BAAI/bge-reranker-v2-m3, k=20), GermanQuAD (474 Absätze, 60 menschliche
Fragen) dense@bge-m3 R@1 88 -> 98 / R@8 97 -> 100. Kosten 0,5 s/Frage auf MPS (kurze
Geschäftsabsätze), 3–10 s/Frage auf CPU (lange Wikipedia-Absätze).

`Reranker` ist ein Protocol statt einer Basisklasse: zwei Implementierungen existieren bereits
(`CrossEncoderReranker` hier, ein Fake in den Tests) — kein ABC ohne zweiten konkreten Fall.
"""
from __future__ import annotations

from typing import Protocol

from dokumentenassistent.suche import Rangliste
from dokumentenassistent.typen import DokumentenassistentFehler, Fundstelle


class Reranker(Protocol):
    def bewerte(self, frage: str, texte: list[str]) -> list[float]: ...


class RerankerFehler(DokumentenassistentFehler):
    """sentence-transformers fehlt (Extra nicht installiert) oder das Modell lässt sich nicht laden."""


def _geraet() -> str:
    """`mps` auf Apple Silicon, wenn verfügbar, sonst `cpu`. Kein Extra installiert -> `cpu`
    (torch fehlt dann ebenfalls, aber diese Funktion wird nur nach erfolgreichem Import gerufen)."""
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def kurzname(modell: str) -> str:
    """`BAAI/bge-reranker-v2-m3` -> `bge-reranker-v2-m3`, für Varianten-Namen im Eval."""
    return modell.rsplit("/", 1)[-1].lower()


class CrossEncoderReranker:
    """Lazy-Import von `sentence_transformers.CrossEncoder` — geladen wird erst bei Konstruktion,
    nicht beim Import dieses Moduls, damit `uv run pytest` ohne das Extra grün bleibt."""

    def __init__(self, modell: str, geraet: str | None = None):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RerankerFehler(
                f"sentence-transformers fehlt für Reranker '{modell}' — "
                "`uv sync --extra reranker` ausführen."
            ) from exc
        self.modell_name = modell
        self.geraet = geraet or _geraet()
        self._modell = CrossEncoder(modell, device=self.geraet)

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        if not texte:
            return []
        scores = self._modell.predict([(frage, text) for text in texte])
        return [float(s) for s in scores]


def rerank(
    rangliste_dense: Rangliste,
    fundstellen_je_id: dict[str, Fundstelle],
    frage: str,
    reranker: Reranker,
    top_k: int,
) -> Rangliste:
    """Top-k der dense-Rangliste per Cross-Encoder-Score neu sortieren, Rest unverändert dahinter.

    Leere Rangliste oder `top_k <= 0` -> Rangliste unverändert zurück (kein Reranker-Aufruf)."""
    if not rangliste_dense or top_k <= 0:
        return rangliste_dense
    kopf, rest = rangliste_dense[:top_k], rangliste_dense[top_k:]
    texte = [fundstellen_je_id[id_].text for id_, _ in kopf]
    scores = reranker.bewerte(frage, texte)
    neu_sortiert = sorted(zip((id_ for id_, _ in kopf), scores), key=lambda p: -p[1])
    return tuple(neu_sortiert) + rest

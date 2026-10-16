"""Retriever-Varianten, die nur im Eval gemessen werden (M1/M3 aus
`docs/retrieval-massnahmen-2026-09-21.md`). `suche.py` bleibt unverändert; hier wird
`bm25_rang`/`_bm25_scores` nur mit anders vorbereiteten Tokens aufgerufen.

- `rrf_gewichtet`: RRF mit Gewicht je Liste (w/(k+Rang)); w=1 für alle = `suche.rrf`.
- `bm25_komposita`: Frage-Tokens ≥ 8 Zeichen werden in zwei Vokabular-Tokens zerlegt
  (optional Fuge s/n/en), die Teile kommen als zusätzliche Frage-Tokens dazu.
- `bm25_praefix`: Dokument-Token trifft Frage-Token, wenn eines Präfix des anderen ist
  (beide ≥ 5 Zeichen); Dokument-Tokens werden auf das Frage-Token abgebildet.
"""
from __future__ import annotations

from collections.abc import Callable

from dokumentenassistent.suche import Rangliste, _bm25_scores, _tokens, bm25_rang
from dokumentenassistent.typen import Fundstelle

MIN_VOKABEL = 4
MIN_KOMPOSITUM = 8
MIN_PRAEFIX = 5
FUGEN = ("", "s", "n", "en")

Vokabular = frozenset[str]
LexikalischeVariante = Callable[[str, tuple[Fundstelle, ...], Vokabular], Rangliste]


# --------------------------------------------------------------------- RRF


def rrf_gewichtet(listen_mit_gewicht: tuple[tuple[Rangliste, float], ...], k: int = 60) -> Rangliste:
    """Reciprocal Rank Fusion mit Gewicht je Liste: Summe von w/(k+Rang)."""
    punkte: dict[str, float] = {}
    for liste, gewicht in listen_mit_gewicht:
        for rang, (id_, _score) in enumerate(liste, start=1):
            punkte[id_] = punkte.get(id_, 0.0) + gewicht / (k + rang)
    return tuple(sorted(punkte.items(), key=lambda p: -p[1]))


# --------------------------------------------------------------- Komposita


def vokabular_der_fundstellen(fundstellen: tuple[Fundstelle, ...]) -> Vokabular:
    """Alle Dokument-Tokens mit ≥ 4 Zeichen."""
    return frozenset(t for f in fundstellen for t in _tokens(f.text) if len(t) >= MIN_VOKABEL)


def zerlege_komposita(token: str, vokabular: Vokabular) -> tuple[str, ...]:
    """Lückenlose Zerlegung in genau zwei Vokabular-Tokens, optional mit Fuge dazwischen
    (rechnungsnummer → rechnung, nummer). Kein Treffer oder Token < 8 Zeichen → leer."""
    if len(token) < MIN_KOMPOSITUM:
        return ()
    for schnitt in range(MIN_VOKABEL, len(token) - MIN_VOKABEL + 1):
        links, rest = token[:schnitt], token[schnitt:]
        if links not in vokabular:
            continue
        for fuge in FUGEN:
            rechts = rest[len(fuge):]
            if rest.startswith(fuge) and len(rechts) >= MIN_VOKABEL and rechts in vokabular:
                return (links, rechts)
    return ()


def erweitere_frage(frage: str, vokabular: Vokabular) -> str:
    """Frage plus alle gefundenen Teilwörter als Text — `bm25_rang` nimmt einen Frage-String."""
    teile = [teil for token in _tokens(frage) for teil in zerlege_komposita(token, vokabular)]
    return f"{frage} {' '.join(teile)}" if teile else frage


def bm25_komposita_rang(frage: str, fundstellen: tuple[Fundstelle, ...], vokabular: Vokabular) -> Rangliste:
    return bm25_rang(erweitere_frage(frage, vokabular), fundstellen)


# ------------------------------------------------------------------ Präfix


def _praefix_treffer(dokument_token: str, frage_tokens: list[str]) -> str:
    """Das erste Frage-Token, das Präfix des Dokument-Tokens ist oder umgekehrt (beide ≥ 5),
    sonst das Dokument-Token selbst."""
    if len(dokument_token) < MIN_PRAEFIX:
        return dokument_token
    for q in frage_tokens:
        if len(q) >= MIN_PRAEFIX and (dokument_token.startswith(q) or q.startswith(dokument_token)):
            return q
    return dokument_token


def bm25_praefix_rang(frage: str, fundstellen: tuple[Fundstelle, ...], _vokabular: Vokabular) -> Rangliste:
    """Dokument-Tokens je Absatz auf das passende Frage-Token abbilden, dann BM25 darüber."""
    frage_tokens = _tokens(frage)
    if not frage_tokens or not fundstellen:
        return ()
    korpus = [[_praefix_treffer(t, frage_tokens) for t in _tokens(f.text)] for f in fundstellen]
    scores = _bm25_scores(frage_tokens, korpus)
    treffer = [(f.id, s) for f, s in zip(fundstellen, scores) if s > 0.0]
    return tuple(sorted(treffer, key=lambda p: -p[1]))


def _bm25_unveraendert(frage: str, fundstellen: tuple[Fundstelle, ...], _vokabular: Vokabular) -> Rangliste:
    return bm25_rang(frage, fundstellen)


# ------------------------------------------------------------- Variantenliste

LEXIKALISCHE_VARIANTEN: dict[str, LexikalischeVariante] = {
    "bm25": _bm25_unveraendert,
    "bm25_komposita": bm25_komposita_rang,
    "bm25_praefix": bm25_praefix_rang,
}

# Name → (lexikalische Liste, Gewicht der lexikalischen Liste); dense immer Gewicht 1.0.
# w=1.0 mit bm25 ist das heutige `hybrid`; w=0 wäre `dense` und wird nicht gedoppelt.
HYBRID_VARIANTEN: dict[str, tuple[str, float]] = {
    "hybrid": ("bm25", 1.0),
    "hybrid_w0.5": ("bm25", 0.5),
    "hybrid_w0.25": ("bm25", 0.25),
    "hybrid_komposita_w1.0": ("bm25_komposita", 1.0),
    "hybrid_komposita_w0.5": ("bm25_komposita", 0.5),
}

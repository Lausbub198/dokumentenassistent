"""Bounded optional follow-up search; callers retain the original citation gate."""
from __future__ import annotations

import re
import time
from collections.abc import Callable

from dokumentenassistent.typen import Antwort

Suchlauf = Callable[[str, str | None, float | None], Antwort]
Umformulieren = Callable[[str, tuple[str, ...], float], str | None]
_MAX_NACHFRAGEN = 2


def _normalisiere(text: str) -> str:
    return " ".join(text.split()).casefold()


def _belegt(antwort: Antwort) -> bool:
    return antwort.status in {"gefunden", "widerspruechlich"} and bool(antwort.karten)


def iterativ_suchen(
    frage: str,
    suchen: Suchlauf,
    umformulieren: Umformulieren,
    *,
    max_nachfragen: int = _MAX_NACHFRAGEN,
    zeitbudget_s: float = 60.0,
    max_suchtext_zeichen: int = 250,
    monotonic: Callable[[], float] = time.monotonic,
) -> Antwort:
    """Start with normal RAG; retry only an ungrounded `nicht_gefunden` answer.

    Follow-up callbacks receive the remaining time budget. They must pass that bound
    through to their model/provider calls. Candidate/reranker limits remain the
    caller's fixed, ordinary search configuration. The orchestration starts at most
    two additional rounds and never treats response text alone as a citation.
    """
    if max_nachfragen < 0 or max_nachfragen > _MAX_NACHFRAGEN:
        raise ValueError("Maximal zwei Nachfragen erlaubt")
    if zeitbudget_s <= 0 or max_suchtext_zeichen <= 0:
        raise ValueError("Zeitbudget und Suchtextlimit müssen positiv sein")

    initial = suchen(frage, None, None)
    if _belegt(initial) or initial.status != "nicht_gefunden" or initial.karten:
        return initial

    letzte_antwort = initial
    start = monotonic()
    bisherige = [frage]
    gesehen = {_normalisiere(frage)}
    for _ in range(max_nachfragen):
        rest_s = zeitbudget_s - (monotonic() - start)
        if rest_s <= 0:
            break
        try:
            suchtext = umformulieren(frage, tuple(bisherige), rest_s)
        except TimeoutError:
            break
        if monotonic() - start >= zeitbudget_s or not isinstance(suchtext, str):
            break
        suchtext = re.sub(r"\s+", " ", suchtext).strip()
        normalisiert = _normalisiere(suchtext)
        if not normalisiert or len(suchtext) > max_suchtext_zeichen or normalisiert in gesehen:
            break
        gesehen.add(normalisiert)
        bisherige.append(suchtext)

        rest_s = zeitbudget_s - (monotonic() - start)
        if rest_s <= 0:
            break
        try:
            antwort = suchen(frage, suchtext, rest_s)
        except TimeoutError:
            break
        if _belegt(antwort):
            return antwort
        if antwort.status != "nicht_gefunden" or antwort.karten:
            break
        letzte_antwort = antwort

    return letzte_antwort

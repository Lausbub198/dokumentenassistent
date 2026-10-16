"""Sprachprüfung ohne Modell (10.10.2026).

Die Antwortsprache steht zentral in `modelle.yaml` (`sprache:`) und geht als System-Anweisung
in jeden Modellaufruf (provider.py). Ob das Modell sich daran gehalten hat, prüft diese Regel —
wie die Zitatprüfung: das Modell schlägt vor, eine feste Regel prüft. Anlass: qwen3:4b schrieb
seine englischen Denkschritte in den Antworttext, obwohl der Prompt Deutsch verlangte.

Geprüft wird nur Deutsch gegen Englisch, über häufige Funktionswörter. Für jede andere
eingestellte Sprache gilt die Antwort als passend (keine Regel, also keine Behauptung).
"""

import re

_WORT = re.compile(r"[a-zäöüß]+")
# Fundstellen-Kennungen ([D…#S1#A1#T…]) und alles mit Ziffern zuerst entfernen: Hex-Hashes zerfielen sonst
# in „a“, „be“, „d“ und zählten als Englisch (Fehlalarm auf einer deutschen Antwort, 10.10.2026).
_KENNUNG = re.compile(r"\[[^\]]*\]|\([^)]*#[^)]*\)|\S*\d\S*")
_DEUTSCH = frozenset("der die das und ist nicht ein eine im in den dem des mit auf für von zu es sich als auch wird wurde nach bei".split())
# Nur Wörter, die es im Deutschen nicht gibt (also nicht „an“, „in“, „so“).
_ENGLISCH = frozenset("the and is not of to it that this for with are was be by from user let's which there".split())


def passt_zur_sprache(text: str, sprache: str) -> bool:
    """False nur, wenn klar mehr englische als deutsche Funktionswörter im Text stehen."""
    if sprache.strip().lower() != "deutsch":
        return True
    woerter = _WORT.findall(_KENNUNG.sub(" ", text).lower())
    deutsch = sum(w in _DEUTSCH for w in woerter)
    englisch = sum(w in _ENGLISCH for w in woerter)
    return not (englisch >= 5 and englisch > deutsch)

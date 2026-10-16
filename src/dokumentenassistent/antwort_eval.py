"""Offline reference metrics. Never imported by productive retrieval or gating."""
import unicodedata

from dokumentenassistent.typen import Antwort


def normalisiere_whitespace(text: str) -> str:
    """NFC + whitespace only. Preserve punctuation, signs, case and negation."""
    return ' '.join(unicodedata.normalize('NFC', text).split())


def bewerte_antwort(antwort: Antwort, zieldatei: str, sollwortlaut: str) -> dict:
    """Substring metrics are evidence-location proxies, NOT entailment judgments."""
    target = unicodedata.normalize('NFC', zieldatei)
    cards = [k for k in antwort.karten
             if unicodedata.normalize('NFC', k.fundstelle.datei_name) == target]
    return {
        'quellen_id_gueltig': bool(antwort.karten),
        'zieldatei_getroffen': bool(cards),
        'beleg_exakt': bool(sollwortlaut) and any(sollwortlaut in k.wortlaut for k in cards),
        'beleg_whitespace': bool(normalisiere_whitespace(sollwortlaut)) and any(
            normalisiere_whitespace(sollwortlaut) in normalisiere_whitespace(k.wortlaut)
            for k in cards),
        'antwort_enthaelt_exakt': bool(sollwortlaut) and sollwortlaut in antwort.text,
        'antwortstuetzung': antwort.stuetzung.status,
        'pruefverfahren': antwort.stuetzung.verfahren,
    }

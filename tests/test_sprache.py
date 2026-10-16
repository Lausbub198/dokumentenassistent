"""Sprachprüfung ohne Modell und zentrale Sprachanweisung (10.10.2026)."""

from dokumentenassistent.provider import OllamaProvider
from dokumentenassistent.sprache import passt_zur_sprache


def test_deutsche_antwort_passt():
    assert passt_zur_sprache("Die Fassadenfarbe hat laut der korrigierten Rechnung 1.170,25 EUR gekostet [1].", "Deutsch")


def test_englisches_denken_faellt_auf():
    text = ("Okay, let's tackle this question. The user is asking what is stated in the purchase "
            "agreement for the excavator. But wait, the provided text is a construction contract.")
    assert not passt_zur_sprache(text, "Deutsch")


def test_kurze_antwort_mit_englischem_fachwort_bleibt_deutsch():
    assert passt_zur_sprache("Das steht im Service Level Agreement auf Seite 2 [1].", "Deutsch")


def test_andere_sprache_wird_nicht_beurteilt():
    assert passt_zur_sprache("The answer is in the contract.", "Englisch")


def test_system_anweisung_kommt_aus_der_einstellung():
    p = OllamaProvider(host="http://x", embed_modell="e", llm_modell="l", sprache="Englisch")
    assert p.system_anweisung() == "Antworte ausschließlich auf Englisch."


def test_deutsche_antwort_mit_kennungen_ist_kein_fehlalarm():
    # Echter Fall 10.10.2026: die Hex-Kennung zerfiel in „a“-Tokens und löste den Hinweis aus.
    text = ("Die Kosten für die Fassade an der Ringstraße sind nicht eindeutig "
            "[D7686bfb19991074d5df0670b4a823955d8d97b349e4b4cb169e0d3b8777ea59a#S1#A1#T17d76cd7f089373c1caf]. "
            "1. Fassadenfarbe: 1.170,25 EUR 2. Fassadengerüst: 3.998,40 EUR")
    assert passt_zur_sprache(text, "Deutsch")

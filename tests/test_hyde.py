"""HyDE: Hypothese bauen, Rückfall auf die Frage, Zusammensetzung des Suchtexts."""
from __future__ import annotations

from dokumentenassistent.hyde import ANWEISUNG, hypothese, suchtext
from tests.conftest import FakeProvider

FRAGE = "Was sollte ich dem Notar für die Grundschuld überweisen?"
ERFUNDEN = "Ich bitte um Begleichung des Rechnungsbetrages von 1.002,41 EUR."


def test_H1_hypothese_bekommt_die_frage_in_die_anweisung():
    p = FakeProvider(text_antworten=[ERFUNDEN])
    assert hypothese(FRAGE, p) == ERFUNDEN
    prompt = p.aufrufe[0][1]
    assert FRAGE in prompt
    assert "Dokumenttext:" in prompt


def test_H2_leere_modellantwort_faellt_auf_die_frage_zurueck():
    """Ein Modell, das nichts liefert, darf die Suche nicht auf einen leeren Vektor
    schicken — dann wird eben wie bisher mit der Frage gesucht."""
    assert hypothese(FRAGE, FakeProvider(text_antworten=["   "])) == FRAGE


def test_H3_suchtext_haengt_die_frage_an_die_hypothese():
    p = FakeProvider(text_antworten=[ERFUNDEN])
    t = suchtext(FRAGE, p)
    assert t.startswith(ERFUNDEN)
    assert t.endswith(FRAGE)


def test_H4_ohne_frage_bleibt_nur_die_hypothese():
    p = FakeProvider(text_antworten=[ERFUNDEN])
    assert suchtext(FRAGE, p, mit_frage=False) == ERFUNDEN


def test_H5_anweisung_verlangt_dokumentstil_nicht_antwortstil():
    """Der Unterschied ist der ganze Trick: der Text soll dem Zielabsatz aehneln,
    nicht einer Antwort auf die Frage."""
    assert "im Stil des Dokuments" in ANWEISUNG
    assert "Erfinde konkrete Werte" in ANWEISUNG

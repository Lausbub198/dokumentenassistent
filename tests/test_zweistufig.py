"""Zweistufiges Antworten, Schritt 1: Auswahl. Ohne Modell."""
from __future__ import annotations

from dokumentenassistent.zweistufig import AUSWAHL, waehle
from dokumentenassistent.suche import suche
from tests.conftest import FakeProvider, fs

A = fs("R.pdf#S1#A1", "Rechnungsbetrag 1.002,41 EUR", datei="R.pdf")
B = fs("R.pdf#S1#A2", "Zahlbar bis 20.06.2025", datei="R.pdf", absatz=2)
C = fs("M.pdf#S1#A1", "Kaltmiete 780,00 EUR", datei="M.pdf")
SET = (A, B, C)
FRAGE = "Was muss ich ueberweisen?"


def test_Z1_gewaehlte_ids_kommen_in_genannter_reihenfolge_zurueck():
    p = FakeProvider(text_antworten=[f"[{B.id}] [{A.id}]"])
    assert waehle(FRAGE, SET, p) == (B, A)


def test_Z2_erfundene_id_wird_verworfen():
    """Sonst schleust ein halluzinierender erster Schritt einen Absatz aus dem Nichts
    in den zweiten — und der zweite kann das nicht mehr merken."""
    p = FakeProvider(text_antworten=[f"[Erfunden.pdf#S9#A9] [{A.id}]"])
    assert waehle(FRAGE, SET, p) == (A,)


def test_Z3_keiner_ergibt_leere_auswahl():
    assert waehle(FRAGE, SET, FakeProvider(text_antworten=["keiner"])) == ()


def test_Z4_hoechstens_begrenzt_die_auswahl():
    p = FakeProvider(text_antworten=[f"[{A.id}] [{B.id}] [{C.id}]"])
    assert waehle(FRAGE, SET, p, hoechstens=2) == (A, B)


def test_Z5_doppelte_nennung_zaehlt_einmal():
    p = FakeProvider(text_antworten=[f"[{A.id}] [{A.id}] [{B.id}]"])
    assert waehle(FRAGE, SET, p) == (A, B)


def test_Z6_leerer_bestand_ruft_kein_modell():
    p = FakeProvider(text_antworten=[])   # jeder Aufruf wuerde werfen
    assert waehle(FRAGE, (), p) == ()


def test_Z7_anweisung_verbietet_die_antwort_im_ersten_schritt():
    """Der ganze Zweck der Trennung: Schritt 1 waehlt aus, er formuliert nicht."""
    assert "Keine Erklärung, keine Antwort auf die Frage" in AUSWAHL


def test_Z8_zweistufige_suche_antwortet_nur_aus_der_auswahl():
    """Die Auswahl ist ein echter erster Aufruf; der zweite sieht nur ihre Absätze."""
    p = FakeProvider(text_antworten=[f"[{A.id}]", f"1.002,41 EUR [{A.id}]"])
    paare = tuple(zip(SET, p.embed([f.text for f in SET])))
    frage = "Wie hoch ist der Rechnungsbetrag?"

    antwort = suche(frage, paare, p, schwelle=0.0, waehler=waehle)

    assert antwort.karten[0].fundstelle == A
    assert len(p.aufrufe) == 2
    assert B.text not in p.aufrufe[1][1]

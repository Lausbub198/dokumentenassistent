"""A1–A7: Abnahme-Ansicht (`/abnahme`) — der Auftraggeber fragt seinen EIGENEN Bestand und
urteilt selbst. Daraus entsteht ein Goldstandard, den niemand aus diesem Projekt geschrieben hat.

Eigene Datei statt Anbau an `tests/test_web.py`: dort sind W16b/W17/W18 im Volllauf derzeit
flaky (separat gemeldet), und ein zusätzlicher Fixture-Nachbar würde das nur verschlimmern.
Alles hier läuft mit FakeProvider, ohne Ollama und ohne Netz.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dokumentenassistent import web_ansicht as ansicht
from dokumentenassistent.typen import Antwort, Belegkarte, Fundstelle
from dokumentenassistent.web import create_app
from dokumentenassistent.werkstatt import Werkstatt
from tests.conftest import FakeProvider

FUNDSTELLE = Fundstelle(
    id="Mietvertrag.pdf#S2#A1",
    datei_hash="h1",
    datei_name="Mietvertrag.pdf",
    seite=2,
    absatz=1,
    text="Kaltmiete 780,00 EUR\nNebenkosten 120,00 EUR monatlich",
)
ANTWORT = Antwort(
    status="gefunden",
    text=f"Die Kaltmiete beträgt 780,00 EUR [{FUNDSTELLE.id}].",
    karten=(Belegkarte(fundstelle=FUNDSTELLE, wortlaut="Kaltmiete 780,00 EUR"),),
)
FRAGE = "Wie hoch ist die Kaltmiete?"


def _bauen(tmp_path, modus: str = "knapp"):
    """Werkstatt mit FakeProvider; `frage()` liefert eine feste Antwort, damit die Ansicht
    geprüft wird und nicht die Suche (die prüfen M11 und das Retrieval-Eval)."""
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    werkstatt = Werkstatt(
        quelle=quelle,
        zielablage=tmp_path / "ablage",
        provider=FakeProvider(),
        arbeitsordner=tmp_path / "arbeit",
    )
    gestellt: list[str] = []

    def frage(text: str) -> Antwort:
        gestellt.append(text)
        return ANTWORT

    werkstatt.frage = frage
    app = create_app(werkstatt, abnahme=tmp_path / "abnahme", abnahme_protokoll_laden=lambda: modus)
    klient = TestClient(app)
    klient.gestellt = gestellt
    klient.abnahme = tmp_path / "abnahme"
    return klient


@pytest.fixture
def client(tmp_path):
    """Standard-Modus `knapp` (seit 23.09.2026)."""
    return _bauen(tmp_path)


@pytest.fixture
def client_voll(tmp_path):
    """Modus `voll` — für Tests, die Frage/Antwort/Bemerkung im Klartext auf der Seite prüfen."""
    return _bauen(tmp_path, "voll")


def _urteile(client) -> list[dict]:
    dateien = sorted(Path(client.abnahme).glob("*/urteile*.jsonl"))
    return [json.loads(z) for d in dateien for z in d.read_text(encoding="utf-8").splitlines() if z.strip()]


def _formularwerte(seiten_html: str) -> dict:
    """Die versteckten Felder des Urteilsformulars — sie tragen Frage, Antwort und Belege
    zum POST, damit der Server zwischen den beiden Schritten nichts merken muss.
    `unescape` macht, was ein Browser beim Absenden auch tut."""
    import html
    import re

    return {
        name: html.unescape(wert)
        for name, wert in re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', seiten_html)
    }


# --------------------------------------------------------------- A1: Seite rendert


def test_A1_abnahme_seite_antwortet_mit_frageformular(client):
    seite = client.get("/abnahme")
    assert seite.status_code == 200
    assert 'name="frage"' in seite.text
    assert "Abnahme" in seite.text


def test_A1b_abnahme_ohne_werkstatt_leitet_auf_start(tmp_path):
    klient = TestClient(
        create_app(None, modelle=tmp_path / "modelle.yaml", zuletzt=tmp_path / "zuletzt.json",
                   provider_laden=lambda: FakeProvider(), provider_suche_laden=lambda: None),
        follow_redirects=False,
    )
    antwort = klient.get("/abnahme")
    assert (antwort.status_code, antwort.headers["location"]) == (303, "/start")


# ------------------------------------------------------- A2: Frage → Belegkarten


def test_A2_frage_ruft_werkstatt_und_zeigt_belegkarte_aufklappbar(client):
    seite = client.post("/abnahme", data={"frage": FRAGE})
    html = seite.text
    assert (seite.status_code, client.gestellt) == (200, [FRAGE])
    assert FUNDSTELLE.datei_name in html
    assert FUNDSTELLE.id in html
    assert "Kaltmiete 780,00 EUR" in html
    assert "<details" in html  # der Absatz klappt auf, statt die Seite zu fluten
    assert 'value="richtig"' in html and 'value="falsch"' in html
    assert 'name="bemerkung"' in html


# ------------------------------------------------------------- A3: Urteil anhängen


def test_A3_urteil_wird_als_zeile_angehaengt(client):
    """Standard-Modus `knapp` (23.09.2026): die Zeile belegt das Urteil, nicht den Wortlaut --
    weder Frage noch Antwort noch Dateiname/ID stehen im Klartext in der Datei."""
    html = client.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    antwort = client.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": "passt"})
    zeilen = _urteile(client)
    assert antwort.status_code == 200
    assert len(zeilen) == 1
    zeile = zeilen[0]
    assert (zeile["urteil"], zeile["bemerkung_zeichen"]) == ("richtig", len("passt"))
    assert zeile["status"] == "gefunden"
    assert zeile["karten_anzahl"] == 1
    assert "frage" not in zeile and "antwort" not in zeile and "belegkarten" not in zeile
    for verboten in (FRAGE, ANTWORT.text, "Kaltmiete 780,00 EUR", FUNDSTELLE.datei_name, FUNDSTELLE.id, "passt"):
        assert verboten not in json.dumps(zeile, ensure_ascii=False)
    assert set(zeile) >= {
        "zeit", "frage_hash", "frage_zeichen", "antwort_hash", "antwort_zeichen",
        "karten_ids_hash", "llm", "llm_suche", "embedding", "reranker", "top_n",
        "absaetze_durchsucht",
    }


def test_A3v_modus_voll_schreibt_wie_bisher_im_klartext(client_voll):
    """Modus `voll` (modelle.yaml `abnahme_protokoll: voll`) bleibt für den synthetischen
    Korpus: Frage, Antworttext und Belegkarten im Klartext, in `urteile-voll.jsonl`."""
    html = client_voll.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    client_voll.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": "passt"})
    voll_dateien = sorted(Path(client_voll.abnahme).glob("*/urteile-voll.jsonl"))
    assert len(voll_dateien) == 1
    assert sorted(Path(client_voll.abnahme).glob("*/urteile.jsonl")) == []  # nichts im knappen Namen
    zeile = json.loads(voll_dateien[0].read_text(encoding="utf-8").splitlines()[0])
    assert (zeile["frage"], zeile["antwort"], zeile["bemerkung"]) == (FRAGE, ANTWORT.text, "passt")
    assert zeile["belegkarten"] == [
        {"id": FUNDSTELLE.id, "datei": FUNDSTELLE.datei_name, "wortlaut": "Kaltmiete 780,00 EUR"}
    ]
    assert zeile["status"] == "gefunden"


def test_A3b_zweites_urteil_ueberschreibt_nichts(client):
    html = client.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    client.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": ""})
    client.post("/abnahme/urteil", data={**felder, "urteil": "falsch", "bemerkung": "Betrag veraltet"})
    zeilen = _urteile(client)
    assert [z["urteil"] for z in zeilen] == ["richtig", "falsch"]
    assert zeilen[1]["bemerkung_zeichen"] == len("Betrag veraltet")


def test_A3c_unbekanntes_urteil_wird_abgewiesen_und_schreibt_nichts(client):
    html = client.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    seite = client.post("/abnahme/urteil", data={**felder, "urteil": "vielleicht", "bemerkung": ""})
    assert seite.status_code == 200
    assert _urteile(client) == []


# ------------------------------------------------------------------ A4: Liste


def test_A4_liste_zeigt_zaehler_und_die_letzten_urteile(client_voll):
    html = client_voll.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    client_voll.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": ""})
    client_voll.post("/abnahme/urteil", data={**felder, "urteil": "falsch", "bemerkung": "daneben"})
    seite = client_voll.get("/abnahme")
    assert "2 Urteile" in seite.text
    assert "1 richtig" in seite.text
    assert "1 falsch" in seite.text
    assert "daneben" in seite.text


def test_A4b_liste_zeigt_hoechstens_zehn(client_voll):
    html = client_voll.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    for i in range(12):
        client_voll.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": f"Nr{i}"})
    text = client_voll.get("/abnahme").text
    assert "12 Urteile" in text
    assert "Nr11" in text
    assert "Nr0<" not in text and "Nr1<" not in text  # die ersten beiden sind aus der Liste gerutscht


def test_A4c_knapp_zeigt_hinweis_statt_wortlaut(client):
    """Standard-Modus `knapp`: die Liste zeigt Zeit/Urteil/Status/Kartenzahl/Längen, aber nicht
    Frage, Antwort oder Bemerkung im Klartext."""
    html = client.post("/abnahme", data={"frage": FRAGE}).text
    felder = _formularwerte(html)
    client.post("/abnahme/urteil", data={**felder, "urteil": "richtig", "bemerkung": "GEHEIMNIS_XYZ"})
    text = client.get("/abnahme").text
    assert "1 Urteile" in text and "1 richtig" in text
    assert "inhaltsfreies Protokoll" in text
    assert FRAGE not in text
    assert ANTWORT.text not in text
    assert "GEHEIMNIS_XYZ" not in text


# ------------------------------------------------------ urteilszeile() als reine Funktion


_GEHEIM_FRAGE = "Wie lautet GEHEIMNIS_XYZ im Mietvertrag?"
_GEHEIM_ANTWORT = "Der Betrag steht bei GEHEIMNIS_XYZ [Vertrag.pdf#S1#A1]."
_GEHEIM_KARTEN = [{"id": "Vertrag.pdf#S1#A1", "datei": "Vertrag.pdf", "wortlaut": "GEHEIMNIS_XYZ"}]
_GEHEIM_BEMERKUNG = "GEHEIMNIS_XYZ stimmt nicht"


def _zeile(modus: str, **override) -> dict:
    werte = {
        "zeit": "2026-09-23T12:00:00+02:00",
        "frage": _GEHEIM_FRAGE,
        "antwort_text": _GEHEIM_ANTWORT,
        "antwort_status": "gefunden",
        "belegkarten": _GEHEIM_KARTEN,
        "urteil": "richtig",
        "bemerkung": _GEHEIM_BEMERKUNG,
        "llm": "gemma4:12b-it-q4_K_M",
        "llm_suche": None,
        "embedding": "qwen3-embedding:0.6b",
        "reranker": "BAAI/bge-reranker-v2-m3",
        "top_n": 5,
        "absaetze_durchsucht": 42,
    } | override
    return ansicht.urteilszeile(modus, **werte)


def test_urteilszeile_knapp_enthaelt_keinen_klartext():
    zeile = _zeile("knapp")
    serialisiert = json.dumps(zeile, ensure_ascii=False)
    for verboten in (_GEHEIM_FRAGE, _GEHEIM_ANTWORT, "GEHEIMNIS_XYZ", "Vertrag.pdf", "Vertrag.pdf#S1#A1"):
        assert verboten not in serialisiert
    assert set(zeile) >= {
        "zeit", "frage_hash", "frage_zeichen", "antwort_hash", "antwort_zeichen", "status",
        "karten_ids_hash", "karten_anzahl", "urteil", "bemerkung_zeichen", "llm", "llm_suche",
        "embedding", "reranker", "top_n", "absaetze_durchsucht",
    }
    assert {"frage", "antwort", "belegkarten", "bemerkung"}.isdisjoint(zeile)
    assert zeile["frage_zeichen"] == len(_GEHEIM_FRAGE)
    assert zeile["bemerkung_zeichen"] == len(_GEHEIM_BEMERKUNG)
    assert zeile["karten_anzahl"] == 1


def test_urteilszeile_voll_enthaelt_den_klartext():
    zeile = _zeile("voll")
    serialisiert = json.dumps(zeile, ensure_ascii=False)
    for erwartet in (_GEHEIM_FRAGE, _GEHEIM_ANTWORT, "GEHEIMNIS_XYZ", "Vertrag.pdf"):
        assert erwartet in serialisiert
    assert zeile["frage"] == _GEHEIM_FRAGE
    assert zeile["antwort"] == _GEHEIM_ANTWORT
    assert zeile["belegkarten"] == _GEHEIM_KARTEN
    assert zeile["bemerkung"] == _GEHEIM_BEMERKUNG


def test_urteilszeile_gleicher_text_ergibt_gleichen_hash():
    a = _zeile("knapp")
    b = _zeile("knapp")
    assert a["frage_hash"] == b["frage_hash"]
    assert a["antwort_hash"] == b["antwort_hash"]
    assert a["karten_ids_hash"] == b["karten_ids_hash"]


def test_urteilszeile_anderer_text_ergibt_anderen_hash():
    a = _zeile("knapp")
    b = _zeile("knapp", frage="Eine ganz andere Frage", antwort_text="Eine ganz andere Antwort")
    assert a["frage_hash"] != b["frage_hash"]
    assert a["antwort_hash"] != b["antwort_hash"]


def test_urteilszeile_unbekannter_modus_wirft():
    with pytest.raises(ValueError):
        _zeile("halb")

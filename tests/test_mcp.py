"""MCP-Lesezugriff — P1–P11.

Drei lesende Werkzeuge über dem freigegebenen Bestand, jeder Aufruf im
Protokoll. Die Fachlogik (Suche, Freigabe) wird hier nicht erneut geprüft.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from dokumentenassistent.mcp_server import Lesezugriff, erzeuge_server
from tests.test_werkstatt import (
    ANTWORT_KALTMIETE,
    FRAGE_KALTMIETE,
    MIETVERTRAG,
    RECHNUNG,
    _protokoll,
    _vorbereiten,
    werkstatt,  # noqa: F401 — Fixture
)

FREI = f"{MIETVERTRAG}#S2#A1"  # Fundstelle der freigegebenen Datei
GESPERRT = f"{RECHNUNG}#S1#A1"  # Fundstelle einer eingeordneten, nicht freigegebenen Datei


@pytest.fixture
def freigegeben(werkstatt):
    """Bestand bis zur Freigabe des Mietvertrags; Rechnung bleibt eingeordnet, aber gesperrt."""
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.freigeben((hashes[MIETVERTRAG],))
    return werkstatt


def _mcp_zeilen(w) -> list[dict]:
    return [e for e in _protokoll(w) if e["art"] == "mcp"]


def test_P1_suchen_liefert_karten_nur_aus_freigegebenen_dateien(freigegeben):
    ergebnis = Lesezugriff(freigegeben).suchen(FRAGE_KALTMIETE)
    assert ergebnis['antwortstuetzung'] == 'ungeprueft'
    assert ergebnis['pruefverfahren'] == 'keine_semantische_pruefung'
    assert (ergebnis["status"], {k["datei"] for k in ergebnis["karten"]}) == ("gefunden", {MIETVERTRAG})


def test_P2_suchen_vor_freigabe_ist_nicht_gefunden_ohne_karten(werkstatt):
    _vorbereiten(werkstatt)
    werkstatt.einordnen()
    ergebnis = Lesezugriff(werkstatt).suchen(FRAGE_KALTMIETE)
    assert (ergebnis["status"], ergebnis["karten"]) == ("nicht_gefunden", [])


def test_P3_fundstelle_lesen_freigegeben_liefert_text(freigegeben):
    ergebnis = Lesezugriff(freigegeben).fundstelle_lesen(FREI)
    assert ergebnis["text"] == "Kaltmiete 780,00 EUR\nNebenkosten 120,00 EUR monatlich"


def test_mcp_gibt_startseite_und_alle_beitragsseiten_aus(freigegeben):
    from dataclasses import replace
    from dokumentenassistent.mcp_server import _karte
    from dokumentenassistent.typen import Belegkarte, SeitenSpanne

    f = freigegeben.index.fundstelle(FREI)
    assert Lesezugriff(freigegeben).fundstelle_lesen(FREI)["seiten"] == [2]
    grenze = f.text.index("\n")
    f = replace(f, spannen=(SeitenSpanne(2, 0, grenze),
                            SeitenSpanne(3, grenze + 1, len(f.text))))
    freigegeben.index.ersetze_fundstellen(f.datei_hash, (f,))
    assert Lesezugriff(freigegeben).fundstelle_lesen(FREI)["seiten"] == [2, 3]
    assert _karte(Belegkarte(f, "Kaltmiete"))["seiten"] == [2, 3]


def test_P4_fundstelle_lesen_nicht_freigegeben_wird_abgelehnt_ohne_text(freigegeben):
    ergebnis = Lesezugriff(freigegeben).fundstelle_lesen(GESPERRT)
    assert (ergebnis["abgelehnt"], "nicht freigegeben" in ergebnis["grund"], "text" in ergebnis) == (
        True,
        True,
        False,
    )


def test_P5_fundstelle_lesen_unbekannt_wird_abgelehnt(freigegeben):
    ergebnis = Lesezugriff(freigegeben).fundstelle_lesen("gibtsnicht#S1#A1")
    assert (ergebnis["abgelehnt"], "unbekannt" in ergebnis["grund"]) == (True, True)


def test_P6_datei_oeffnen_liefert_zielablage_nicht_quelle(freigegeben):
    ergebnis = Lesezugriff(freigegeben).datei_oeffnen(FREI)
    pfad = ergebnis["pfad"]
    assert (
        pfad.startswith(str(freigegeben.zielablage)),
        pfad.startswith(str(freigegeben.quelle)),
    ) == (True, False)


def test_P7_datei_oeffnen_nicht_freigegeben_wird_abgelehnt(freigegeben):
    ergebnis = Lesezugriff(freigegeben).datei_oeffnen(GESPERRT)
    assert (ergebnis["abgelehnt"], "pfad" in ergebnis) == (True, False)


def test_P8_jeder_aufruf_schreibt_genau_eine_mcp_zeile_mit_werkzeug_und_fundstellen(freigegeben):
    zugriff = Lesezugriff(freigegeben)
    zugriff.suchen(FRAGE_KALTMIETE)
    zugriff.fundstelle_lesen(FREI)
    zugriff.datei_oeffnen(FREI)
    zeilen = _mcp_zeilen(freigegeben)
    canonical = freigegeben.index.fundstelle(FREI).id
    assert [(z["werkzeug"], z["fundstellen"]) for z in zeilen] == [
        ("suchen", [canonical]),
        ("fundstelle_lesen", [canonical]),
        ("datei_oeffnen", [canonical]),
    ]


def test_mcp_search_never_sends_unapproved_document_to_model(tmp_path):
    from dokumentenassistent.typen import Datei, Fundstelle
    from dokumentenassistent.werkstatt import Werkstatt
    from tests.conftest import FakeProvider
    public = Datei('a'*64, tmp_path/'public.pdf', 'public.pdf', 1)
    private = Datei('b'*64, tmp_path/'private.pdf', 'private.pdf', 1)
    fpub = Fundstelle('pub', public.hash, public.name, 1, 1, 'Rechnung Betrag 10 EUR')
    fpriv = Fundstelle('priv', private.hash, private.name, 1, 1, 'GEHEIMNIS_XYZ Betrag 999 EUR')
    provider = FakeProvider(text_antworten=['10 EUR [pub]'])
    w = Werkstatt(tmp_path/'source', tmp_path/'dest', provider, arbeitsordner=tmp_path/'work')
    for doc, chunk in ((public, fpub), (private, fpriv)):
        w.index.registriere(doc, 'sicher')
        w.index.speichere_fundstellen((chunk,))
    vectors = provider.embed([fpub.text, fpriv.text])
    w.index.speichere_embeddings(((fpub.id, vectors[0]), (fpriv.id, vectors[1])),
        modell_revision=provider.embedding_revision(), erwartete_texte={fpub.id:fpub.text,fpriv.id:fpriv.text})
    w.index.markiere_bestaetigt(public.hash, tmp_path/'approved.pdf')
    result = Lesezugriff(w).suchen('Rechnung Betrag 10 EUR')
    prompt = next(value for kind,value in provider.aufrufe if kind=='text')
    assert result['status'] == 'gefunden'
    assert fpriv.text not in prompt
    assert fpub.text in prompt


def test_P9_abgelehnter_aufruf_schreibt_zeile_mit_abgelehnt_true(freigegeben):
    Lesezugriff(freigegeben).fundstelle_lesen(GESPERRT)
    zeile = _mcp_zeilen(freigegeben)[-1]
    assert (zeile["werkzeug"], zeile["abgelehnt"], zeile["fundstellen"], bool(zeile["grund"])) == (
        "fundstelle_lesen",
        True,
        [],
        True,
    )


def test_P10_server_registriert_genau_drei_lesende_tools(freigegeben):
    server = erzeuge_server(freigegeben)
    tools = asyncio.run(server.list_tools())
    assert sorted(t.name for t in tools) == ["datei_oeffnen", "fundstelle_lesen", "suchen"]


def test_P11_tool_ueber_server_liefert_dasselbe_wie_direkter_aufruf(freigegeben):
    freigegeben.provider.text_antworten.append(ANTWORT_KALTMIETE)  # zweiter Suchlauf braucht eine Antwort
    direkt = Lesezugriff(freigegeben).suchen(FRAGE_KALTMIETE)
    server = erzeuge_server(freigegeben)
    ergebnis = asyncio.run(server.call_tool("suchen", {"frage": FRAGE_KALTMIETE}))
    assert json.loads(ergebnis.content[0].text) == direkt

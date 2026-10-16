"""Belastungstest-Geschirr — L1–L6 gegen FakeProvider, Steuerfall-Korpus, tests/golden.json.

Kein Ollama: `speicher` wird gestubbt, der Provider antwortet schema-abhängig.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dokumentenassistent.lasttest import kopiere_stufe, lauf
from dokumentenassistent.lasttest_bericht import schreibe_bericht
from tests.conftest import FakeProvider

REPO = Path(__file__).resolve().parent.parent
KORPUS = REPO / "beispiele" / "steuerfall" / "Quelle"
GOLDEN: dict = json.loads((REPO / "tests" / "golden.json").read_text(encoding="utf-8"))

PFLICHTFELDER = {
    "stufe", "llm", "embedding", "dateien", "seiten", "fundstellen", "zeit_s", "modellaufrufe",
    "modellzeit_s", "status_verteilung", "soll_status_treffer", "soll_kategorie_treffer",
    "belege_gesamt", "belege_ungueltig", "konflikte_gefunden", "konflikte_soll", "konflikte_treffer",
    "fragen", "fragen_treffer_quote", "korrekturen_mensch", "speicher", "fehler",
    "reranker", "rerank_k", "top_n",
}
PROFIL = {
    "kategorien": ["Wohnung Nord", "Wohnung Süd", "Sonstiges"],
    "dokumenttypen": ["Rechnung", "Vertrag"],
    "felder": ["datum", "aussteller", "betrag", "rechnungsnummer"],
    "namensschema": "{typ}_{kategorie}",  # ohne Feldplatzhalter → sicher auch ohne belegte Felder
}
EINORDNUNG = {"kategorie": "Wohnung Nord", "typ": "Rechnung", "felder": [], "begruendung": "Test"}


class StapelFake(FakeProvider):
    """Eingereihte Antworten (oder Exceptions) gehen vor; sonst antwortet er je Schema —
    so hängt der Test nicht an der Zahl der Modellaufrufe."""

    def generate_json(self, prompt: str, schema: dict) -> dict:
        if self.json_antworten:
            return super().generate_json(prompt, schema)
        return PROFIL if "namensschema" in schema["properties"] else EINORDNUNG

    def generate_text(self, prompt: str) -> str:
        return "nicht gefunden"


def _hashes(ordner: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ordner.rglob("*")) if p.is_file()}


def _zeilen(ordner: Path) -> list[dict]:
    return [json.loads(z) for z in (ordner / "laeufe.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def voller_lauf(tmp_path_factory) -> dict:
    ausgabe = tmp_path_factory.mktemp("last")
    vorher = _hashes(KORPUS)
    zeile = lauf(KORPUS, GOLDEN, 13, StapelFake(), ausgabe, llm="fake", embedding="fake", speicher=lambda: "-")
    return {"zeile": zeile, "ausgabe": ausgabe, "vorher": vorher, "nachher": _hashes(KORPUS)}


def test_L1_ein_lauf_schreibt_genau_eine_zeile_mit_allen_pflichtfeldern(voller_lauf):
    zeilen = _zeilen(voller_lauf["ausgabe"])
    assert (len(zeilen), PFLICHTFELDER - set(zeilen[0]), zeilen[0]["fehler"], zeilen[0]["dateien"]) == (
        1, set(), None, 13,
    )


def test_L2_kennzahlen_stimmen_gegen_golden(voller_lauf):
    """11 Modellantworten „Wohnung Nord/Rechnung" ohne Felder: 11 sicher, 1 Duplikat, 1 OCR unsicher.
    Status trifft 9 von 13 golden-Dateien; Kategorie stimmt bei 5 der 7 sicheren mit Sollkategorie."""
    z = voller_lauf["zeile"]
    assert (
        z["status_verteilung"], z["soll_status_treffer"], z["soll_kategorie_treffer"],
        z["modellaufrufe"]["generate_json"], z["belege_gesamt"], len(z["fragen"]),
    ) == (
        {"sicher": 11, "konflikt": 0, "unklar": 0, "duplikat": 1, "ocr_unsicher": 1},
        round(9 / 13, 3), round(5 / 7, 3), 12, 0, 3,
    )


def test_L3_fehler_im_einordnen_erzeugt_zeile_mit_fehler_statt_absturz(tmp_path):
    provider = StapelFake(json_antworten=[PROFIL, RuntimeError("Ollama weg")])
    zeile = lauf(KORPUS, GOLDEN, 3, provider, tmp_path, speicher=lambda: "-")
    assert (zeile["fehler"]["phase"], zeile["fehler"]["text"], len(_zeilen(tmp_path)), zeile["fragen"]) == (
        "einordnen", "Ollama weg", 1, [],
    )


def test_L4_bericht_hat_eine_tabellenzeile_je_stufe(tmp_path):
    basis = {
        "dateien": 10, "zeit_s": {"einordnen": 20.0}, "status_verteilung": {"sicher": 8, "unklar": 2},
        "soll_kategorie_treffer": 0.9, "belege_ungueltig": 1, "belege_gesamt": 30,
        "konflikte_gefunden": 1, "konflikte_soll": 1,
        "fragen": [{"frage": "F1", "treffer": True, "dauer_s": 2.0}, {"frage": "F2", "treffer": False, "dauer_s": 4.0}],
    }
    zeilen = [
        {**basis, "llm": "a", "stufe": 10},
        {**basis, "llm": "a", "stufe": 25, "fragen": [], "fehler": {"phase": "einordnen", "typ": "X", "text": "kaputt"}},
        {**basis, "llm": "b", "stufe": 10},
    ]
    (tmp_path / "laeufe.jsonl").write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")
    bericht = schreibe_bericht(tmp_path).read_text(encoding="utf-8")
    tabellenzeilen = [z for z in bericht.splitlines() if z.startswith(("| 10 |", "| 25 |"))]
    assert (len(tabellenzeilen), "| F2 | rot | – | rot |" in bericht, "FEHLER in einordnen" in bericht) == (
        3, True, True,
    )


def test_L5_stufenauswahl_kopiert_nur_die_dateien_der_stufe(tmp_path):
    """Drei Regeln: `stufen`-Dict mit Pfadliste (Malerbetrieb), `ab_stufe` je Datei, sonst erste N."""
    per_liste = kopiere_stufe(KORPUS, {"stufen": {"2": ["Beleg.pdf", "Hausgeld.pdf"]}}, 2, tmp_path / "a")
    mit_ab_stufe = kopiere_stufe(KORPUS, {"dateien": {"Anhang.pdf": {"ab_stufe": 50}}}, 10, tmp_path / "b")
    erste_fuenf = kopiere_stufe(KORPUS, GOLDEN, 5, tmp_path / "c")
    assert (
        [p.name for p in per_liste], len(mit_ab_stufe), "Anhang.pdf" in {p.name for p in mit_ab_stufe},
        [p.name for p in erste_fuenf], len(list((tmp_path / "c").iterdir())),
    ) == (
        ["Beleg.pdf", "Hausgeld.pdf"], 12, False,
        ["Anhang.pdf", "Beleg.pdf", "Dokument1 Kopie.pdf", "Dokument1.pdf", "Hausgeld.pdf"], 5,
    )


def test_L6_originalkorpus_bleibt_hashgleich(voller_lauf):
    assert voller_lauf["nachher"] == voller_lauf["vorher"]


def test_L8_zeile_traegt_reranker_rerank_k_top_n(tmp_path):
    """Ohne Angabe: heutiges Verhalten (kein Reranker, 20/8) — aber in der Zeile sichtbar,
    damit ein Lauf ohne Reranker von einem mit unterscheidbar bleibt."""
    from dokumentenassistent.provider import Sucheinstellungen

    ohne = lauf(KORPUS, GOLDEN, 3, StapelFake(), tmp_path / "a", speicher=lambda: "-")
    assert (ohne["reranker"], ohne["rerank_k"], ohne["top_n"]) == (None, 20, 8)

    class FakeReranker:
        def bewerte(self, frage, texte):
            return [0.0] * len(texte)

    mit = lauf(
        KORPUS, GOLDEN, 3, StapelFake(), tmp_path / "b", speicher=lambda: "-",
        sucheinstellungen=Sucheinstellungen(reranker=FakeReranker(), rerank_k=30, top_n=12),
        reranker_name="BAAI/bge-reranker-v2-m3",
    )
    assert (mit["reranker"], mit["rerank_k"], mit["top_n"]) == ("BAAI/bge-reranker-v2-m3", 30, 12)


def test_L9_cli_argumente_reranker_rerank_k_top_n(tmp_path, monkeypatch):
    """--reranker/--rerank-k/--top-n landen unverändert in den Sucheinstellungen des Laufs."""
    from dokumentenassistent import lasttest
    from dokumentenassistent import provider as provider_modul

    class FakeCrossEncoder:
        def __init__(self, modell, geraet=None):
            self.modell, self.geraet = modell, geraet

        def bewerte(self, frage, texte):
            return [0.0] * len(texte)

    monkeypatch.setattr(provider_modul, "CrossEncoderReranker", FakeCrossEncoder)
    gesehen: dict = {}

    def fake_lauf(korpus, golden, stufe, provider, ausgabe, **kwargs):
        gesehen.update(kwargs)
        return {"dateien": 0, "zeit_s": {"gesamt": 0.0}, "fehler": None}

    monkeypatch.setattr(lasttest, "lauf", fake_lauf)
    monkeypatch.setattr(lasttest, "schreibe_bericht", lambda ordner: "")
    monkeypatch.setattr(lasttest, "schreibe_umgebung", lambda ordner: None)
    lasttest.main([
        "--korpus", str(KORPUS.parent), "--golden", str(REPO / "tests" / "golden.json"),
        "--stufen", "3", "--ausgabe", str(tmp_path),
        "--reranker", "BAAI/bge-reranker-v2-m3", "--rerank-k", "30", "--top-n", "12",
        "--rerank-geraet", "mps",
    ])
    einstellungen = gesehen["sucheinstellungen"]
    assert (einstellungen.rerank_k, einstellungen.top_n) == (30, 12)
    assert (einstellungen.reranker.modell, einstellungen.reranker.geraet) == (
        "BAAI/bge-reranker-v2-m3", "mps",
    )
    assert gesehen["reranker_name"] == "BAAI/bge-reranker-v2-m3"


def test_L7_karte_datei_enthaelt_wertet_erste_belegkarte():
    from dokumentenassistent.lasttest_bericht import frage_zeile
    from dokumentenassistent.typen import Antwort, Belegkarte
    from tests.conftest import fs
    karte = Belegkarte(fs("Rechnung (4).pdf#S1#A1", "x", datei="Rechnung (4).pdf"), "x")
    soll = {"frage": "Summe?", "status": None, "pruefung": "karte_datei_enthaelt", "dateien": ["Rechnung (4).pdf"]}
    assert frage_zeile(soll, Antwort("gefunden", "…", (karte,)), 0.1)["treffer"] is True

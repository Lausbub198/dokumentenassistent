"""R1–R10: Retrieval-Eval ohne LLM, ausschließlich mit FakeProvider (keine Ollama-Aufrufe)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dokumentenassistent.retrieval_eval import (
    RetrievalEvalFehler,
    fundstellen_der_stufe,
    golden_filter,
    kennzahlen_variante,
    lauf,
    nicht_gefunden_quote,
    rang_der_datei,
    rang_des_absatzes,
    ranglisten_frage,
)
from dokumentenassistent.retrieval_eval_bericht import (
    baue_bericht,
    lese_laeufe,
    schreibe_bericht,
)
from dokumentenassistent.retrieval_reranker import kurzname
from dokumentenassistent.retrieval_varianten import (
    HYBRID_VARIANTEN,
    LEXIKALISCHE_VARIANTEN,
    bm25_komposita_rang,
    bm25_praefix_rang,
    erweitere_frage,
    rrf_gewichtet,
    vokabular_der_fundstellen,
    zerlege_komposita,
)
from dokumentenassistent.suche import bm25_rang, rrf
from tests.conftest import FakeProvider, fs, schreibe_text_pdf

# ------------------------------------------------------------------- R1: Golden-Filter

def test_R1_golden_filter_trennt_gefunden_und_nicht_gefunden():
    fragen = (
        {"frage": "F1", "status": "gefunden", "datei": "a.pdf"},
        {"frage": "F2", "status": "nicht_gefunden"},
        {"frage": "F3", "status": "gefunden"},  # keine Datei -> zählt nicht als gefunden
        {"frage": "F4", "status": None, "pruefung": "karte_datei_enthaelt"},  # Summenfrage: weder noch
    )
    gefunden, nicht_gefunden = golden_filter(fragen)
    assert ([f["frage"] for f in gefunden], [f["frage"] for f in nicht_gefunden]) == (["F1"], ["F2"])


# --------------------------------------------------------------- R2: Rang-Funktion

def test_R2_rang_der_datei_findet_ersten_treffer_und_none_sonst():
    fundstellen_je_id = {
        "a.pdf#S1#A1": fs("a.pdf#S1#A1", "x", datei="a.pdf"),
        "b.pdf#S1#A1": fs("b.pdf#S1#A1", "y", datei="b.pdf"),
        "b.pdf#S1#A2": fs("b.pdf#S1#A2", "z", datei="b.pdf"),
    }
    rangliste = (("a.pdf#S1#A1", 0.9), ("b.pdf#S1#A1", 0.5), ("b.pdf#S1#A2", 0.4))
    assert rang_der_datei(rangliste, fundstellen_je_id, "b.pdf") == 2
    assert rang_der_datei(rangliste, fundstellen_je_id, "a.pdf") == 1
    assert rang_der_datei(rangliste, fundstellen_je_id, "c.pdf") is None
    assert rang_der_datei((), fundstellen_je_id, "a.pdf") is None


# ---------------------------------------------------------------- R3: Kennzahlen

def test_R3_kennzahlen_variante_recall_und_mrr_handbeispiel():
    # 4 Fragen, Ränge 1, 3, nicht gefunden, 5
    kennzahlen = kennzahlen_variante([1, 3, None, 5])
    assert kennzahlen == {
        "recall_at_1": round(1 / 4, 3),
        "recall_at_3": round(2 / 4, 3),
        "recall_at_5": round(3 / 4, 3),
        "recall_at_8": round(3 / 4, 3),
        "recall_at_12": round(3 / 4, 3),
        "recall_at_20": round(3 / 4, 3),
        "mrr": round((1 / 1 + 1 / 3 + 0 + 1 / 5) / 4, 3),
    }


def test_R3_kennzahlen_variante_recall_at_12_und_20_trennen_tiefe_raenge():
    """top_n war nie gemessen: 1/5/8 zeigen nicht, was ein größeres Fenster einfängt."""
    kennzahlen = kennzahlen_variante([9, 13, 21])
    assert (
        kennzahlen["recall_at_8"], kennzahlen["recall_at_12"], kennzahlen["recall_at_20"],
    ) == (0.0, round(1 / 3, 3), round(2 / 3, 3))


def test_R3_kennzahlen_variante_leere_liste_gibt_none():
    assert kennzahlen_variante([]) == {
        "recall_at_1": None, "recall_at_3": None, "recall_at_5": None, "recall_at_8": None,
        "recall_at_12": None, "recall_at_20": None, "mrr": None,
    }


def test_R3_nicht_gefunden_quote_zaehlt_scores_unter_schwelle():
    assert nicht_gefunden_quote([0.01, 0.03, 0.0, 0.5], schwelle=0.02) == round(2 / 4, 3)
    assert nicht_gefunden_quote([], schwelle=0.02) is None


# ------------------------------------------------------------ R4: Varianten (Fake)

@pytest.fixture
def mini_fundstellen():
    return (
        fs("a.pdf#S1#A1", "Die Rechnung für die Heizung beträgt 500 Euro", datei="a.pdf"),
        fs("b.pdf#S1#A1", "Der Vertrag über das Fahrzeug läuft bis 2027", datei="b.pdf"),
        fs("b.pdf#S1#A2", "Zahlbar innerhalb von 14 Tagen nach Rechnungseingang", datei="b.pdf"),
        fs("c.pdf#S1#A1", "Notiz: Besprechung am Montag um 9 Uhr", datei="c.pdf"),
    )


def test_R4_ranglisten_frage_liefert_bm25_dense_hybrid(mini_fundstellen):
    provider = FakeProvider()
    vektoren = provider.embed([f.text for f in mini_fundstellen])
    paare = tuple(zip(mini_fundstellen, vektoren))
    ranglisten = ranglisten_frage("Wie hoch ist die Rechnung für die Heizung?", mini_fundstellen, paare, provider)
    assert set(ranglisten) == {"bm25", "dense", "hybrid"}
    # a.pdf teilt die meisten Wörter mit der Frage -> muss in bm25 vorne liegen
    assert ranglisten["bm25"][0][0] == "a.pdf#S1#A1"
    # jede Rangliste ist absteigend sortiert
    for rangliste in ranglisten.values():
        scores = [s for _, s in rangliste]
        assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------- R5: Fundstellen ohne LLM

def test_R5_fundstellen_der_stufe_nutzt_erfassen_und_auslesen_ohne_modellaufruf(tmp_path):
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    schreibe_text_pdf(korpus / "Rechnung (2).pdf", ["Rechnung Nr. 2025-0815\nBetrag 500 EUR"])
    golden = {"stufen": {}}
    provider = FakeProvider()  # keine Antworten eingereiht -> jeder Modellaufruf wirft AssertionError
    fundstellen = fundstellen_der_stufe(korpus, golden, 1, provider, tmp_path / "arbeit")
    assert len(fundstellen) >= 1
    assert fundstellen[0].datei_name == "Rechnung (2).pdf"
    assert provider.aufrufe == []  # erfassen/auslesen rufen den Provider nicht auf


def test_R5_fundstellen_der_stufe_ohne_dateien_ist_ein_fehler(tmp_path):
    korpus = tmp_path / "leer"
    korpus.mkdir()
    with pytest.raises(RetrievalEvalFehler):
        fundstellen_der_stufe(korpus, {"stufen": {}}, 1, FakeProvider(), tmp_path / "arbeit")


# ------------------------------------------------------------- R6: voller Lauf

@pytest.fixture
def kleiner_korpus(tmp_path):
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    schreibe_text_pdf(korpus / "Rechnung Heizung.pdf", ["Rechnung für die Heizung, Betrag 500 Euro"])
    schreibe_text_pdf(korpus / "Vertrag Fahrzeug.pdf", ["Vertrag über das Fahrzeug, Laufzeit bis 2027"])
    golden = {
        "fragen": [
            {"frage": "Was kostet die Heizung?", "status": "gefunden", "datei": "Rechnung Heizung.pdf", "ab_stufe": 0},
            {"frage": "Was steht im Kaufvertrag für den Bagger?", "status": "nicht_gefunden", "ab_stufe": 0},
        ],
    }
    return korpus, golden


def test_R6_lauf_schreibt_bm25_und_je_embedding_dense_und_hybrid(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    ausgabe = tmp_path / "ausgabe"
    zeilen = lauf(
        korpus, golden, 10, ("fake-a", "fake-b"),
        lambda emb: FakeProvider(), ausgabe, host="http://test",
    )
    varianten = {(z["variante"], z["embedding"]) for z in zeilen}
    lexikalisch = {(name, None) for name in LEXIKALISCHE_VARIANTEN}
    je_embedding = {(name, emb) for emb in ("fake-a", "fake-b") for name in ("dense", *HYBRID_VARIANTEN)}
    assert varianten == lexikalisch | je_embedding
    assert {"bm25", "bm25_komposita", "bm25_praefix"} <= set(LEXIKALISCHE_VARIANTEN)
    assert {"hybrid", "hybrid_w0.5", "hybrid_w0.25", "hybrid_komposita_w1.0", "hybrid_komposita_w0.5"} <= set(
        HYBRID_VARIANTEN
    )
    geschrieben = lese_laeufe(ausgabe / "laeufe.jsonl")
    assert len(geschrieben) == len(zeilen) == 3 + 2 * 6
    bm25_zeile = next(z for z in zeilen if z["variante"] == "bm25")
    assert (bm25_zeile["fragenzahl"], bm25_zeile["fragenzahl_nicht_gefunden"], bm25_zeile["embed_sekunden"]) == (
        1, 1, None,
    )
    dense_zeile = next(z for z in zeilen if z["variante"] == "dense" and z["embedding"] == "fake-a")
    assert dense_zeile["embed_sekunden"] is not None
    assert dense_zeile["recall_at_1"] in (0.0, 1.0)
    # top_score je Frage beider Klassen: Datengrundlage für suche.SCHWELLE (21.09.)
    assert 0.0 < dense_zeile["fragen"][0]["top_score"] <= 1.0
    assert [z["frage"] for z in dense_zeile["nicht_gefunden_fragen"]] == ["Was steht im Kaufvertrag für den Bagger?"]


def test_R6_lauf_ohne_embedding_ist_ein_fehler(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    with pytest.raises(RetrievalEvalFehler):
        lauf(korpus, golden, 0, (), lambda emb: FakeProvider(), tmp_path / "ausgabe")


def test_R6_lauf_ohne_passende_fragen_ist_ein_fehler(kleiner_korpus, tmp_path):
    korpus, _ = kleiner_korpus
    golden = {"fragen": [{"frage": "F", "status": None, "ab_stufe": 0}]}
    with pytest.raises(RetrievalEvalFehler):
        lauf(korpus, golden, 0, ("fake",), lambda emb: FakeProvider(), tmp_path / "ausgabe")


def test_R6_abbruch_beim_zweiten_embedding_laesst_die_lexikalischen_zeilen_da(kleiner_korpus, tmp_path):
    """Gemessen 22./23.09.2026: zwei Läufe kosteten je 76 Minuten und hinterließen keine
    Zeile, weil erst nach dem letzten Embedding geschrieben wurde."""
    korpus, golden = kleiner_korpus
    ausgabe = tmp_path / "ausgabe"

    def provider(embedding: str):
        if embedding == "kaputt":
            raise RuntimeError("Embedding-Dienst weg")
        return FakeProvider()

    with pytest.raises(RuntimeError):
        lauf(korpus, golden, 10, ("fake", "kaputt"), provider, ausgabe)
    zeilen = [json.loads(z) for z in (ausgabe / "laeufe.jsonl").read_text("utf-8").splitlines()]
    assert {z["embedding"] for z in zeilen} == {None, "fake"}


# --------------------------------------------------------------- R7: Berichtstabelle

def test_R7_bericht_hat_tabellenzeile_je_variante_und_wo_es_bricht(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    ausgabe = tmp_path / "ausgabe"
    lauf(korpus, golden, 10, ("fake",), lambda emb: FakeProvider(), ausgabe)
    pfad = schreibe_bericht(ausgabe)
    text = pfad.read_text(encoding="utf-8")
    assert "| bm25 |" in text
    assert "| dense | fake |" in text
    assert "| hybrid | fake |" in text
    assert "| bm25_komposita | – |" in text
    assert "| hybrid_w0.5 | fake |" in text
    assert "| hybrid_komposita_w1.0 | fake |" in text
    assert "## Wo es bricht" in text
    assert "hybrid_w0.25@fake" in text
    assert "bm25_praefix@-" in text
    assert "Was kostet die Heizung?" in text
    # sortiert nach Variante, dann Embedding
    assert text.index("| bm25 |") < text.index("| bm25_komposita |") < text.index("| dense |") < text.index("| hybrid |")


def test_R7_bericht_zeigt_recall_at_3_12_20():
    zeile = {
        "variante": "dense", "embedding": "fake", "fundstellenzahl": 3, "embed_sekunden": 1.0,
        "recall_at_1": 0.5, "recall_at_3": 0.6, "recall_at_5": 0.7, "recall_at_8": 0.8,
        "recall_at_12": 0.9, "recall_at_20": 1.0, "mrr": 0.6,
        "nicht_gefunden_treffer_quote": 1.0, "dauer_s_frage_avg": 0.1, "fragen": [],
    }
    text = baue_bericht((zeile,))
    assert "Recall@3" in text and "Recall@12" in text and "Recall@20" in text
    assert "| dense | fake | 3 | 1.0 | 50 | 60 | 70 | 80 | 90 | 100 | 0.6 |" in text


def test_R7_baue_bericht_ohne_zeilen_ist_lesbar():
    assert "Keine Läufe" in baue_bericht(())


def test_R7_lese_laeufe_fehlende_datei_gibt_leeres_tuple(tmp_path):
    assert lese_laeufe(tmp_path / "nicht_da.jsonl") == ()


# ------------------------------------------------------- R8: gewichtete RRF

def test_R8_rrf_gewichtet_mit_gewicht_1_entspricht_rrf():
    a = (("x", 0.9), ("y", 0.5))
    b = (("y", 0.8), ("z", 0.1))
    assert rrf_gewichtet(((a, 1.0), (b, 1.0))) == rrf((a, b))


def test_R8_rrf_gewichtet_skaliert_nur_die_gewichtete_liste():
    a = (("x", 0.9),)
    b = (("y", 0.8),)
    punkte = dict(rrf_gewichtet(((a, 0.5), (b, 1.0)), k=60))
    assert punkte == {"x": pytest.approx(0.5 / 61), "y": pytest.approx(1 / 61)}
    assert rrf_gewichtet(((a, 0.5), (b, 1.0)))[0][0] == "y"


def test_R8_rrf_gewichtet_leer():
    assert rrf_gewichtet(()) == ()
    assert rrf_gewichtet((((), 0.5),)) == ()


def test_R8_rrf_zaehlt_doppelte_id_pro_rangliste_nur_einmal():
    doppelt = (("x", 0.9), ("x", 0.8))
    einzel = (("x", 0.9),)

    assert rrf((doppelt,)) == (("x", 1 / 61),)
    assert rrf((doppelt,)) == rrf((einzel,))


# ------------------------------------------------------ R9: Komposita zerlegen

VOKABULAR = frozenset({"telefon", "rechnung", "nummer", "fassade", "farbe", "kita", "sonne"})


def test_R9_zerlege_komposita_zwei_teile_mit_und_ohne_fuge():
    assert zerlege_komposita("telefonrechnung", VOKABULAR) == ("telefon", "rechnung")
    assert zerlege_komposita("rechnungsnummer", VOKABULAR) == ("rechnung", "nummer")  # Fugen-s
    assert zerlege_komposita("fassadenfarbe", VOKABULAR) == ("fassade", "farbe")  # Fugen-n


def test_R9_zerlege_komposita_kein_treffer_gibt_leer():
    assert zerlege_komposita("sonnenschein", VOKABULAR) == ()  # "schein" nicht im Vokabular
    assert zerlege_komposita("rechnung", VOKABULAR) == ()  # 8 Zeichen, aber nicht zusammengesetzt


def test_R9_zerlege_komposita_kurze_tokens_unveraendert():
    assert zerlege_komposita("telefon", VOKABULAR) == ()
    assert zerlege_komposita("kitafar", VOKABULAR) == ()


def test_R9_erweitere_frage_haengt_teile_an_und_laesst_kurze_tokens():
    assert erweitere_frage("Telefon Nummer", VOKABULAR) == "Telefon Nummer"
    assert erweitere_frage("Wie hoch war die Telefonrechnung?", VOKABULAR) == (
        "Wie hoch war die Telefonrechnung? telefon rechnung"
    )


def test_R9_vokabular_der_fundstellen_tokens_ab_vier_zeichen():
    fundstellen = (fs("a.pdf#S1#A1", "Die Telefon-Rechnung Nr. 12345", datei="a.pdf"),)
    assert vokabular_der_fundstellen(fundstellen) == frozenset({"telefon", "rechnung", "12345"})


# --------------------------------------------- R10: BM25-Varianten auf Fundstellen

@pytest.fixture
def komposita_fundstellen():
    return (
        fs("a.pdf#S1#A1", "Telefon Rechnung März 500 Euro", datei="a.pdf"),
        fs("b.pdf#S1#A1", "Vertrag über das Fahrzeug bis 2027", datei="b.pdf"),
        fs("c.pdf#S1#A1", "Notiz: Besprechung am Montag", datei="c.pdf"),
    )


def test_R10_bm25_komposita_findet_was_bm25_nicht_findet(komposita_fundstellen):
    vokabular = vokabular_der_fundstellen(komposita_fundstellen)
    assert bm25_rang("Telefonrechnung", komposita_fundstellen) == ()
    rangliste = bm25_komposita_rang("Telefonrechnung", komposita_fundstellen, vokabular)
    assert rangliste[0][0] == "a.pdf#S1#A1"
    assert len(rangliste) == 1


def test_R10_bm25_praefix_trifft_ab_fuenf_zeichen(komposita_fundstellen):
    vokabular = vokabular_der_fundstellen(komposita_fundstellen)
    assert bm25_praefix_rang("Telefonrechnung", komposita_fundstellen, vokabular)[0][0] == "a.pdf#S1#A1"
    assert bm25_praefix_rang("Rechn", komposita_fundstellen, vokabular)[0][0] == "a.pdf#S1#A1"
    assert bm25_praefix_rang("Rech", komposita_fundstellen, vokabular) == ()
    assert bm25_praefix_rang("Vertrag", komposita_fundstellen, vokabular)[0][0] == "b.pdf#S1#A1"


# ------------------------------------------------------- R12: Reranker-Varianten im Eval (M4)


class _FakeRerankerImmerErsterAbsatz:
    """Bewertet den ersten übergebenen Text am höchsten — reicht, um zu prüfen, dass `lauf()`
    die Reranker-Variante tatsächlich durchreicht, ohne sentence-transformers zu importieren."""

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        return [1.0] + [0.0] * (len(texte) - 1)


def test_R12_lauf_mit_reranker_erzeugt_dense_rerank_variante_je_modell_und_k(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    ausgabe = tmp_path / "ausgabe"
    reranker_je_modell = {"fake/Reranker-Modell": _FakeRerankerImmerErsterAbsatz()}
    zeilen = lauf(
        korpus, golden, 10, ("fake-a",), lambda emb: FakeProvider(), ausgabe,
        reranker_je_modell=reranker_je_modell, reranker_k=(8, 20),
    )
    varianten = {(z["variante"], z["embedding"]) for z in zeilen}
    erwartete_reranker_varianten = {
        (f"dense_rerank_{kurzname('fake/Reranker-Modell')}_k{k}", "fake-a") for k in (8, 20)
    }
    assert erwartete_reranker_varianten <= varianten
    rerank_zeile = next(z for z in zeilen if z["variante"].startswith("dense_rerank_"))
    assert rerank_zeile["fragen"][0]["rerank_sekunden"] >= 0.0
    # dense selbst trägt kein rerank_sekunden-Feld
    dense_zeile = next(z for z in zeilen if z["variante"] == "dense" and z["embedding"] == "fake-a")
    assert "rerank_sekunden" not in dense_zeile["fragen"][0]


def test_R12_lauf_ohne_reranker_erzeugt_keine_dense_rerank_variante(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    zeilen = lauf(korpus, golden, 10, ("fake-a",), lambda emb: FakeProvider(), tmp_path / "ausgabe")
    assert not any(z["variante"].startswith("dense_rerank_") for z in zeilen)


def test_R13_rang_des_absatzes_zaehlt_die_fundstelle_selbst():
    rangliste = (("a.pdf#S1#A1", 0.9), ("b.pdf#S1#A1", 0.5), ("b.pdf#S1#A2", 0.4))
    assert rang_des_absatzes(rangliste, "b.pdf#S1#A2") == 3
    assert rang_des_absatzes(rangliste, "a.pdf#S1#A1") == 1
    assert rang_des_absatzes(rangliste, "c.pdf#S1#A1") is None
    assert rang_des_absatzes((), "a.pdf#S1#A1") is None


def test_R13_bestand_umgeht_den_korpusordner_und_weist_absatzgenau_aus(tmp_path):
    """GermanQuAD-Form: je Absatz eine Fundstelle, `datei` == `absatz_id`. Dateigenau und
    absatzgenau müssen dann dieselben Zahlen liefern — genau das prüft dieser Test."""
    fundstellen = (
        fs("c1", "Der Testturm für den seillosen Aufzug steht in Rottweil", datei="c1"),
        fs("c2", "In Sichuan wächst vor allem Reis", datei="c2"),
    )
    fragen = (
        {"frage": "Wo steht der Testturm für den seillosen Aufzug?", "status": "gefunden",
         "datei": "c1", "absatz_id": "c1"},
    )
    ausgabe = tmp_path / "ausgabe"
    zeilen = lauf(
        Path("beweise/germanquad"), {}, len(fundstellen), ("fake",), lambda emb: FakeProvider(),
        ausgabe, bestand=(fundstellen, fragen), zusatz={"ziehung": {"seed": 42, "gezogen": 1}},
    )
    dense = next(z for z in zeilen if z["variante"] == "dense")
    assert dense["fundstellenzahl"] == 2
    assert dense["fragenzahl"] == 1
    assert dense["absatzgenau"]["recall_at_1"] == dense["recall_at_1"]
    assert dense["absatzgenau"]["mrr"] == dense["mrr"]
    assert dense["fragen"][0]["rang_absatz"] == dense["fragen"][0]["rang"]
    assert dense["ziehung"] == {"seed": 42, "gezogen": 1}


def test_R13_ohne_absatz_id_bleibt_die_zeile_wie_bisher(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    zeilen = lauf(korpus, golden, 10, ("fake",), lambda emb: FakeProvider(), tmp_path / "ausgabe")
    dense = next(z for z in zeilen if z["variante"] == "dense")
    assert "absatzgenau" not in dense
    assert "rang_absatz" not in dense["fragen"][0]


def test_R13_bericht_zeigt_die_absatzgenaue_tabelle_nur_wenn_es_sie_gibt(tmp_path):
    fundstellen = (fs("c1", "Rottweil Testturm Aufzug", datei="c1"),)
    fragen = ({"frage": "Wo steht der Testturm?", "status": "gefunden", "datei": "c1", "absatz_id": "c1"},)
    ausgabe = tmp_path / "ausgabe"
    lauf(Path("gq"), {}, 1, ("fake",), lambda emb: FakeProvider(), ausgabe, bestand=(fundstellen, fragen))
    text = schreibe_bericht(ausgabe).read_text(encoding="utf-8")
    assert "## Absatzgenau" in text
    assert baue_bericht(({"variante": "dense", "embedding": "fake", "fundstellenzahl": 1,
                          "korpus": "x", "stufe": 1, "fragen": []},)).count("## Absatzgenau") == 0


def test_R12_bericht_zeigt_reranker_variante_automatisch(kleiner_korpus, tmp_path):
    korpus, golden = kleiner_korpus
    ausgabe = tmp_path / "ausgabe"
    reranker_je_modell = {"fake/Reranker-Modell": _FakeRerankerImmerErsterAbsatz()}
    lauf(
        korpus, golden, 10, ("fake-a",), lambda emb: FakeProvider(), ausgabe,
        reranker_je_modell=reranker_je_modell, reranker_k=(8,),
    )
    text = schreibe_bericht(ausgabe).read_text(encoding="utf-8")
    assert f"| dense_rerank_{kurzname('fake/Reranker-Modell')}_k8 | fake-a |" in text

"""A1–A12: Abweisung (trennt ein Signal beantwortbare von unbeantwortbaren Fragen?).

Ohne Ollama, ohne sentence-transformers: FakeProvider aus conftest, FakeReranker hier.
Die Auswertungsfunktionen (ROC-AUC, Schwelle, Überlappung, Verlust) sind rein und werden
an Handbeispielen geprüft — sie sind der Kern des Befunds und dürfen nicht geraten sein.
"""
from __future__ import annotations

import json

import pytest

from dokumentenassistent.abweisung import (
    AbweisungFehler,
    auswertung,
    baue_bericht,
    beste_schwelle,
    faelle_germanquad,
    faelle_malerbetrieb,
    lauf,
    mit_geschwistern,
    punkte,
    roc_auc,
    ueberlappung,
    verlust_bei_spezifitaet,
)
from tests.conftest import FakeProvider, fs


class FakeReranker:
    """Score je Text aus einer Map; unbekannter Text -> 0.0."""

    def __init__(self, score_je_text: dict[str, float]):
        self.score_je_text = score_je_text
        self.aufrufe: list[tuple[str, list[str]]] = []

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        self.aufrufe.append((frage, texte))
        return [self.score_je_text.get(t, 0.0) for t in texte]


# ------------------------------------------------------------------ A1: ROC-AUC


def test_A1_roc_auc_handbeispiel():
    # Vier Paare: (3>2), (3>0), (1<2), (1>0) -> 3 von 4 richtig geordnet.
    assert roc_auc([3.0, 1.0], [2.0, 0.0]) == 0.75


def test_A1_roc_auc_perfekt_und_umgekehrt_und_bindungen():
    assert roc_auc([2.0, 3.0], [0.0, 1.0]) == 1.0
    assert roc_auc([0.0, 1.0], [2.0, 3.0]) == 0.0
    # Bindung zählt als halbes Paar: (1=1)=0.5, (1>0)=1, (1=1)=0.5, (1>0)=1 -> 3/4
    assert roc_auc([1.0, 1.0], [1.0, 0.0]) == 0.75
    # Alles gleich -> Münzwurf
    assert roc_auc([1.0, 1.0], [1.0, 1.0]) == 0.5


def test_A1_roc_auc_ohne_eine_klasse_ist_none():
    assert roc_auc([], [1.0]) is None
    assert roc_auc([1.0], []) is None


# ------------------------------------------------------------- A2: beste Schwelle


def test_A2_beste_schwelle_handbeispiel_trennt_vollstaendig():
    # beantwortbar >= 2, unbeantwortbar <= 1 -> Schwelle 2.0 trennt ohne Fehler.
    e = beste_schwelle([2.0, 3.0, 4.0], [0.0, 1.0])
    assert (e["schwelle"], e["genauigkeit"], e["sensitivitaet"], e["spezifitaet"]) == (2.0, 1.0, 1.0, 1.0)


def test_A2_beste_schwelle_bei_ueberlappung_waehlt_hoechste_genauigkeit():
    # 4 beantwortbar (1,2,3,4), 2 unbeantwortbar (0.5, 2.5) -- die Bereiche ueberlappen.
    # Schwelle 1.0: alle 4 durchgelassen, 0.5 abgewiesen -> 5/6, besser als jede andere.
    e = beste_schwelle([1.0, 2.0, 3.0, 4.0], [0.5, 2.5])
    assert e["genauigkeit"] == pytest.approx(5 / 6, abs=1e-3)
    assert (e["schwelle"], e["sensitivitaet"], e["spezifitaet"]) == (1.0, 1.0, 0.5)


# ----------------------------------------------------------- A3: Überlappung


def test_A3_ueberlappung_meldet_grenzen_und_ob_getrennt_wird():
    getrennt = ueberlappung([0.06, 0.09], [0.008, 0.001])
    assert (getrennt["min_beantwortbar"], getrennt["max_unbeantwortbar"], getrennt["ueberlappt"]) == (
        0.06, 0.008, False,
    )
    assert ueberlappung([0.5062, 0.6], [0.5161, 0.4])["ueberlappt"] is True


# ------------------------------------------- A4: Verlust bei 95 % Spezifität


def test_A4_verlust_bei_spezifitaet_handbeispiel():
    # 20 unbeantwortbare 0..19, 95 % = 19 abgewiesen -> Schwelle muss ueber 18 liegen.
    unbeantwortbar = [float(i) for i in range(20)]
    beantwortbar = [5.0, 10.0, 25.0, 30.0]
    e = verlust_bei_spezifitaet(beantwortbar, unbeantwortbar, ziel=0.95)
    assert e["spezifitaet"] >= 0.95
    assert e["verlorene"] == 2  # 5.0 und 10.0 fallen unter die Schwelle
    assert e["sensitivitaet"] == 0.5


def test_A4_verlust_bei_spezifitaet_kostet_bei_voller_ueberlappung_jede_frage():
    # Jeder unbeantwortbare Wert liegt ueber allen beantwortbaren: 95 % Spezifitaet ist nur
    # zu haben, indem man auch die einzige beantwortbare Frage abweist.
    e = verlust_bei_spezifitaet([1.0], [5.0, 6.0], ziel=0.95)
    assert e["ziel_erreicht"] is True
    assert e["verlorene"] == 1 and e["sensitivitaet"] == 0.0 and e["spezifitaet"] == 1.0


# ------------------------------------------------- A5/A6: Stichprobe GermanQuAD


def _gq_fragen(anzahl: int) -> tuple[dict, ...]:
    return tuple(
        {"frage": f"F{i}", "status": "gefunden", "datei": f"A{i}", "absatz_id": f"A{i}"}
        for i in range(anzahl)
    )


def test_A5_faelle_germanquad_haelften_deterministisch_und_disjunkt():
    faelle = faelle_germanquad(_gq_fragen(20), n=5, seed=42)
    assert len(faelle) == 10
    beantwortbar = [f for f in faelle if f["klasse"] == "beantwortbar"]
    unbeantwortbar = [f for f in faelle if f["klasse"] == "unbeantwortbar"]
    assert len(beantwortbar) == len(unbeantwortbar) == 5
    assert not ({f["frage"] for f in beantwortbar} & {f["frage"] for f in unbeantwortbar})
    assert faelle_germanquad(_gq_fragen(20), n=5, seed=42) == faelle
    assert faelle_germanquad(_gq_fragen(20), n=5, seed=7) != faelle


def test_A6_nur_unbeantwortbare_lassen_genau_ihren_zielabsatz_weg():
    faelle = faelle_germanquad(_gq_fragen(20), n=5, seed=42)
    for f in faelle:
        if f["klasse"] == "beantwortbar":
            assert f["weglassen"] == frozenset()
        else:
            assert f["weglassen"] == frozenset({f["absatz_id"]})


def test_A6_fragen_mit_mehreren_zielabsaetzen_fliegen_raus():
    """Sonst waere eine 'unbeantwortbare' Frage in Wahrheit beantwortbar: man entfernt
    einen ihrer Zielabsaetze, der zweite bleibt im Bestand stehen."""
    fragen = (
        {"frage": "doppelt", "status": "gefunden", "datei": "A1", "absatz_id": "A1"},
        {"frage": "doppelt", "status": "gefunden", "datei": "A2", "absatz_id": "A2"},
        *_gq_fragen(6),
    )
    faelle = faelle_germanquad(fragen, n=3, seed=1)
    assert "doppelt" not in {f["frage"] for f in faelle}
    assert len(faelle) == 6


def test_A6_zu_wenige_brauchbare_fragen_ist_ein_fehler_keine_stille_kuerzung():
    with pytest.raises(AbweisungFehler):
        faelle_germanquad(_gq_fragen(5), n=4, seed=1)


# ------------------------------------------------ A7: Stichprobe malerbetrieb


def test_A7_faelle_malerbetrieb_ergaenzt_je_beantwortbare_frage_einen_weglass_fall():
    fundstellen = (
        fs("a.pdf#S1#A1", "x", datei="a.pdf"),
        fs("a.pdf#S1#A2", "y", datei="a.pdf"),
        fs("b.pdf#S1#A1", "z", datei="b.pdf"),
    )
    gefunden = ({"frage": "Fa", "status": "gefunden", "datei": "a.pdf"},)
    nicht_gefunden = ({"frage": "Fn", "status": "nicht_gefunden"},)
    faelle = faelle_malerbetrieb(gefunden, nicht_gefunden, fundstellen)
    klassen = [(f["frage"], f["klasse"], f["weglassen"]) for f in faelle]
    assert klassen == [
        ("Fa", "beantwortbar", frozenset()),
        ("Fn", "unbeantwortbar", frozenset()),
        ("Fa", "unbeantwortbar", frozenset({"a.pdf#S1#A1", "a.pdf#S1#A2"})),
    ]


# ------------------------------------------------- A7b: Geschwisterabsätze

def test_A7_mit_geschwistern_zaehlt_verbleibende_absaetze_desselben_artikels():
    """Die Kontrollgruppe fuer den Befund: bleibt nach dem Weglassen ein Nachbarabsatz
    desselben Artikels stehen, koennte er die Frage doch beantworten."""
    fundstellen = (
        fs("c1", "Aufzugsanlage\n\nText eins", datei="c1"),
        fs("c2", "Aufzugsanlage\n\nText zwei", datei="c2"),
        fs("c3", "Bundesliga\n\nText drei", datei="c3"),
    )
    faelle = (
        {"frage": "F1", "klasse": "beantwortbar", "weglassen": frozenset(), "absatz_id": "c1"},
        {"frage": "F2", "klasse": "unbeantwortbar", "weglassen": frozenset({"c1"}), "absatz_id": "c1"},
        {"frage": "F3", "klasse": "unbeantwortbar", "weglassen": frozenset({"c3"}), "absatz_id": "c3"},
    )
    assert [f["geschwister"] for f in mit_geschwistern(faelle, fundstellen)] == [0, 1, 0]


# ------------------------------------------------------------------ A8: Punkte


FUNDSTELLEN = (
    fs("a", "Heizung Rechnung Krause", datei="a.pdf"),
    fs("b", "Dach Ziegel Sturm", datei="b.pdf"),
    fs("c", "Kita Sonnenschein Anstrich", datei="c.pdf"),
)


def test_A8_punkte_je_signal_und_fall_und_weglassen_senkt_den_score():
    faelle = (
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar", "weglassen": frozenset(), "absatz_id": "a"},
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "unbeantwortbar", "weglassen": frozenset({"a"}),
         "absatz_id": "a"},
    )
    zeilen = punkte(faelle, FUNDSTELLEN, ("fake",), lambda _e: FakeProvider(), {}, ())
    signale = {z["signal"] for z in zeilen}
    assert signale == {"bm25", "dense@fake", "rrf@fake"}
    je = {(z["signal"], z["klasse"]): z["score"] for z in zeilen}
    assert je[("dense@fake", "beantwortbar")] > je[("dense@fake", "unbeantwortbar")]
    assert je[("bm25", "beantwortbar")] > je[("bm25", "unbeantwortbar")]


def test_A8_reranker_score_ist_das_maximum_ueber_die_top_k_ohne_weggelassene():
    reranker = FakeReranker({"Heizung Rechnung Krause": 9.0, "Dach Ziegel Sturm": 1.0,
                             "Kita Sonnenschein Anstrich": 2.0})
    faelle = (
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar", "weglassen": frozenset(), "absatz_id": "a"},
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "unbeantwortbar", "weglassen": frozenset({"a"}),
         "absatz_id": "a"},
    )
    zeilen = punkte(faelle, FUNDSTELLEN, ("fake",), lambda _e: FakeProvider(),
                    {"BAAI/bge-reranker-v2-m3": reranker}, (3,))
    je = {(z["signal"], z["klasse"]): z["score"] for z in zeilen}
    assert je[("rerank_bge-reranker-v2-m3_k3@fake", "beantwortbar")] == 9.0
    assert je[("rerank_bge-reranker-v2-m3_k3@fake", "unbeantwortbar")] == 2.0


def test_A8_reranker_wird_je_paar_nur_einmal_gefragt():
    """Zwischenspeicher: derselbe (Frage, Absatz) kostet bei k=2 und k=3 nur einen Aufruf.
    Ohne ihn verdoppelt jede weitere k-Stufe die CPU-Zeit."""
    reranker = FakeReranker({"Heizung Rechnung Krause": 9.0, "Dach Ziegel Sturm": 1.0,
                             "Kita Sonnenschein Anstrich": 2.0})
    faelle = ({"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar",
               "weglassen": frozenset(), "absatz_id": "a"},)
    punkte(faelle, FUNDSTELLEN, ("fake",), lambda _e: FakeProvider(),
           {"BAAI/bge-reranker-v2-m3": reranker}, (2, 3))
    bewertet = [t for _f, texte in reranker.aufrufe for t in texte]
    assert sorted(bewertet) == sorted(set(bewertet))


# ------------------------------------------------------- A9: Auswertung/Bericht


def test_A9_auswertung_je_signal_mit_auc_schwelle_und_verlust():
    zeilen = [
        {"signal": "s", "frage": "F1", "klasse": "beantwortbar", "score": 2.0},
        {"signal": "s", "frage": "F2", "klasse": "beantwortbar", "score": 3.0},
        {"signal": "s", "frage": "F3", "klasse": "unbeantwortbar", "score": 0.0},
        {"signal": "s", "frage": "F4", "klasse": "unbeantwortbar", "score": 1.0},
    ]
    (e,) = auswertung(zeilen)
    assert e["signal"] == "s" and e["auc"] == 1.0
    assert e["n_beantwortbar"] == 2 and e["n_unbeantwortbar"] == 2
    assert e["beste_schwelle"]["genauigkeit"] == 1.0
    assert e["ueberlappung"]["ueberlappt"] is False
    assert e["bei_spezifitaet_95"]["verlorene"] == 0


def test_A9_auswertung_sortiert_nach_auc_absteigend():
    zeilen = [
        {"signal": "schwach", "frage": "F1", "klasse": "beantwortbar", "score": 0.0},
        {"signal": "schwach", "frage": "F2", "klasse": "unbeantwortbar", "score": 1.0},
        {"signal": "stark", "frage": "F1", "klasse": "beantwortbar", "score": 1.0},
        {"signal": "stark", "frage": "F2", "klasse": "unbeantwortbar", "score": 0.0},
    ]
    assert [e["signal"] for e in auswertung(zeilen)] == ["stark", "schwach"]


def test_A9_bericht_nennt_jedes_signal_und_die_spalten():
    zeilen = [
        {"signal": "s", "frage": "F1", "klasse": "beantwortbar", "score": 2.0},
        {"signal": "s", "frage": "F2", "klasse": "unbeantwortbar", "score": 0.0},
    ]
    text = baue_bericht(auswertung(zeilen), korpus="testkorpus")
    assert "testkorpus" in text and "| s |" in text
    assert "AUC" in text and "Verlust" in text


# ------------------------------------------------------------------- A10: Lauf


def test_A10_lauf_schreibt_beide_dateien_und_den_bericht(tmp_path):
    faelle = (
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar", "weglassen": frozenset(), "absatz_id": "a"},
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "unbeantwortbar", "weglassen": frozenset({"a"}),
         "absatz_id": "a"},
    )
    ergebnis = lauf(faelle, FUNDSTELLEN, ("fake",), lambda _e: FakeProvider(), tmp_path, korpus="testkorpus")
    scores = [json.loads(z) for z in (tmp_path / "abweisung-scores.jsonl").read_text("utf-8").splitlines()]
    assert len(scores) == 6  # 3 Signale x 2 Faelle
    assert {"signal", "frage", "klasse", "score", "korpus", "datum"} <= set(scores[0])
    signale = [json.loads(z) for z in (tmp_path / "abweisung.jsonl").read_text("utf-8").splitlines()]
    assert {z["signal"] for z in signale} == {"bm25", "dense@fake", "rrf@fake"}
    # Name traegt den Korpus: sonst ueberschreibt der zweite Korpus den Bericht des ersten.
    assert (tmp_path / "abweisung-bericht-testkorpus.md").exists()


def test_A11_abbruch_beim_zweiten_embedding_laesst_das_erste_auf_der_platte(tmp_path):
    """Gemessen 23.09.2026: ein Lauf über 400 Fälle lief 76 Minuten und hinterließ null
    Zeilen, weil erst nach dem letzten Embedding geschrieben wurde."""
    faelle = (
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar", "weglassen": frozenset(), "absatz_id": "a"},
    )

    def provider(embedding: str):
        if embedding == "kaputt":
            raise RuntimeError("Embedding-Dienst weg")
        return FakeProvider()

    with pytest.raises(RuntimeError):
        lauf(faelle, FUNDSTELLEN, ("fake", "kaputt"), provider, tmp_path, korpus="testkorpus")
    scores = [json.loads(z) for z in (tmp_path / "abweisung-scores.jsonl").read_text("utf-8").splitlines()]
    assert {z["signal"] for z in scores} == {"bm25", "dense@fake", "rrf@fake"}


def test_A10_zweiter_korpus_ueberschreibt_den_bericht_des_ersten_nicht(tmp_path):
    faelle = (
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "beantwortbar", "weglassen": frozenset()},
        {"frage": "Heizung Rechnung Krause Anstrich", "klasse": "unbeantwortbar", "weglassen": frozenset({"a"})},
    )
    for korpus in ("korpus eins", "korpus zwei"):
        lauf(faelle, FUNDSTELLEN, ("fake",), lambda _e: FakeProvider(), tmp_path, korpus=korpus)
    assert sorted(p.name for p in tmp_path.glob("abweisung-bericht-*.md")) == [
        "abweisung-bericht-korpus-eins.md", "abweisung-bericht-korpus-zwei.md",
    ]

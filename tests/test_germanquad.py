"""G1–G8: GermanQuAD als zweiter, unabhängiger Prüfstein für das Retrieval-Eval.

Kein Netzzugriff, kein Modell: die Arrow-Dateien werden hier als Mini-Fassung in
`tmp_path` geschrieben (dieselben drei Spaltensätze wie der MTEB-Spiegel), damit die
Tests nicht von `beweise/germanquad/` abhängen.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dokumentenassistent.germanquad import (
    GermanQuadFehler,
    lade,
    ziehe_fragen,
)

pa = pytest.importorskip("pyarrow", reason="pyarrow gehört zur Gruppe dev und zum Extra eval")


def _schreibe_arrow(pfad: Path, spalten: dict[str, list]) -> Path:
    tabelle = pa.table(spalten)
    with pa.ipc.new_stream(pa.OSFile(str(pfad), "wb"), tabelle.schema) as schreiber:
        schreiber.write_table(tabelle)
    return pfad


@pytest.fixture
def mini_gq(tmp_path):
    """3 Korpus-Absätze, 4 Fragen — Absatz c1 wird von zwei Fragen belegt."""
    ordner = tmp_path / "gq"
    ordner.mkdir()
    _schreibe_arrow(
        ordner / "corpus.arrow",
        {"_id": ["c1", "c2", "c3"], "text": ["Aufzug in Rottweil", "Reis in Sichuan", "Tee im Export"]},
    )
    _schreibe_arrow(
        ordner / "queries.arrow",
        {
            "_id": ["q1", "q2", "q3", "q4"],
            "text": ["Wo steht der Testturm?", "Was wächst in Sichuan?", "Wohin geht der Tee?", "Wer baut Aufzüge?"],
        },
    )
    _schreibe_arrow(
        ordner / "qrels.arrow",
        {
            "query-id": ["q1", "q2", "q3", "q4"],
            "corpus-id": ["c1", "c2", "c3", "c1"],
            "score": [1, 1, 1, 1],
        },
    )
    return ordner


# ------------------------------------------------------------------ G1: Fundstellen


def test_G1_lade_macht_je_korpus_absatz_genau_eine_fundstelle(mini_gq):
    fundstellen, _ = lade(mini_gq)
    assert [f.id for f in fundstellen] == ["c1", "c2", "c3"]
    erste = fundstellen[0]
    assert (erste.datei_name, erste.seite, erste.absatz, erste.text) == ("c1", 1, 1, "Aufzug in Rottweil")
    # datei_hash ist gesetzt und je Absatz verschieden — der Index/Eval braucht ihn als Schlüssel
    assert len({f.datei_hash for f in fundstellen}) == 3


# ------------------------------------------------------------------ G2: Fragen


def test_G2_fragen_haben_golden_form_mit_datei_und_absatz_id(mini_gq):
    _, fragen = lade(mini_gq)
    assert fragen[0] == {
        "frage": "Wo steht der Testturm?",
        "status": "gefunden",
        "datei": "c1",
        "absatz_id": "c1",
    }
    assert len(fragen) == 4
    assert {f["status"] for f in fragen} == {"gefunden"}
    # dateigenau und absatzgenau fallen hier zusammen: die Fundstellen-ID IST der Zielabsatz
    assert all(f["datei"] == f["absatz_id"] for f in fragen)


def test_G2b_zwei_fragen_duerfen_denselben_absatz_belegen(mini_gq):
    _, fragen = lade(mini_gq)
    assert [f["frage"] for f in fragen if f["datei"] == "c1"] == [
        "Wo steht der Testturm?",
        "Wer baut Aufzüge?",
    ]


# ------------------------------------------------------- G3: Stichprobe mit Seed


def test_G3_ziehe_fragen_ist_deterministisch_und_begrenzt():
    fragen = tuple({"frage": f"F{i}", "status": "gefunden", "datei": f"c{i}", "absatz_id": f"c{i}"} for i in range(20))
    a = ziehe_fragen(fragen, 5, seed=42)
    b = ziehe_fragen(fragen, 5, seed=42)
    assert a == b
    assert len(a) == 5
    assert all(f in fragen for f in a)  # Teilmenge der Ausgangsfragen, nichts erfunden
    assert ziehe_fragen(fragen, 5, seed=7) != a


def test_G3b_ziehe_fragen_ohne_begrenzung_gibt_alles_unveraendert():
    fragen = tuple({"frage": f"F{i}"} for i in range(3))
    assert ziehe_fragen(fragen, None, seed=42) == fragen
    assert ziehe_fragen(fragen, 99, seed=42) == fragen


def test_G3c_lade_mit_fragen_begrenzung_zieht_deterministisch(mini_gq):
    _, zwei = lade(mini_gq, fragen=2, seed=42)
    _, nochmal = lade(mini_gq, fragen=2, seed=42)
    assert len(zwei) == 2
    assert [f["frage"] for f in zwei] == [f["frage"] for f in nochmal]


# ------------------------------------------------------------ G4: Fehlerbilder


def test_G4_fehlende_datei_nennt_den_pfad(tmp_path):
    with pytest.raises(GermanQuadFehler) as fehler:
        lade(tmp_path / "gibtsnicht")
    assert "corpus.arrow" in str(fehler.value)


def test_G4b_qrel_auf_unbekannten_absatz_ist_ein_fehler(mini_gq):
    _schreibe_arrow(
        mini_gq / "qrels.arrow",
        {"query-id": ["q1"], "corpus-id": ["c99"], "score": [1]},
    )
    with pytest.raises(GermanQuadFehler) as fehler:
        lade(mini_gq)
    assert "c99" in str(fehler.value)


def test_G4c_qrel_auf_unbekannte_frage_ist_ein_fehler(mini_gq):
    _schreibe_arrow(
        mini_gq / "qrels.arrow",
        {"query-id": ["q99"], "corpus-id": ["c1"], "score": [1]},
    )
    with pytest.raises(GermanQuadFehler) as fehler:
        lade(mini_gq)
    assert "q99" in str(fehler.value)


def test_G5_ohne_pyarrow_kommt_eine_klare_meldung(mini_gq, monkeypatch):
    import builtins

    echter_import = builtins.__import__

    def gesperrter_import(name, *args, **kwargs):
        if name == "pyarrow":
            raise ImportError("No module named 'pyarrow'")
        return echter_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", gesperrter_import)
    with pytest.raises(GermanQuadFehler) as fehler:
        lade(mini_gq)
    assert "pyarrow" in str(fehler.value)
    assert "uv sync --extra eval" in str(fehler.value)

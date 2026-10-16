"""Modellwahl: modelle.yaml zeilenweise umschreiben, Kommentare bleiben (10.10.2026)."""

from dokumentenassistent.modellwahl import schreibe


def test_wert_wird_ersetzt_und_kommentar_bleibt(tmp_path):
    p = tmp_path / "modelle.yaml"
    p.write_text("# Messkommentar\nllm: alt     # schneller: x\nembedding: e\n")
    schreibe(p, {"llm": "neu"})
    assert p.read_text() == "# Messkommentar\nllm: neu     # schneller: x\nembedding: e\n"


def test_fehlender_schluessel_kommt_nach_llm(tmp_path):
    p = tmp_path / "modelle.yaml"
    p.write_text("llm: a\nembedding: e\n")
    schreibe(p, {"llm_suche": "b"})
    assert p.read_text() == "llm: a\nllm_suche: b\nembedding: e\n"

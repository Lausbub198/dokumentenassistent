from dokumentenassistent import laufzeit_vergleich as lv


def test_prompts_kurz_und_lang_aus_dem_bestand(tmp_path):
    (tmp_path / "a.txt").write_text(" ".join(f"w{i}" for i in range(500)), encoding="utf-8")
    p = lv.prompts(tmp_path, kurz_woerter=10, lang_woerter=300)
    assert len(p["kurz"].split()) < len(p["lang"].split()) and p["lang"].startswith(lv.AUFTRAG)


def test_miss_misst_vier_arten_und_waermt_vorher_auf():
    aufrufe = []

    class P:
        def generate_text(self, prompt): aufrufe.append("text"); return "x"
        def generate_json(self, prompt, schema): aufrufe.append("json"); return {}
    r = lv.miss(P(), {"kurz": "k", "lang": "l"}, wiederholungen=2)
    assert set(r) == {"kurz_text", "lang_text", "kurz_json", "lang_json"} and len(aufrufe) == 1 + 4 * 2


def test_prompts_ueberspringt_macos_hilfsdateien(tmp_path):
    (tmp_path / "a.txt").write_text("wort " * 50, encoding="utf-8")
    (tmp_path / "._a.txt").write_bytes(b"\x00\x05\x16\x07\xb0\xff")
    assert "wort" in lv.prompts(tmp_path, kurz_woerter=5, lang_woerter=20)["kurz"]

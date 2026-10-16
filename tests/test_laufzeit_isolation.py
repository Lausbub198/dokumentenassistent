from dokumentenassistent import laufzeit_isolation as li


def test_jede_wiederholung_und_art_bekommt_einen_eigenen_ausschnitt():
    alle = [f"w{i}" for i in range(60000)]
    ps = {li.prompt(alle, n, w, art) for n in li.LAENGEN.values() for w in range(3) for art in ("text", "json")}
    assert len(ps) == 12
    anfaenge = {p[len(li.AUFTRAG):len(li.AUFTRAG) + 20] for p in ps}
    assert len(anfaenge) == 12  # kein gemeinsamer Anfang, also kein Prompt-Cache-Treffer


def test_miss_zaehlt_fehler_und_json_ohne_abbruch():
    def aufruf(text, schema):
        if schema is not None and "w3" in text[:200]:
            raise RuntimeError("kaputt")
        return {"prompt_tokens": 10, "prefill_s": 1.0, "prefill_tps": 10.0, "gen_tokens": 5, "gen_tps": 50.0,
                "gesamt_s": 1.2, "antwort": '{"thema": "x", "jahr": "1999"}' if schema else "Text"}
    r = li.miss(aufruf, [f"w{i}" for i in range(60000)], wiederholungen=2)
    assert set(r) == {"kurz_text", "kurz_json", "lang_text", "lang_json"}
    assert r["kurz_text"]["prefill_tps"] == 10.0 and r["kurz_json"]["json_ok"] == r["kurz_json"]["n_ok"]


def test_json_gueltig():
    assert li.json_gueltig('{"a": 1}') and not li.json_gueltig("") and not li.json_gueltig("[1]")

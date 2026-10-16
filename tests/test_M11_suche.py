import pytest

import dokumentenassistent.suche as suche_modul
from dokumentenassistent.suche import SCHWELLE, bm25_rang, dense_rang, rrf, suche
from tests.conftest import fs, FakeProvider
from dokumentenassistent.typen import Vorschlag


def test_elternseiten_lehnen_mehrseiten_fundstellen_ab_bevor_modell_laeuft():
    from dataclasses import replace
    from dokumentenassistent.typen import SeitenSpanne

    grenze = F_HEIZ.text.index(" Wohnung")
    f = replace(F_HEIZ, spannen=(SeitenSpanne(1, 0, grenze),
                                 SeitenSpanne(2, grenze, len(F_HEIZ.text))))
    provider = FakeProvider()
    with pytest.raises(ValueError, match="Mehrseiten"):
        suche(FRAGE_HEIZ, ((f, provider.embed([f.text])[0]),), provider,
              schwelle=0.0, eltern_seiten=1)
    assert not any(art == "text" for art, _ in provider.aufrufe)

F_HEIZ = fs("Rechnung (2).pdf#S1#A3", "Rechnungsbetrag Reparatur Heizung Wohnung Nord 1.240,00 EUR", absatz=3)
F_MIET = fs("Dokument1.pdf#S1#A2", "Mietvertrag Wohnung Nord Kaltmiete 780,00 EUR", datei="Dokument1.pdf", absatz=2)
F_LOHN = fs("Lohnsteuer.pdf#S1#A1", "Lohnsteuerbescheinigung Bruttoarbeitslohn 52.000 EUR", datei="Lohnsteuer.pdf")
FSET = (F_HEIZ, F_MIET, F_LOHN)
# Seit 21.09. entscheidet allein der Kosinus (SCHWELLE 0.49, kein BM25/RRF). Der Bag-of-Words-FakeProvider
# liefert für das Einzelwort „Heizung" gegen den 8-Wort-Absatz nur 1/sqrt(8) = 0.333 -> abgewiesen.
# Vier Treffer-Wörter ergeben 4/sqrt(4*8) = 0.667 -> F_HEIZ vorn, F_MIET (0.378) dahinter, F_LOHN fehlt.
FRAGE_HEIZ = "Reparatur Heizung Wohnung Nord"


def _paare():
    prov = FakeProvider(); vecs = prov.embed([f.text for f in FSET])
    return tuple(zip(FSET, vecs))


def test_M11_G1_bm25_findet_exakten_begriff():
    assert bm25_rang("Heizung", FSET)[0][0] == F_HEIZ.id


def test_M11_G2_dense_findet_naechsten_absatz():
    prov = FakeProvider(); q = prov.embed(["Kaltmiete Wohnung Nord"])[0]
    assert dense_rang(q, _paare())[0][0] == F_MIET.id


def test_M11_G3_rrf_belohnt_treffer_in_beiden_listen():
    a = (("x", 9.0), ("y", 8.0)); b = (("y", 0.9), ("z", 0.8))
    assert rrf((a, b))[0][0] == "y"


def test_M11_G4_antwort_mit_gueltigem_zitat_ist_gefunden():
    prov = FakeProvider(text_antworten=["Die Heizungsreparatur kostete 1.240,00 EUR [Rechnung (2).pdf#S1#A3]."])
    a = suche("Rechnungsbetrag Reparatur Heizung Wohnung Nord?", _paare(), prov)
    # Plan-Korrektur 19.09.: vorher „Heizungsreparatur" — als Kompositum weder für BM25 noch für den Bag-of-Words-FakeProvider ein Treffer
    # 21.09.: „Was kostete die Reparatur der Heizung?" hat beim FakeProvider Kosinus 0.272 < SCHWELLE; fünf Treffer-Wörter -> 0.79
    assert (a.status, a.karten[0].fundstelle.id) == ("gefunden", F_HEIZ.id)


def test_M11_G5_belegkarte_traegt_datei_und_seite():
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    k = suche(FRAGE_HEIZ, _paare(), prov).karten[0]
    assert (k.fundstelle.datei_name, k.fundstelle.seite) == ("Rechnung (2).pdf", 1)


def test_M11_G6_nur_top_n_absaetze_stehen_im_prompt():
    prov = FakeProvider(text_antworten=["x [Rechnung (2).pdf#S1#A3]"])
    suche(FRAGE_HEIZ, _paare(), prov, top_n=1)
    assert F_LOHN.text not in prov.aufrufe[0][1]


def test_M11_G7_offener_konflikt_ergibt_widerspruechlich():
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    assert suche(FRAGE_HEIZ, _paare(), prov, offene_konflikt_hashes=frozenset({F_HEIZ.datei_hash})).status == "widerspruechlich"


def test_M11_B1_frage_ohne_treffer_ergibt_nicht_gefunden_ohne_modellaufruf():
    prov = FakeProvider(text_antworten=["sollte nie kommen"])
    a = suche("Kaufvertrag Auto Kilometerstand", _paare(), prov)
    assert (a.status, prov.aufrufe) == ("nicht_gefunden", [])


def test_M11_B8_top_kosinus_unter_schwelle_ergibt_nicht_gefunden_ohne_modellaufruf():
    # „Heizung" trifft F_HEIZ (Kosinus 0.333 > 0), liegt aber unter SCHWELLE 0.49 -> kein Modellaufruf
    prov = FakeProvider(text_antworten=["sollte nie kommen"])
    assert SCHWELLE == 0.49
    a = suche("Heizung", _paare(), prov)
    assert (a.status, prov.aufrufe) == ("nicht_gefunden", [])
    # dieselbe Frage mit gesenkter Schwelle erreicht das Modell -> die Schwelle war der Grund
    prov2 = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    assert suche("Heizung", _paare(), prov2, schwelle=0.3).status == "gefunden"


def test_M11_B9_suche_ruft_kein_bm25_und_keine_rrf(monkeypatch):
    monkeypatch.setattr(suche_modul, "bm25_rang", lambda *a, **k: pytest.fail("bm25_rang im Suchpfad"))
    monkeypatch.setattr(suche_modul, "rrf", lambda *a, **k: pytest.fail("rrf im Suchpfad"))
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    assert suche(FRAGE_HEIZ, _paare(), prov).status == "gefunden"


def test_M11_B2_antwort_ohne_zitat_ergibt_nicht_gefunden():
    prov = FakeProvider(text_antworten=["Die Heizung kostete 1.240 EUR."])
    assert suche(FRAGE_HEIZ, _paare(), prov).status == "nicht_gefunden"


def test_M11_B3_erfundene_id_wird_verworfen():
    prov = FakeProvider(text_antworten=["1.240 EUR [Rechnung (2).pdf#S4#A9]"])
    assert suche(FRAGE_HEIZ, _paare(), prov).status == "nicht_gefunden"


def test_M11_B4_id_ausserhalb_top_n_wird_verworfen():
    prov = FakeProvider(text_antworten=["52.000 EUR [Lohnsteuer.pdf#S1#A1]"])
    assert suche(FRAGE_HEIZ, _paare(), prov, top_n=1).karten == ()


def test_M11_B5_leerer_bestand_ergibt_nicht_gefunden():
    assert suche(FRAGE_HEIZ, (), FakeProvider()).status == "nicht_gefunden"


def test_M11_B6_leere_frage_ergibt_nicht_gefunden():
    assert suche("   ", _paare(), FakeProvider()).status == "nicht_gefunden"


def test_M11_G8_bm25_trifft_auch_bei_zwei_absaetzen():
    # BM25Okapi lieferte hier 0 (negative IDF bei kleinem Bestand) — Befund e2e 19.09.
    assert bm25_rang("Heizung", (F_HEIZ, F_MIET))[0][0] == F_HEIZ.id


def test_M11_B7_absatz_ohne_fragebegriff_hat_keinen_bm25_treffer():
    assert [i for i, _ in bm25_rang("Heizung", FSET)] == [F_HEIZ.id]


# ------------------------------------------------------------------ Reranker (R12)
# Kein sentence-transformers in den Tests: der Cross-Encoder wird durch einen
# deterministischen Fake ersetzt, genau wie in tests/test_retrieval_reranker.py.


class FakeReranker:
    def __init__(self, score_je_text: dict[str, float]):
        self.score_je_text = score_je_text
        self.aufrufe: list[tuple[str, list[str]]] = []

    def bewerte(self, frage: str, texte: list[str]) -> list[float]:
        self.aufrufe.append((frage, texte))
        return [self.score_je_text.get(t, 0.0) for t in texte]


def test_M11_G9_reranker_sortiert_die_rangliste_um():
    # dense hat F_HEIZ (0.667) vor F_MIET (0.378); der Reranker sieht es umgekehrt.
    reranker = FakeReranker({F_HEIZ.text: 0.1, F_MIET.text: 0.9})
    prov = FakeProvider(text_antworten=["780,00 EUR [Dokument1.pdf#S1#A2]"])
    a = suche(FRAGE_HEIZ, _paare(), prov, reranker=reranker)
    assert (a.status, a.karten[0].fundstelle.id) == ("gefunden", F_MIET.id)
    # Der Prompt führt den umsortierten Absatz zuerst — der Reranker wirkt vor dem Modellaufruf.
    prompt = prov.aufrufe[0][1]
    assert prompt.index(F_MIET.text) < prompt.index(F_HEIZ.text)


def test_M11_G10_ohne_reranker_bleibt_alles_wie_bisher():
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    ohne = suche(FRAGE_HEIZ, _paare(), prov)
    prov2 = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    explizit_none = suche(FRAGE_HEIZ, _paare(), prov2, reranker=None)
    assert ohne == explizit_none and ohne.karten[0].fundstelle.id == F_HEIZ.id


def test_M11_G11_rerank_k_begrenzt_die_texte_die_der_reranker_sieht():
    reranker = FakeReranker({F_HEIZ.text: 0.1})
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    suche(FRAGE_HEIZ, _paare(), prov, reranker=reranker, rerank_k=1)
    assert reranker.aufrufe == [(FRAGE_HEIZ, [F_HEIZ.text])]


def test_M11_G16_metadatenbonus_ordnet_vor_dem_reranker_und_entfernt_nichts():
    reranker = FakeReranker({F_HEIZ.text: 0.1, F_MIET.text: 0.9})
    prov = FakeProvider(text_antworten=[f"780,00 EUR [{F_MIET.id}]"])
    metadatum = Vorschlag(
        datei_hash=F_MIET.datei_hash,
        datei_name=F_MIET.datei_name,
        kategorie=None,
        typ="Reparatur Heizung Wohnung Nord",
        felder=(),
        zielname=None,
        status="unklar",
    )

    antwort = suche(
        FRAGE_HEIZ,
        _paare(),
        prov,
        reranker=reranker,
        vorschlaege_je_hash={F_MIET.datei_hash: metadatum},
        metadatenbonus=0.4,
    )

    assert antwort.karten[0].fundstelle.id == F_MIET.id
    # Alle zwei Kandidaten mit positivem Dense-Score bleiben erhalten.
    assert reranker.aufrufe[0][1] == [F_MIET.text, F_HEIZ.text]


def test_M11_B11_metadatenbonus_kann_kosinus_schwelle_nicht_uebergehen():
    reranker = FakeReranker({F_HEIZ.text: 10.0})
    prov = FakeProvider(text_antworten=[f"1.240,00 EUR [{F_HEIZ.id}]"])
    metadatum = Vorschlag(
        datei_hash=F_HEIZ.datei_hash,
        datei_name=F_HEIZ.datei_name,
        kategorie=None,
        typ="Heizung",
        felder=(),
        zielname=None,
        status="unklar",
    )

    antwort = suche(
        "Heizung",
        _paare(),
        prov,
        reranker=reranker,
        vorschlaege_je_hash={F_HEIZ.datei_hash: metadatum},
        metadatenbonus=10.0,
    )

    assert antwort.status == "nicht_gefunden"
    assert reranker.aufrufe == []
    assert prov.aufrufe == []


def test_M11_B10_schwelle_greift_vor_dem_reranker_kein_aufruf():
    """Die Schwelle prüft den Kosinus, nicht den Cross-Encoder-Score: „Heizung" liegt mit 0.333
    unter SCHWELLE 0.49 und wird abgewiesen, ohne dass der Reranker überhaupt läuft."""
    reranker = FakeReranker({F_HEIZ.text: 9.9})
    prov = FakeProvider(text_antworten=["sollte nie kommen"])
    a = suche("Heizung", _paare(), prov, reranker=reranker)
    assert (a.status, reranker.aufrufe, prov.aufrufe) == ("nicht_gefunden", [], [])


# --- Parent-Document-Retrieval (25.09.2026): klein einbetten, gross ausliefern ----------

# Drei Absaetze einer Seite: der Suchtreffer sitzt im ersten, die ANTWORT im zweiten.
# Genau die Lage, an der das heutige Verfahren scheitert -- gemessen am echten Bestand:
# 9 von 85 Antworten existieren in keinem einzelnen Stueck.
E_TREFFER = fs("Auszug.pdf#S2#A1", "Kontoauszug Dezember 2024 Sparkasse", datei="Auszug.pdf", seite=2, absatz=1)
E_ANTWORT = fs("Auszug.pdf#S2#A2", "27.11.2024 Sylwia Cieslak -120,00 EUR", datei="Auszug.pdf", seite=2, absatz=2)
E_REST    = fs("Auszug.pdf#S2#A3", "Uebertrag auf neue Seite", datei="Auszug.pdf", seite=2, absatz=3)
E_ANDERE  = fs("Auszug.pdf#S3#A1", "Kontoauszug Januar 2025 Sparkasse", datei="Auszug.pdf", seite=3, absatz=1)
ESET = (E_TREFFER, E_ANTWORT, E_REST, E_ANDERE)


def _eltern_paare():
    prov = FakeProvider(); return tuple(zip(ESET, prov.embed([f.text for f in ESET])))


def test_M11_G12_eltern_liefern_die_ganze_seite_statt_nur_des_treffers():
    """Der Treffer ist der Zeiger, ausgeliefert wird seine Seite. Damit muss die
    Antwort nicht mehr IM gefundenen Stueck stehen, nur in seiner Naehe."""
    prov = FakeProvider(text_antworten=["Am 27.11.2024 [Auszug.pdf#S2#A1]."])
    antwort = suche("Kontoauszug Dezember 2024 Sparkasse", _eltern_paare(), prov,
                    top_n=1, schwelle=0.0, eltern_seiten=1)
    assert antwort.status == "gefunden"
    karte = antwort.karten[0]
    # Der Beleg traegt die ganze Seite -- inklusive des Absatzes mit der Antwort.
    assert "Sylwia Cieslak -120,00 EUR" in karte.wortlaut
    assert "Uebertrag auf neue Seite" in karte.wortlaut
    # Seite 3 gehoert nicht dazu.
    assert "Januar 2025" not in karte.wortlaut
    assert karte.fundstelle.seite == 2


def test_M11_G13_eltern_seiten_begrenzt_die_zahl_der_seiten():
    prov = FakeProvider(text_antworten=["Steht in [Auszug.pdf#S2#A1]."])
    antwort = suche("Kontoauszug Sparkasse", _eltern_paare(), prov,
                    top_n=4, schwelle=0.0, eltern_seiten=1)
    assert len(antwort.karten) == 1  # nur eine Seite im Prompt, also nur eine zitierbar


def test_M11_G14_ohne_eltern_seiten_bleibt_alles_wie_bisher():
    """Standard 0 = Verhalten vor dem 25.09.2026; der Beleg ist genau der Treffer."""
    prov = FakeProvider(text_antworten=["Steht in [Auszug.pdf#S2#A1]."])
    antwort = suche("Kontoauszug Dezember 2024 Sparkasse", _eltern_paare(), prov,
                    top_n=1, schwelle=0.0)
    assert antwort.karten[0].wortlaut == E_TREFFER.text


def test_M11_G15_suchtext_steuert_die_einbettung_frage_bleibt_fuer_reranker_und_prompt():
    """HyDE: eingebettet wird `suchtext`, aber Reranker und Prompt sehen die echte Frage.
    Sonst koennte eine erfundene Zahl in der Hypothese das Ranking oder die Antwort
    verfaelschen -- sie darf nur die Vorauswahl lenken."""
    prov = FakeProvider(text_antworten=[f"Kaltmiete [{F_MIET.id}]."])
    # Die FRAGE allein ("Reparatur Heizung Wohnung Nord") traefe F_HEIZ (siehe G_HEIZ oben).
    # Der SUCHTEXT zielt stattdessen auf Kaltmiete -> F_MIET muss gefunden werden.
    antwort = suche("Reparatur Heizung Wohnung Nord", _paare(), prov, top_n=1, schwelle=0.0,
                    suchtext="Kaltmiete Wohnung Nord")
    assert antwort.karten[0].fundstelle.id == F_MIET.id
    # generate_text bekam die ECHTE Frage im Prompt, nicht den Suchtext.
    assert "Reparatur Heizung Wohnung Nord" in prov.aufrufe[-1][1]
    assert "Kaltmiete Wohnung Nord" not in prov.aufrufe[-1][1].split("Frage:")[-1]


def test_M11_B11_ohne_suchtext_bleibt_alles_wie_bisher():
    prov = FakeProvider(text_antworten=[f"Heizung [{F_HEIZ.id}]."])
    a = suche(FRAGE_HEIZ, _paare(), prov, top_n=1, schwelle=0.0)
    assert a.karten[0].fundstelle.id == F_HEIZ.id


# ---------------------------------------------------------------- Phase D: Kaskade (02.10.2026)

def test_M11_G17_dynamisch_gibt_nur_absaetze_nahe_am_besten_score_weiter():
    reranker = FakeReranker({F_HEIZ.text: 0.9, F_MIET.text: 0.3})  # 0,3 < 0,5 × 0,9
    prov = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    a = suche(FRAGE_HEIZ, _paare(), prov, reranker=reranker, top_n=20, kontextauswahl="dynamisch")
    prompt = prov.aufrufe[0][1]
    assert a.status == "gefunden" and F_HEIZ.text in prompt and F_MIET.text not in prompt


def test_M11_G18_kaskade_fasst_nur_ohne_zitat_mit_top_n_nach():
    reranker = FakeReranker({F_HEIZ.text: 0.9, F_MIET.text: 0.3})
    prov = FakeProvider(text_antworten=["nicht gefunden", "780,00 EUR [Dokument1.pdf#S1#A2]"])
    a = suche(FRAGE_HEIZ, _paare(), prov, reranker=reranker, top_n=20, kontextauswahl="dynamisch", kaskade=True)
    assert (a.status, a.karten[0].fundstelle.id) == ("gefunden", F_MIET.id)
    assert F_MIET.text not in prov.aufrufe[0][1] and F_MIET.text in prov.aufrufe[1][1]
    prov2 = FakeProvider(text_antworten=["1.240,00 EUR [Rechnung (2).pdf#S1#A3]"])
    suche(FRAGE_HEIZ, _paare(), prov2, reranker=reranker, top_n=20, kontextauswahl="dynamisch", kaskade=True)
    assert len(prov2.aufrufe) == 1  # Treffer in Stufe 1: kein Nachgriff


def test_M11_G19_stufe2_streng_und_pruefung_wirken_nur_im_nachgriff():
    reranker = FakeReranker({F_HEIZ.text: 0.9, F_MIET.text: 0.3})
    kw = dict(reranker=reranker, top_n=20, kontextauswahl="dynamisch", kaskade=True)
    prov = FakeProvider(text_antworten=["nicht gefunden", "nicht gefunden"])
    suche(FRAGE_HEIZ, _paare(), prov, kaskade_stufe2="streng", **kw)
    assert "genau den erfragten Vorgang" not in prov.aufrufe[0][1]
    assert "genau den erfragten Vorgang" in prov.aufrufe[1][1]
    nein = FakeProvider(text_antworten=["nicht gefunden", "780,00 EUR [Dokument1.pdf#S1#A2]"],
                        json_antworten=[{"belegt": "nein"}])
    assert suche(FRAGE_HEIZ, _paare(), nein, kaskade_stufe2="pruefung", **kw).status == "nicht_gefunden"
    ja = FakeProvider(text_antworten=["nicht gefunden", "780,00 EUR [Dokument1.pdf#S1#A2]"],
                      json_antworten=[{"belegt": "ja"}])
    assert suche(FRAGE_HEIZ, _paare(), ja, kaskade_stufe2="pruefung", **kw).status == "gefunden"


def test_M11_B12_ungueltige_kaskaden_einstellungen():
    with pytest.raises(ValueError, match="Reranker"):
        suche(FRAGE_HEIZ, _paare(), FakeProvider(), kontextauswahl="dynamisch")
    with pytest.raises(ValueError, match="unbekannt"):
        suche(FRAGE_HEIZ, _paare(), FakeProvider(), kaskade_stufe2="irgendwas")


def test_M11_G20_stufe2_texte_gleich_wie_in_der_messung():
    from dokumentenassistent import antwortstufe
    assert suche_modul._STUFE2_STRENG == antwortstufe.STUFE2_STRENG
    assert suche_modul._PRUEF_ANWEISUNG == antwortstufe.PRUEF_ANWEISUNG
    assert suche_modul._PRUEF_SCHEMA == antwortstufe.PRUEF_SCHEMA

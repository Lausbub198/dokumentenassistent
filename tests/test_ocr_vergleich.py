"""OCR-Vergleich: reine Funktionen (Normalisierung, Distanz, CER/WER, Zahlentreue,
Stichprobe) an synthetischen Mini-Texten. Kein echter Korpus, kein Tesseract, kein Vision."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from dokumentenassistent.ocr_bericht import gemeinsame_seiten
from dokumentenassistent.ocr_vergleich import (
    ENGINES,
    bereits_gemessen,
    PDFTOPPM,
    OcrVergleichFehler,
    cer,
    datumsangaben,
    levenshtein,
    main,
    normalisiere,
    paarweise,
    pruefe_engines,
    sammle_korpus,
    schaetze_neigung,
    stichprobe,
    tragfaehige_seiten,
    uebernommene_zeilen,
    vorverarbeite,
    wer,
    wortmengen_kennzahlen,
    zahlen,
    zahlentreue,
    zeichen_ngramm_kennzahlen,
)

# ------------------------------------------------------------- Normalisierung


def test_normalisiere_faltet_leerraum_und_zeilenumbrueche():
    assert normalisiere("Miete\n\n  je   Monat\t900") == "Miete je Monat 900"


def test_normalisiere_vereinheitlicht_anfuehrungszeichen_und_striche():
    assert normalisiere("„Vertrag“ – ‚Anlage‘") == '"Vertrag" - \'Anlage\''


def test_normalisiere_loest_ligaturen_auf():
    assert normalisiere("Pﬂicht und Eﬃzienz") == "Pflicht und Effizienz"


def test_normalisiere_trifft_beide_seiten_gleich():
    """Die Normalisierung ist auf Referenz und OCR dieselbe Funktion — gleiche Eingabe,
    gleiche Ausgabe, unabhaengig davon, wer den Text erzeugt hat."""
    roh = "Betrag: 1.240,00 EUR"
    assert normalisiere(roh) == normalisiere(roh)
    assert normalisiere(roh) == "Betrag: 1.240,00 EUR"


def test_normalisiere_ist_idempotent():
    text = normalisiere("Zeile 1\nZeile  2")
    assert normalisiere(text) == text


# ------------------------------------------------------------------- Distanz


@pytest.mark.parametrize(
    ("a", "b", "erwartet"),
    [
        ("", "", 0),
        ("abc", "abc", 0),
        ("abc", "", 3),
        ("", "abc", 3),
        ("kitten", "sitting", 3),
        ("Miete", "Mlete", 1),
    ],
)
def test_levenshtein(a, b, erwartet):
    assert levenshtein(a, b) == erwartet


def test_levenshtein_auf_wortlisten():
    assert levenshtein(["a", "b", "c"], ["a", "x", "c"]) == 1


def test_levenshtein_ist_symmetrisch():
    assert levenshtein("Nebenkosten", "Nebenkoslen") == levenshtein("Nebenkoslen", "Nebenkosten")


# ------------------------------------------------------------------ CER / WER


def test_cer_null_bei_gleichem_text():
    assert cer("Die Miete betraegt 900 Euro", "Die Miete betraegt 900 Euro") == 0.0


def test_cer_ein_zeichen_falsch():
    assert cer("abcd", "abcx") == pytest.approx(0.25)


def test_cer_leere_referenz_ist_none():
    assert cer("", "irgendwas") is None


def test_cer_normalisiert_vorher():
    assert cer("Miete\n\n900", "Miete 900") == 0.0


def test_wer_ein_wort_von_vier():
    assert wer("a b c d", "a b c x") == pytest.approx(0.25)


def test_wer_leere_ocr_ist_eins():
    assert wer("a b c d", "") == pytest.approx(1.0)


# ----------------------------------- Reihenfolge-unabhaengige Kennzahlen (Wort/Trigramm)


def test_wortmengen_gleicher_text_ist_eins():
    kennzahl = wortmengen_kennzahlen("Die Miete betraegt 900 Euro", "Die Miete betraegt 900 Euro")
    assert kennzahl["wort_praezision"] == 1.0
    assert kennzahl["wort_ausbeute"] == 1.0
    assert kennzahl["wort_f1"] == 1.0


def test_wortmengen_gleiche_woerter_andere_reihenfolge_ist_eins_waehrend_cer_hoch_ist():
    """Der Kern des Befunds: mehrspaltige Seiten und Tabellen liefern dieselben Woerter in
    anderer Folge. Die Editierdistanz zaehlt das als Fehler, die Wortmenge nicht."""
    referenz = "Mietzins monatlich 900 Euro Nebenkosten pauschal 180 Euro Kaution 1800 Euro"
    umgestellt = "Kaution 1800 Euro Nebenkosten pauschal 180 Euro Mietzins monatlich 900 Euro"
    assert wortmengen_kennzahlen(referenz, umgestellt)["wort_f1"] == 1.0
    assert cer(referenz, umgestellt) > 0.3


def test_wortmengen_ist_multimenge_nicht_menge():
    """Ein dreimal genanntes Wort muss dreimal gelesen werden — sonst verschwinden
    Wiederholungen (und damit wiederholte Betraege) aus der Rechnung."""
    kennzahl = wortmengen_kennzahlen("900 900 900", "900 900")
    assert kennzahl["wort_praezision"] == pytest.approx(1.0)
    assert kennzahl["wort_ausbeute"] == pytest.approx(2 / 3)
    assert kennzahl["wort_f1"] == pytest.approx(0.8)


def test_wortmengen_fehlendes_wort_senkt_ausbeute_nicht_praezision():
    kennzahl = wortmengen_kennzahlen("a b c d", "a b c")
    assert kennzahl["wort_praezision"] == pytest.approx(1.0)
    assert kennzahl["wort_ausbeute"] == pytest.approx(0.75)


def test_wortmengen_zusaetzliches_wort_senkt_praezision_nicht_ausbeute():
    kennzahl = wortmengen_kennzahlen("a b c", "a b c x")
    assert kennzahl["wort_praezision"] == pytest.approx(0.75)
    assert kennzahl["wort_ausbeute"] == pytest.approx(1.0)


def test_wortmengen_nutzt_dieselbe_normalisierung_wie_cer():
    assert wortmengen_kennzahlen("Miete\n\n900", "Miete 900")["wort_f1"] == 1.0


def test_wortmengen_leere_referenz_ist_none():
    assert wortmengen_kennzahlen("", "irgendwas")["wort_f1"] is None


def test_wortmengen_leere_ocr_ist_null():
    kennzahl = wortmengen_kennzahlen("a b c", "")
    assert kennzahl["wort_praezision"] == 0.0
    assert kennzahl["wort_ausbeute"] == 0.0
    assert kennzahl["wort_f1"] == 0.0


def test_ngramm_faengt_teilwortfehler_den_die_wortmenge_verwirft():
    """'Rechnunq' statt 'Rechnung': die Wortmenge wirft das Wort komplett weg (F1 0),
    die Trigramme behalten den groessten Teil."""
    assert wortmengen_kennzahlen("Rechnung", "Rechnunq")["wort_f1"] == 0.0
    assert zeichen_ngramm_kennzahlen("Rechnung", "Rechnunq")["ngramm_f1"] > 0.5


def test_ngramm_gleicher_text_ist_eins():
    assert zeichen_ngramm_kennzahlen("Nebenkosten 180", "Nebenkosten 180")["ngramm_f1"] == 1.0


def test_ngramm_ist_multimenge():
    """'aaaa' hat zweimal das Trigramm 'aaa' — 'aaa' nur einmal."""
    kennzahl = zeichen_ngramm_kennzahlen("aaaa", "aaa", n=3)
    assert kennzahl["ngramm_ausbeute"] == pytest.approx(0.5)
    assert kennzahl["ngramm_praezision"] == pytest.approx(1.0)


def test_ngramm_nutzt_dieselbe_normalisierung_wie_cer():
    assert zeichen_ngramm_kennzahlen("Miete\n\n900", "Miete 900")["ngramm_f1"] == 1.0


def test_ngramm_reihenfolge_unabhaengig_bei_bloecken():
    referenz = "Mietzins monatlich 900 Euro und Kaution 1800 Euro"
    umgestellt = "Kaution 1800 Euro und Mietzins monatlich 900 Euro"
    assert zeichen_ngramm_kennzahlen(referenz, umgestellt)["ngramm_f1"] > 0.9
    assert cer(referenz, umgestellt) > 0.3


def test_ngramm_zu_kurze_referenz_ist_none():
    assert zeichen_ngramm_kennzahlen("ab", "ab", n=3)["ngramm_f1"] is None


# -------------------------------------------------------- Zahlen und Datumsangaben


def test_zahlen_erkennt_deutsche_tausender_und_dezimaltrennung():
    assert zahlen("Kaution 1.240,00 EUR, Miete 900 EUR, Faktor 0,5") == ("1240.00", "900", "0.5")


def test_zahlen_vergleicht_wertgleich_trotz_schreibweise():
    assert zahlen("1.240,00") == zahlen("1240,00")


def test_zahlen_nimmt_datumsangaben_nicht_auseinander():
    assert zahlen("Frist 14.08.2026 und Betrag 300") == ("300",)


def test_datumsangaben_punktform_und_iso():
    assert datumsangaben("am 14.08.2026 bzw. 2026-08-14 und 1.9.26") == (
        "2026-08-14",
        "2026-08-14",
        "2026-09-01",
    )


def test_datumsangaben_ignoriert_unmoegliche_werte():
    assert datumsangaben("Position 32.13.2026") == ()


def test_zahlentreue_zaehlt_getroffen_verfehlt_erfunden():
    ergebnis = zahlentreue("Miete 900 EUR, Kaution 1.800,00 EUR", "Miete 900 EUR, Kaution 1.300,00 EUR")
    assert ergebnis["zahlen_gefunden"] == 1
    assert ergebnis["zahlen_verfehlt"] == 1
    assert ergebnis["zahlen_erfunden"] == 1


def test_zahlentreue_erkennt_fehlende_zahl_ohne_erfindung():
    ergebnis = zahlentreue("900 und 300", "900")
    assert (ergebnis["zahlen_gefunden"], ergebnis["zahlen_verfehlt"], ergebnis["zahlen_erfunden"]) == (1, 1, 0)


def test_zahlentreue_zaehlt_datumsangaben_mit():
    ergebnis = zahlentreue("Frist 14.08.2026", "Frist 14.03.2026")
    assert ergebnis["daten_verfehlt"] == 1
    assert ergebnis["daten_erfunden"] == 1


def test_zahlentreue_mehrfach_gleiche_zahl_ist_multimenge():
    ergebnis = zahlentreue("900 900 900", "900 900")
    assert (ergebnis["zahlen_gefunden"], ergebnis["zahlen_verfehlt"]) == (2, 1)


# ------------------------------------------------------- Tragfaehige Teilmenge


def _seite(datei, nummer, engine, cer_wert):
    return {"art": "seite", "datei": datei, "seite": nummer, "engine": engine, "cer": cer_wert}


def test_tragfaehige_seiten_behaelt_nur_wo_alle_engines_unter_der_schwelle_sind():
    seiten = [
        _seite("a.pdf", 1, "tesseract", 0.05), _seite("a.pdf", 1, "vision", 0.09),
        _seite("b.pdf", 1, "tesseract", 0.70), _seite("b.pdf", 1, "vision", 0.68),
        _seite("c.pdf", 1, "tesseract", 0.05), _seite("c.pdf", 1, "vision", 0.62),
    ]
    behalten = tragfaehige_seiten(seiten, ["tesseract", "vision"])
    assert {(z["datei"], z["engine"]) for z in behalten} == {("a.pdf", "tesseract"), ("a.pdf", "vision")}


def test_tragfaehige_seiten_verwirft_seite_ohne_messung_aller_engines():
    seiten = [_seite("a.pdf", 1, "tesseract", 0.05)]
    assert tragfaehige_seiten(seiten, ["tesseract", "vision"]) == []


# ----------------------------------------------------------------- Stichprobe


def _kandidaten(anzahl: int) -> tuple[tuple[str, int], ...]:
    return tuple((f"datei{i // 5}.pdf", i % 5 + 1) for i in range(anzahl))


def test_stichprobe_ist_deterministisch():
    kandidaten = _kandidaten(50)
    assert stichprobe(kandidaten, 10, seed=42) == stichprobe(kandidaten, 10, seed=42)


def test_stichprobe_anderer_seed_andere_auswahl():
    kandidaten = _kandidaten(50)
    assert stichprobe(kandidaten, 10, seed=42) != stichprobe(kandidaten, 10, seed=7)


def test_stichprobe_begrenzt_auf_n():
    assert len(stichprobe(_kandidaten(50), 10, seed=42)) == 10


def test_stichprobe_nimmt_alles_wenn_weniger_da_ist():
    kandidaten = _kandidaten(6)
    assert sorted(stichprobe(kandidaten, 99, seed=42)) == sorted(kandidaten)


def test_stichprobe_streut_ueber_dateien():
    """Reihum je Datei, damit nicht 150 Seiten aus drei Dateien kommen."""
    kandidaten = _kandidaten(50)  # 10 Dateien a 5 Seiten
    auswahl = stichprobe(kandidaten, 10, seed=42)
    assert len({datei for datei, _ in auswahl}) == 10


# ------------------------------------------------- Lauf auf synthetischem Mini-PDF

ZEILEN = (
    "Mietvertrag Musterstrasse 5",
    "Die Kaltmiete betraegt 1.240,00 EUR monatlich, faellig zum dritten Werktag.",
    "Die Kaution in Hoehe von 3.720,00 EUR ist am 14.08.2026 faellig.",
    "Nebenkosten pauschal 180,50 EUR, Kuendigungsfrist drei Monate zum Monatsende.",
)


def _mini_pdf(ziel, mit_text=True):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    blatt = canvas.Canvas(str(ziel), pagesize=A4)
    blatt.setFont("Helvetica", 12)
    hoehe = 760
    for zeile in ZEILEN if mit_text else ():
        blatt.drawString(60, hoehe, zeile)
        hoehe -= 24
    blatt.showPage()
    blatt.save()
    return ziel


def test_pruefe_engines_weist_unbekannte_namen_ab():
    with pytest.raises(OcrVergleichFehler, match="Unbekannte Engine"):
        pruefe_engines(["tesseract", "gibtsnicht"])


def test_sammle_korpus_trennt_mit_und_ohne_textebene(tmp_path):
    _mini_pdf(tmp_path / "mit.pdf")
    _mini_pdf(tmp_path / "ohne.pdf", mit_text=False)
    referenzen, ohne = sammle_korpus(tmp_path, min_zeichen=50)
    assert {pfad.name: anzahl for pfad, anzahl in ohne.items()} == {"ohne.pdf": 1}
    assert list(referenzen) == [(str(tmp_path / "mit.pdf"), 1)]


def test_sammle_korpus_ueberspringt_kurze_seiten(tmp_path):
    _mini_pdf(tmp_path / "mit.pdf")
    referenzen, _ = sammle_korpus(tmp_path, min_zeichen=10_000)
    assert referenzen == {}


@pytest.mark.skipif(not shutil.which("tesseract") or not Path(PDFTOPPM).exists(),
                    reason="braucht tesseract und pdftoppm")
def test_lauf_schreibt_seitenzeile_sofort_und_bericht_ohne_inhalt(tmp_path):
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    _mini_pdf(korpus / "mini.pdf")
    ausgabe = tmp_path / "beweise"
    assert main(["--korpus", str(korpus), "--seiten", "1", "--engines", "tesseract",
                 "--dpi", "150", "--min-zeichen", "50", "--ausgabe", str(ausgabe)]) == 0

    lauf = next(ausgabe.glob("*/laeufe.jsonl"))
    zeilen = [json.loads(z) for z in lauf.read_text("utf-8").splitlines()]
    arten = [z["art"] for z in zeilen]
    assert arten == ["lauf", "seite", "engine"]
    seite = zeilen[1]
    assert seite["cer"] is not None and seite["ocr_sekunden"] > 0 and seite["render_sekunden"] > 0
    assert seite["wort_f1"] is not None and seite["ngramm_f1"] is not None
    assert "text" not in seite and "ocr_text" not in seite

    bericht = (lauf.parent / "bericht.md").read_text("utf-8")
    assert "mini.pdf" in bericht and "tesseract" in bericht
    assert "F1 Wort" in bericht and "Tragfaehige Teilmenge" in bericht
    assert "Messbedingungen" in bericht and "| 42 |" in bericht  # Seed steht im Bericht
    for zeile in ZEILEN:
        assert zeile not in bericht  # kein Dokumentinhalt im Bericht


# ------------------------------------------------------- Bild-Vorverarbeitung

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


def _textseite(breite: int = 400, hoehe: int = 300, zeilen: int = 8) -> Image.Image:
    """Synthetische "Textseite": weisses Blatt mit waagerechten schwarzen Balken.

    Kein echter Text — die Neigungsschaetzung arbeitet auf Zeilenprofilen, und Balken sind
    die Zeilen, auf die es ankommt. Damit braucht der Test keinen Korpus und keine Schrift.
    """
    feld = np.full((hoehe, breite), 255, dtype=np.uint8)
    for i in range(zeilen):
        y = 20 + i * (hoehe - 40) // zeilen
        feld[y : y + 6, 40 : breite - 40] = 0
    return Image.fromarray(feld, mode="L")


def test_schaetze_neigung_ist_null_auf_gerader_seite():
    assert abs(schaetze_neigung(_textseite())) < 0.3


def test_schaetze_neigung_findet_gedrehte_seite():
    gedreht = _textseite().rotate(3.0, resample=Image.BICUBIC, fillcolor=255, expand=False)
    assert schaetze_neigung(gedreht) == pytest.approx(3.0, abs=0.5)


def test_vorverarbeite_richtet_gedrehtes_testbild_gerade():
    """Die Kernforderung: was schief hereinkommt, geht gerade heraus."""
    gedreht = _textseite().rotate(2.5, resample=Image.BICUBIC, fillcolor=255, expand=False)
    assert abs(schaetze_neigung(gedreht)) > 1.5
    gerade = vorverarbeite(gedreht)
    assert abs(schaetze_neigung(gerade)) < 0.6


def test_vorverarbeite_liefert_graustufen():
    assert vorverarbeite(_textseite().convert("RGB")).mode == "L"


def test_vorverarbeite_laesst_gerade_seite_gerade():
    assert abs(schaetze_neigung(vorverarbeite(_textseite()))) < 0.6


def test_vorverarbeite_jede_stufe_einzeln_abschaltbar():
    """Ohne `entzerren` bleibt die Neigung stehen — die Stufe ist also wirklich aus."""
    gedreht = _textseite().rotate(2.5, resample=Image.BICUBIC, fillcolor=255, expand=False)
    ohne = vorverarbeite(gedreht, entzerren=False)
    assert abs(schaetze_neigung(ohne)) > 1.5
    alles_aus = vorverarbeite(gedreht, graustufen=False, entzerren=False, kontrast=False,
                              entrauschen=False)
    assert np.array_equal(np.asarray(alles_aus), np.asarray(gedreht))


def test_vorverarbeite_aendert_das_eingangsbild_nicht():
    quelle = _textseite().rotate(2.5, resample=Image.BICUBIC, fillcolor=255, expand=False)
    vorher = np.asarray(quelle).copy()
    vorverarbeite(quelle)
    assert np.array_equal(np.asarray(quelle), vorher)


def test_vorverarbeite_kontrast_spreizt_flaues_bild():
    """Flauer Scan (Grauwerte 100 bis 150) wird auf die volle Skala gezogen."""
    rampe = np.linspace(100, 150, 50, dtype=np.uint8)[None, :].repeat(50, axis=0)
    flau = Image.fromarray(rampe, mode="L")
    assert int(rampe.max()) - int(rampe.min()) == 50
    werte = np.asarray(vorverarbeite(flau, entzerren=False, entrauschen=False))
    assert int(werte.max()) - int(werte.min()) > 150


# ------------------------------------------------------------ Engine-Register


def test_engines_enthalten_die_portablen_kandidaten():
    for name in ("tesseract", "tesseract_vorverarbeitet", "paddleocr", "easyocr"):
        assert name in ENGINES


def test_pruefe_engines_ueberspringt_nicht_installierte_engine_laut(monkeypatch, capsys):
    """Fehlende Abhaengigkeitsgruppe -> klare Meldung und Ueberspringen, kein stiller Verzicht."""
    from dokumentenassistent import ocr_vergleich

    def kaputt():
        raise OcrVergleichFehler("Testgruppe fehlt")

    monkeypatch.setitem(ocr_vergleich.ENGINE_PRUEFUNG, "paddleocr", kaputt)
    assert pruefe_engines(["tesseract", "paddleocr"]) == ("tesseract",)
    assert "paddleocr" in capsys.readouterr().err


def test_pruefe_engines_laesst_engine_ohne_pruefung_durch():
    assert pruefe_engines(["tesseract_vorverarbeitet"]) == ("tesseract_vorverarbeitet",)


# ------------------------------------------------- Paarweiser Vergleich je Seite


def _messung(datei, engine, **felder):
    return {"art": "seite", "datei": datei, "seite": 1, "engine": engine, **felder}


def test_paarweise_zaehlt_besser_gleich_schlechter_bei_f1():
    seiten = [
        _messung("a.pdf", "tesseract", wort_f1=0.90), _messung("a.pdf", "neu", wort_f1=0.95),
        _messung("b.pdf", "tesseract", wort_f1=0.80), _messung("b.pdf", "neu", wort_f1=0.80),
        _messung("c.pdf", "tesseract", wort_f1=0.70), _messung("c.pdf", "neu", wort_f1=0.60),
    ]
    ergebnis = paarweise(seiten, "tesseract", "neu", "wort_f1")
    assert (ergebnis["besser"], ergebnis["gleich"], ergebnis["schlechter"]) == (1, 1, 1)
    assert ergebnis["seiten"] == 3
    assert ergebnis["delta_median"] == pytest.approx(0.0)


def test_paarweise_dreht_die_richtung_bei_cer_um():
    """Bei CER ist weniger besser — sonst behauptet die Tabelle das Gegenteil."""
    seiten = [
        _messung("a.pdf", "tesseract", cer=0.20), _messung("a.pdf", "neu", cer=0.10),
        _messung("b.pdf", "tesseract", cer=0.10), _messung("b.pdf", "neu", cer=0.30),
    ]
    ergebnis = paarweise(seiten, "tesseract", "neu", "cer")
    assert (ergebnis["besser"], ergebnis["schlechter"]) == (1, 1)


def test_paarweise_nimmt_nur_seiten_die_beide_engines_gemessen_haben():
    seiten = [
        _messung("a.pdf", "tesseract", wort_f1=0.9), _messung("a.pdf", "neu", wort_f1=0.9),
        _messung("b.pdf", "tesseract", wort_f1=0.9),
    ]
    assert paarweise(seiten, "tesseract", "neu", "wort_f1")["seiten"] == 1


def test_paarweise_ohne_gemeinsame_seite_ist_leer():
    ergebnis = paarweise([_messung("a.pdf", "tesseract", wort_f1=0.9)], "tesseract", "neu", "wort_f1")
    assert ergebnis["seiten"] == 0 and ergebnis["delta_median"] is None


# ------------------------------------------- Uebernahme alter Messungen (Vergleichbarkeit)


def _alt(datei, seite, engine):
    return {"art": "seite", "datei": datei, "seite": seite, "engine": engine, "wort_f1": 0.9}


def test_uebernommene_zeilen_liefert_nur_die_gemessenen_seiten():
    alt = [_alt("a.pdf", 1, "tesseract"), _alt("b.pdf", 2, "tesseract"), _alt("c.pdf", 3, "tesseract")]
    zeilen, fehlend = uebernommene_zeilen(alt, [("a.pdf", 1), ("b.pdf", 2)], ["tesseract"])
    assert {(z["datei"], z["seite"]) for z in zeilen} == {("a.pdf", 1), ("b.pdf", 2)}
    assert fehlend == ()


def test_uebernommene_zeilen_meldet_fehlende_paare():
    zeilen, fehlend = uebernommene_zeilen([_alt("a.pdf", 1, "tesseract")],
                                          [("a.pdf", 1), ("b.pdf", 2)], ["tesseract"])
    assert len(zeilen) == 1
    assert fehlend == (("tesseract", "b.pdf", 2),)


def test_uebernommene_zeilen_markiert_die_herkunft():
    zeilen, _ = uebernommene_zeilen([_alt("a.pdf", 1, "vision")], [("a.pdf", 1)], ["vision"])
    assert zeilen[0]["uebernommen"] is True


def test_uebernommene_zeilen_ignoriert_fremde_engines_und_andere_arten():
    alt = [_alt("a.pdf", 1, "vision"), {"art": "lauf"}, _alt("a.pdf", 1, "tesseract")]
    zeilen, _ = uebernommene_zeilen(alt, [("a.pdf", 1)], ["vision"])
    assert [z["engine"] for z in zeilen] == ["vision"]


@pytest.mark.skipif(not shutil.which("tesseract") or not Path(PDFTOPPM).exists(),
                    reason="braucht tesseract und pdftoppm")
def test_lauf_uebernimmt_alte_messung_und_vergleicht_paarweise(tmp_path):
    """Eine Engine wird gemessen, eine aus einem alten Lauf uebernommen — und der Bericht
    stellt beide paarweise gegenueber, ohne die alte neu zu messen."""
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    _mini_pdf(korpus / "mini.pdf")
    alt = tmp_path / "alt.jsonl"
    alt.write_text(json.dumps({
        # Dateiname ohne Ordner — genau so, wie das Protokoll ihn fuehrt (`pdf.name`)
        "art": "seite", "engine": "tesseract", "datei": "mini.pdf", "seite": 1,
        "cer": 0.5, "wer": 0.5, "wort_f1": 0.5, "ngramm_f1": 0.5,
        "zahlen_gefunden": 1, "zahlen_verfehlt": 0, "zahlen_erfunden": 0,
        "daten_gefunden": 0, "daten_verfehlt": 0, "daten_erfunden": 0,
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    ausgabe = tmp_path / "beweise"

    assert main(["--korpus", str(korpus), "--seiten", "1", "--engines", "tesseract_vorverarbeitet",
                 "--dpi", "150", "--min-zeichen", "50", "--ausgabe", str(ausgabe),
                 "--uebernehmen", str(alt), "--uebernehmen-engines", "tesseract"]) == 0

    lauf = next(ausgabe.glob("*/laeufe.jsonl"))
    zeilen = [json.loads(z) for z in lauf.read_text("utf-8").splitlines()]
    uebernommen = [z for z in zeilen if z.get("uebernommen")]
    assert [z["engine"] for z in uebernommen] == ["tesseract"]
    assert [z for z in zeilen if z.get("art") == "uebernahme"][0]["fehlend"] == 0

    bericht = (lauf.parent / "bericht.md").read_text("utf-8")
    assert "Paarweise je Seite gegen `tesseract`" in bericht
    assert "| tesseract_vorverarbeitet | wort_f1 |" in bericht
    assert "Uebernommen aus" in bericht
    for zeile in ZEILEN:
        assert zeile not in bericht


def test_uebernommene_zeilen_vergleicht_ueber_den_dateinamen_nicht_den_pfad():
    """Das Protokoll fuehrt `pdf.name`, die Stichprobe kennt den vollen Pfad. Wer hier den
    Pfad vergleicht, uebernimmt nichts und merkt es nur an der Warnung (live passiert:
    0 uebernommen, 450 fehlend)."""
    zeilen, fehlend = uebernommene_zeilen(
        [_alt("mini.pdf", 1, "tesseract")], [("/daten/ordner/mini.pdf", 1)], ["tesseract"]
    )
    assert len(zeilen) == 1 and fehlend == ()


# ------------------------------------------------- Fortsetzen eines abgebrochenen Laufs


def test_bereits_gemessen_liest_engine_datei_seite_aus_dem_protokoll():
    zeilen = [
        {"art": "lauf"},
        {"art": "seite", "engine": "easyocr", "datei": "a.pdf", "seite": 3},
        {"art": "fehler", "engine": "easyocr", "datei": "b.pdf", "seite": 1},
        {"art": "seite", "engine": "tesseract", "datei": "a.pdf", "seite": 3, "uebernommen": True},
    ]
    assert bereits_gemessen(zeilen) == {("easyocr", "a.pdf", 3)}


def test_bereits_gemessen_zaehlt_uebernommene_nicht_als_gemessen():
    """Uebernommene Zeilen kommen aus einem anderen Lauf — sie duerfen eine Messung dieser
    Engine nicht verhindern, sonst haengt das Fortsetzen davon ab, was uebernommen wurde."""
    zeilen = [{"art": "seite", "engine": "vision", "datei": "a.pdf", "seite": 1,
               "uebernommen": True}]
    assert bereits_gemessen(zeilen) == set()


@pytest.mark.skipif(not shutil.which("tesseract") or not Path(PDFTOPPM).exists(),
                    reason="braucht tesseract und pdftoppm")
def test_lauf_misst_mit_fortsetzen_keine_seite_zweimal(tmp_path):
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    _mini_pdf(korpus / "mini.pdf")
    ausgabe = tmp_path / "beweise"
    args = ["--korpus", str(korpus), "--seiten", "1", "--engines", "tesseract",
            "--dpi", "150", "--min-zeichen", "50", "--ausgabe", str(ausgabe)]
    assert main(args) == 0
    assert main([*args, "--fortsetzen"]) == 0

    lauf = next(ausgabe.glob("*/laeufe.jsonl"))
    zeilen = [json.loads(z) for z in lauf.read_text("utf-8").splitlines()]
    assert sum(1 for z in zeilen if z.get("art") == "seite") == 1


@pytest.mark.skipif(not shutil.which("tesseract") or not Path(PDFTOPPM).exists(),
                    reason="braucht tesseract und pdftoppm")
def test_fortsetzen_uebernimmt_nicht_ein_zweites_mal(tmp_path):
    """Sonst stuenden die uebernommenen Seiten doppelt im Protokoll und zaehlten doppelt
    in jeden Median."""
    korpus = tmp_path / "korpus"
    korpus.mkdir()
    _mini_pdf(korpus / "mini.pdf")
    alt = tmp_path / "alt.jsonl"
    alt.write_text(json.dumps({"art": "seite", "engine": "vision", "datei": "mini.pdf",
                               "seite": 1, "wort_f1": 0.5}, ensure_ascii=False) + "\n", "utf-8")
    ausgabe = tmp_path / "beweise"
    args = ["--korpus", str(korpus), "--seiten", "1", "--engines", "tesseract",
            "--dpi", "150", "--min-zeichen", "50", "--ausgabe", str(ausgabe),
            "--uebernehmen", str(alt), "--uebernehmen-engines", "vision"]
    assert main(args) == 0
    assert main([*args, "--fortsetzen"]) == 0

    zeilen = [json.loads(z) for z in next(ausgabe.glob("*/laeufe.jsonl")).read_text("utf-8").splitlines()]
    assert sum(1 for z in zeilen if z.get("uebernommen")) == 1
    assert sum(1 for z in zeilen if z.get("art") == "uebernahme") == 1


# ------------------------------------------- Schnittmenge aller Engines (Vergleichbarkeit)


def test_gemeinsame_seiten_behaelt_nur_was_jede_engine_gemessen_hat():
    """Nach dem Abbruch haben die neuen Engines 100 Seiten, die uebernommenen 144. Ohne
    Schnittmenge vergliche die Tabelle Mediane ueber verschiedene Seitenmengen."""
    seiten = [
        _messung("a.pdf", "alt", wort_f1=0.9), _messung("a.pdf", "neu", wort_f1=0.9),
        _messung("b.pdf", "alt", wort_f1=0.9),
    ]
    behalten = gemeinsame_seiten(seiten, ["alt", "neu"])
    assert {(z["datei"], z["engine"]) for z in behalten} == {("a.pdf", "alt"), ("a.pdf", "neu")}


def test_gemeinsame_seiten_ohne_schnittmenge_ist_leer():
    seiten = [_messung("a.pdf", "alt", wort_f1=0.9), _messung("b.pdf", "neu", wort_f1=0.9)]
    assert gemeinsame_seiten(seiten, ["alt", "neu"]) == []


def test_gemeinsame_seiten_haelt_je_engine_und_seite_genau_eine_zeile():
    """Zwei Dateien gleichen Namens in verschiedenen Ordnern erzeugen denselben Schluessel
    (das Protokoll fuehrt `pdf.name`). Ohne diese Entdopplung zaehlte eine Engine 99 Zeilen
    auf 96 Seiten, die naechste 96 — und die Mediane waeren nicht mehr vergleichbar."""
    seiten = [
        _messung("a.pdf", "alt", wort_f1=0.9), _messung("a.pdf", "neu", wort_f1=0.8),
        _messung("a.pdf", "neu", wort_f1=0.2),
    ]
    behalten = gemeinsame_seiten(seiten, ["alt", "neu"])
    assert len(behalten) == 2
    assert [z["wort_f1"] for z in behalten if z["engine"] == "neu"] == [0.8]

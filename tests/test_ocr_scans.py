"""Gegenlese-Paket fuer echte Scan-Seiten: reine Funktionen an synthetischen Daten.

Kein echter Korpus, keine Engine, kein Netz. Gemessen wird hier nichts — nur, ob die
Ziehung deterministisch ist, ob die Kennzahlen zaehlen, was sie behaupten, und ob das
gebaute Paket offline traegt (keine externe Adresse, ein Urteilsfeld je Seite und Engine).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dokumentenassistent.ocr_scans import (
    BILDENDUNGEN,
    URTEILE,
    baue_paket,
    bild_fuer,
    gegenlese_html,
    indikatoren,
    ocr_pflichtige_quellen,
    protokollzeile,
    readme_text,
    ziehe,
)

from tests.conftest import schreibe_bild, schreibe_bild_pdf, schreibe_text_pdf


# --------------------------------------------------------------- Quellen finden


def _korpus(tmp_path: Path) -> Path:
    """Ein Mini-Korpus: ein PDF **mit** Textebene (nicht OCR-pflichtig), zwei Bild-PDFs
    ohne Textebene und eine Bilddatei."""
    korpus = tmp_path / "korpus"
    (korpus / "unterordner").mkdir(parents=True)
    schreibe_text_pdf(korpus / "Mietvertrag.pdf", ["Miete 900,00 EUR", "Seite zwei"])
    schreibe_bild_pdf(korpus / "Scan_0043.pdf", "Rechnung 17,90 EUR")
    schreibe_bild_pdf(korpus / "unterordner" / "Scan_0044.pdf", "Quittung 5,00 EUR")
    schreibe_bild(korpus / "IMG_8831.jpg", "Beleg 12,00 EUR")
    return korpus


def test_quellen_nimmt_pdfs_ohne_textebene_und_bilddateien(tmp_path):
    korpus = _korpus(tmp_path)
    namen = {Path(datei).name for datei, _seite in ocr_pflichtige_quellen(korpus)}
    assert namen == {"Scan_0043.pdf", "Scan_0044.pdf", "IMG_8831.jpg"}


def test_quellen_laesst_pdfs_mit_textebene_aus(tmp_path):
    """Das ist die Abgrenzung zur bisherigen Messung: Seiten **mit** Textebene haben eine
    Wahrheit und wurden dort gemessen. Hier geht es genau um die anderen."""
    korpus = _korpus(tmp_path)
    assert not [q for q in ocr_pflichtige_quellen(korpus) if "Mietvertrag" in q[0]]


def test_quellen_fuehrt_bilddatei_als_seite_eins(tmp_path):
    korpus = _korpus(tmp_path)
    bilder = [q for q in ocr_pflichtige_quellen(korpus) if q[0].endswith(".jpg")]
    assert bilder and all(seite == 1 for _datei, seite in bilder)


def test_quellen_laesst_macos_metadaten_rumpfe_aus(tmp_path):
    """`._IMG_8831.jpg` traegt die Endung eines Bildes und ist keines. Der erste Lauf vom
    24.09.2026 ist darueber gestolpert ('cannot identify image file') und hat neun statt
    zehn Seiten geliefert."""
    korpus = _korpus(tmp_path)
    (korpus / "._IMG_8831.jpg").write_bytes(b"\x00\x05\x16\x07Metadaten, kein Bild")
    (korpus / "._Scan_0043.pdf").write_bytes(b"\x00\x05\x16\x07")
    namen = {Path(datei).name for datei, _seite in ocr_pflichtige_quellen(korpus)}
    assert not [n for n in namen if n.startswith("._")]


def test_quellen_kennt_die_ueblichen_bildendungen():
    assert set(BILDENDUNGEN) == {".jpg", ".jpeg", ".png"}


def test_quellen_nimmt_jede_seite_eines_mehrseitigen_scans(tmp_path):
    korpus = tmp_path / "k"
    korpus.mkdir()
    bild = schreibe_bild(tmp_path / "roh.png", "Seite")
    from PIL import Image

    erste = Image.open(bild).convert("RGB")
    erste.save(korpus / "Scan.pdf", "PDF", save_all=True, append_images=[erste, erste])
    assert sorted(s for _d, s in ocr_pflichtige_quellen(korpus)) == [1, 2, 3]


# ------------------------------------------------------------------- Ziehung


def test_ziehung_ist_bei_gleichem_seed_identisch(tmp_path):
    korpus = _korpus(tmp_path)
    assert ziehe(korpus, 3, 42) == ziehe(korpus, 3, 42)


def test_ziehung_streut_ueber_die_dateien(tmp_path):
    """Zehn Seiten aus einem Dokument waeren zehnmal derselbe Scanner. Die Ziehung geht
    reihum ueber die Dateien, bevor sie eine Datei ein zweites Mal anfasst."""
    korpus = tmp_path / "k"
    korpus.mkdir()
    from PIL import Image

    bild = Image.open(schreibe_bild(tmp_path / "roh.png", "Seite")).convert("RGB")
    for nummer in range(4):
        bild.save(korpus / f"Scan_{nummer}.pdf", "PDF", save_all=True,
                  append_images=[bild] * 4)
    gezogen = ziehe(korpus, 4, 42)
    assert len({Path(datei).name for datei, _seite in gezogen}) == 4


def test_ziehung_nimmt_hoechstens_was_da_ist(tmp_path):
    assert len(ziehe(_korpus(tmp_path), 99, 42)) == 3


# ---------------------------------------------------------------- Kennzahlen


def test_indikatoren_zaehlen_zeichen_zahlen_und_daten():
    werte = indikatoren("Rechnung 1.240,00 EUR vom 14.08.2026, Pos. 3")
    assert werte["zahlen"] == 2  # 1.240,00 und 3 — das Datum zaehlt nicht als Zahl
    assert werte["daten"] == 1
    assert werte["zeichen"] == len("Rechnung 1.240,00 EUR vom 14.08.2026, Pos. 3")


def test_indikatoren_falten_leerraum_wie_die_messung_davor():
    assert indikatoren("Miete\n\n  900")["zeichen"] == len("Miete 900")


def test_indikatoren_auf_leerem_text_sind_null():
    assert indikatoren("") == {"zeichen": 0, "zahlen": 0, "daten": 0}


def test_protokollzeile_enthaelt_keinen_dokumentinhalt():
    """Der Korpus ist privat: in `laeufe.jsonl` stehen Kennzahlen, nie der gelesene Text."""
    zeile = protokollzeile(
        engine="tesseract", quelle=Path("/x/Scan.pdf"), seite=3, nummer=1,
        text="Geheime Rechnung 1.240,00 EUR", konfidenz=0.81, sekunden=1.5, loadavg=0.4,
    )
    roh = json.dumps(zeile, ensure_ascii=False)
    assert "Geheime" not in roh and "1.240" not in roh
    assert zeile["zeichen"] == 29 and zeile["zahlen"] == 1 and zeile["konfidenz"] == 0.81
    assert zeile["datei"] == "Scan.pdf" and zeile["seite"] == 3


def test_protokollzeile_markiert_dauer_unter_fremdlast():
    """Eine Dauer, die unter Fremdlast entstanden ist, misst zum guten Teil die Maschine.
    Sie wird deshalb am Feld selbst gekennzeichnet, nicht nur im Fliesstext daneben."""
    fest = dict(engine="x", quelle=Path("a.jpg"), seite=1, nummer=1, text="", konfidenz=None,
                sekunden=1.0)
    assert protokollzeile(**fest, loadavg=12.0)["dauer_unter_fremdlast"] is True
    assert protokollzeile(**fest, loadavg=0.4)["dauer_unter_fremdlast"] is False


def test_readme_kennzeichnet_fremdlast_nur_wenn_sie_vorlag():
    unter_last = readme_text(_seiten(), ["tesseract"], "2026-09-23", lasten=[12.0, 0.3])
    assert "nicht belastbar" in unter_last and "dauer_unter_fremdlast" in unter_last
    assert "nicht belastbar" not in readme_text(_seiten(), ["tesseract"], "2026-09-23", [0.3])


def test_readme_zaehlt_die_betroffenen_messungen_statt_des_startwerts():
    """Der Lauf vom 24.09.2026 startete bei loadavg 3,6 — unter der Schwelle — und lief bei
    bis zu 10,2 weiter. Ein README, das nur den **Startwert** befragt, schwieg zu 37 von 40
    unbelastbaren Zeitangaben: es schwieg also genau dann, wenn es haette reden muessen.
    Gezaehlt werden deshalb die einzelnen Messungen."""
    text = readme_text(_seiten(), ["tesseract"], "2026-09-23", lasten=[3.6, 9.0, 10.2, 8.0])
    assert "3 der 4 Messungen" in text
    assert "10.2" in text  # der hoechste gemessene Wert, nicht der erste


def test_protokollzeile_haelt_fehlende_konfidenz_offen():
    zeile = protokollzeile(engine="x", quelle=Path("a.jpg"), seite=1, nummer=1,
                           text="", konfidenz=None, sekunden=0.1, loadavg=9.0)
    assert zeile["konfidenz"] is None


# -------------------------------------------------------------------- Paket


def _seiten() -> list[dict]:
    return [
        {
            "nummer": 1, "bild": "seite-01.png", "datei": "Scan_0043.pdf", "seite": 7,
            "ergebnisse": [
                {"engine": "tesseract", "text": "Rechnung <b>17,90</b> EUR"},
                {"engine": "tesseract_vorverarbeitet", "text": "Rechnung 17,90 EUR"},
                {"engine": "paddleocr", "text": "Rechnung 17.90 EUR"},
                {"engine": "vision", "text": ""},
            ],
        }
    ]


def test_html_zeigt_bild_und_alle_engines():
    html = gegenlese_html(_seiten(), "2026-09-23")
    assert 'src="seite-01.png"' in html
    for engine in ("tesseract", "tesseract_vorverarbeitet", "paddleocr", "vision"):
        assert engine in html


def test_html_maskiert_dokumenttext_statt_ihn_auszufuehren():
    html = gegenlese_html(_seiten(), "2026-09-23")
    assert "&lt;b&gt;17,90&lt;/b&gt;" in html
    assert "<b>17,90</b>" not in html


def test_html_hat_je_seite_und_engine_ein_urteil_und_ein_freitextfeld():
    html = gegenlese_html(_seiten(), "2026-09-23")
    for engine in ("tesseract", "tesseract_vorverarbeitet", "paddleocr", "vision"):
        for urteil in URTEILE:
            assert f'name="urteil-1-{engine}" value="{urteil}"' in html
        assert f'name="notiz-1-{engine}"' in html


def test_html_laedt_nichts_nach_ausser_den_eigenen_bildern():
    """Safari, Doppelklick, kein Server: ein einziger externer **Verweis** wuerde das Paket
    an eine Netzverbindung haengen — und den privaten Korpus potenziell nach draussen.

    Geprueft werden Verweise (`src`, `href`, `url()`, `@import`), nicht das Vorkommen der
    Zeichenkette `https://`: die steht im echten Paket sehr wohl im HTML, naemlich als
    **Dokumenttext** in einem `<pre>` — auf Rechnungen sind Web-Adressen gedruckt. Der erste
    Test hat auf die Zeichenkette geprueft, waere auf synthetischen Daten gruen geblieben und
    haette am echten Paket falschen Alarm ausgeloest. Inerter Text ist kein Verweis.
    """
    seiten = _seiten()
    seiten[0]["ergebnisse"][0]["text"] = "Rechnung, mehr unter https://beispiel.invalid/agb"
    html = gegenlese_html(seiten, "2026-09-23")
    verweise = re.findall(r"""(?:src|href|action|poster)\s*=\s*["']([^"']*)["']""", html)
    assert verweise == ["seite-01.png"]
    assert "url(" not in html and "@import" not in html
    assert "fetch(" not in html and "XMLHttpRequest" not in html


def test_html_sichert_urteile_als_datei_zum_herunterladen():
    html = gegenlese_html(_seiten(), "2026-09-23")
    assert "Urteile sichern" in html
    assert "Blob" in html and "download" in html


def test_html_nennt_herkunft_der_seite():
    html = gegenlese_html(_seiten(), "2026-09-23")
    assert "Scan_0043.pdf" in html and "Seite 7" in html


def test_readme_nennt_die_beurteilungsfelder_und_die_grenze():
    text = readme_text(_seiten(), ["tesseract", "paddleocr"], "2026-09-23")
    for feld in ("Beträge", "Daten", "Rechnungsnummern", "Namen"):
        assert feld in text
    assert "kein" in text.lower() and "Statistik" in text
    assert "gegenlesen.html" in text


def test_paket_schreibt_html_und_readme(tmp_path):
    baue_paket(_seiten(), ["tesseract", "paddleocr"], tmp_path, "2026-09-23")
    assert (tmp_path / "gegenlesen.html").exists()
    assert (tmp_path / "README.md").exists()
    assert "Scan_0043.pdf" in (tmp_path / "gegenlesen.html").read_text("utf-8")


def test_bild_fuer_bilddatei_legt_ein_png_an(tmp_path):
    quelle = schreibe_bild(tmp_path / "IMG.jpg", "Beleg")
    ziel = tmp_path / "seite-01.png"
    bild_fuer(quelle, 1, 300, ziel)
    assert ziel.exists() and ziel.read_bytes()[:4] == b"\x89PNG"


def test_bild_fuer_pdf_rendert_die_verlangte_seite(tmp_path):
    from dokumentenassistent.ocr_vergleich import PDFTOPPM

    if not Path(PDFTOPPM).exists():
        pytest.skip("pdftoppm nicht installiert")
    quelle = schreibe_bild_pdf(tmp_path / "Scan.pdf", "Rechnung")
    ziel = tmp_path / "seite-01.png"
    bild_fuer(quelle, 1, 150, ziel)
    assert ziel.exists() and ziel.read_bytes()[:4] == b"\x89PNG"

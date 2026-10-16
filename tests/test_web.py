"""Stufe 3 · Web-Oberfläche — W1–W18.

Prüft die vier Bereiche gegen eine Werkstatt mit FakeProvider: dass jede Seite
antwortet, dass jedes Formular genau den Werkstatt-Aufruf auslöst, den es
verspricht, und dass die Zustände (Status, nicht_gefunden, Providerfehler)
sichtbar unterschiedlich gerendert werden. Keine Fachlogik wird hier erneut
geprüft (das tun M1–M11 und die Verdrahtungsstufe).
"""
from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dokumentenassistent import web_ansicht as ansicht
from dokumentenassistent.provider import OcrEinstellungen, ProviderFehler, Sucheinstellungen
from dokumentenassistent.web import create_app
from dokumentenassistent.werkstatt import Werkstatt
from tests.conftest import FakeProvider, schreibe_bild, schreibe_text_pdf

ZWECK = "Steuererklärung 2025"

MIETVERTRAG = "Dokument1 Kopie.pdf"  # bytegleiche Kopie, sortiert VOR Dokument1.pdf
KOPIE = "Dokument1.pdf"  # zweiter Fundort desselben Hashes → Duplikat
BILD = "IMG_8831.jpg"  # unscharf → ocr_unsicher
RECHNUNG = "Rechnung (2).pdf"
KORREKTUR = "Rechnung (3).pdf"  # Konflikt zum Betrag der Rechnung
ANLEITUNG = "Untitled.pdf"  # ohne Bezug zum Zweck → unklar

PROFIL_ANTWORT = {
    "kategorien": ["Wohnung Nord", "Einkommen"],
    "dokumenttypen": ["Rechnung", "Mietvertrag"],
    "felder": ["datum", "aussteller", "betrag", "rechnungsnummer"],
    "namensschema": "{datum}_{typ}_{aussteller}",
}


def _einlesen(client):
    """Quelle einlesen und auf das Ende warten.

    Seit 24.09.2026 laeuft Erfassen+Auslesen im Hintergrund (OCR ist bei Scans der
    teuerste Schritt und hielt den Browser vorher fest). Ein Test, der danach sofort
    weiterliest, sieht sonst einen halb gefuellten Index -- mal gruen, mal rot."""
    antwort = client.post("/profil/einlesen")
    thread = client.app.state.job.thread
    if thread is not None:
        thread.join(timeout=30)
    return antwort


def _feld(name: str, wert: str, fid: str, wortlaut: str) -> dict:
    return {"name": name, "wert": wert, "fundstelle_id": fid, "wortlaut": wortlaut}


EIN_MIETVERTRAG = {
    "kategorie": "Wohnung Nord",
    "typ": "Mietvertrag",
    "begruendung": "Mietvertrag der Wohnung Nord",
    "felder": [
        _feld("datum", "2024-01-01", f"{MIETVERTRAG}#S3#A1", "Vertragsdatum 01.01.2024"),
        _feld("aussteller", "Meier", f"{MIETVERTRAG}#S1#A1", "Hausverwaltung Meier"),
        _feld("betrag", "780,00 EUR", f"{MIETVERTRAG}#S2#A1", "Kaltmiete 780,00 EUR"),
        _feld("rechnungsnummer", "2024-MV-77", f"{MIETVERTRAG}#S1#A1", "Vertragsnummer 2024-MV-77"),
    ],
}
EIN_RECHNUNG = {
    "kategorie": "Wohnung Nord",
    "typ": "Rechnung",
    "begruendung": "Heizungsreparatur Wohnung Nord",
    "felder": [
        _feld("datum", "2025-05-14", f"{RECHNUNG}#S1#A1", "Rechnungsdatum 14.05.2025"),
        _feld("aussteller", "Krause", f"{RECHNUNG}#S1#A1", "Krause GmbH"),
        _feld("betrag", "1.240,00 EUR", f"{RECHNUNG}#S1#A1", "Rechnungsbetrag 1.240,00 EUR"),
        _feld("rechnungsnummer", "2025-0815", f"{RECHNUNG}#S1#A1", "Rechnung Nr. 2025-0815"),
    ],
}
EIN_KORREKTUR = {
    "kategorie": "Wohnung Nord",
    "typ": "Rechnung",
    "begruendung": "Korrekturrechnung zur Heizungsreparatur",
    "felder": [
        _feld("datum", "2025-06-02", f"{KORREKTUR}#S1#A1", "Rechnungsdatum 02.06.2025"),
        _feld("aussteller", "Krause", f"{KORREKTUR}#S1#A1", "Krause GmbH"),
        _feld("betrag", "1.180,00 EUR", f"{KORREKTUR}#S1#A1", "Rechnungsbetrag 1.180,00 EUR"),
        _feld(
            "rechnungsnummer",
            "2025-0815-K",
            f"{KORREKTUR}#S1#A1",
            "Korrekturrechnung Nr. 2025-0815-K",
        ),
    ],
}
EIN_ANLEITUNG = {
    "kategorie": "unbekannt",
    "typ": "unbekannt",
    "begruendung": "Bedienungsanleitung ohne Bezug zum Zweck",
    "felder": [],
}

# 21.09.: Suche ist dense allein mit Kosinus-Schwelle 0.49. Der Bag-of-Words-FakeProvider gibt für
# „Wie hoch ist die Kaltmiete?" gegen den Kaltmiete-Absatz nur 0.105; vier Treffer-Wörter ergeben 0.566.
FRAGE_KALTMIETE = "Kaltmiete und Nebenkosten monatlich in EUR?"
ANTWORT_KALTMIETE = f"Die Kaltmiete beträgt 780,00 EUR [{MIETVERTRAG}#S2#A1]."
FRAGE_OHNE_BELEG = "Welchen Kilometerstand hat das Auto?"

PROFIL_FORMULAR = {
    "zweck": ZWECK,
    "kategorien": "Wohnung Nord\nEinkommen",
    "dokumenttypen": "Rechnung\nMietvertrag",
    "felder": "datum\naussteller\nbetrag\nrechnungsnummer",
    "namensschema": "{datum}_{typ}_{aussteller}",
}


def _schreibe_korpus(quelle: Path) -> None:
    schreibe_text_pdf(
        quelle / RECHNUNG,
        [
            (
                "Rechnung Nr. 2025-0815\nRechnungsdatum 14.05.2025\nHeizung Sanitär Krause GmbH\n"
                "Rechnungsbetrag 1.240,00 EUR\nLeistung: Reparatur Heizung, Wohnung Nord"
            )
        ],
    )
    schreibe_text_pdf(
        quelle / KORREKTUR,
        [
            (
                "Korrekturrechnung Nr. 2025-0815-K\nKorrektur zu Rechnung Nr. 2025-0815\n"
                "Rechnungsdatum 02.06.2025\nHeizung Sanitär Krause GmbH\nRechnungsbetrag 1.180,00 EUR"
            )
        ],
    )
    schreibe_text_pdf(
        quelle / KOPIE,
        [
            "Mietvertrag Wohnung Nord\nVermieter Hausverwaltung Meier\nVertragsnummer 2024-MV-77",
            "Kaltmiete 780,00 EUR\nNebenkosten 120,00 EUR monatlich",
            "Vertragsdatum 01.01.2024\nMietbeginn 01.02.2024",
        ],
    )
    shutil.copyfile(quelle / KOPIE, quelle / MIETVERTRAG)
    schreibe_bild(quelle / BILD, "Quittung 17,90 EUR", unscharf=True)
    schreibe_text_pdf(
        quelle / ANLEITUNG,
        [
            (
                "Bedienungsanleitung Router Modell FB-7530\nKapitel 1 Inbetriebnahme\n"
                "Stecken Sie das Netzteil ein und warten Sie auf die Power-LED."
            )
        ],
    )


def _werkstatt(tmp_path: Path, provider: FakeProvider) -> Werkstatt:
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    _schreibe_korpus(quelle)
    return Werkstatt(
        quelle=quelle,
        zielablage=tmp_path / "ablage",
        provider=provider,
        arbeitsordner=tmp_path / "arbeit",
    )


def _zeile(html: str, hash_: str) -> str:
    """Der <tr>-Block, in dem dieser Hash zuerst auftaucht."""
    start = html.rindex("<tr", 0, html.index(hash_))
    return html[start : html.index("</tr>", start)]


@pytest.fixture
def werkstatt(tmp_path):
    """Mini-Korpus wie in test_werkstatt.py: fünf eingereihte JSON-Antworten
    (Profil + vier Einordnungen), eine Text-Antwort für die Suche."""
    provider = FakeProvider(
        json_antworten=[
            PROFIL_ANTWORT,
            EIN_MIETVERTRAG,
            EIN_RECHNUNG,
            EIN_KORREKTUR,
            EIN_ANLEITUNG,
        ],
        text_antworten=[ANTWORT_KALTMIETE],
    )
    return _werkstatt(tmp_path, provider)


@pytest.fixture
def client(werkstatt):
    return TestClient(create_app(werkstatt))


@pytest.fixture
def stapel(client, werkstatt):
    """Quelle eingelesen, Profil bestätigt, Vorschläge erzeugt. Gibt Name → Hash."""
    _einlesen(client)
    client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    client.post("/profil/bestaetigen", data=PROFIL_FORMULAR)
    client.post("/eingang/einordnen")
    client.app.state.job.thread.join(timeout=10)  # Einordnen läuft im Hintergrund
    return {d.name: d.hash for d in werkstatt.index.dateien()}


# ------------------------------------------------------------------ W1: Seiten


@pytest.mark.parametrize("pfad", ["/profil", "/eingang", "/bestand", "/finden"])
def test_W1_vier_bereiche_antworten(client, pfad):
    antwort = client.get(pfad)
    assert (antwort.status_code, "text/html" in antwort.headers["content-type"]) == (200, True)


def test_W1b_startseite_fuehrt_auf_profil(client):
    assert client.get("/").url.path == "/profil"


# -------------------------------------------------------------- W2/W3: Profil


def test_W2_vorschlagen_zeigt_entwurf_als_editierbares_formular(client):
    _einlesen(client)
    seite = client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    html = seite.text
    assert (
        seite.status_code,
        'name="kategorien"' in html,
        'name="namensschema"' in html,
        "Wohnung Nord" in html,
        "{datum}_{typ}_{aussteller}" in html,
        "/profil/bestaetigen" in html,
    ) == (200, True, True, True, True, True)


def test_W3_bestaetigen_speichert_das_profil(client, werkstatt):
    _einlesen(client)
    client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    vorher = werkstatt.profil
    antwort = client.post("/profil/bestaetigen", data=PROFIL_FORMULAR)
    assert (
        vorher,
        antwort.status_code,
        werkstatt.profil is not None,
        werkstatt.profil.zweck,
        werkstatt.profil.kategorien,
        werkstatt.profil_pfad.exists(),
    ) == (None, 200, True, ZWECK, ("Wohnung Nord", "Einkommen"), True)


# ----------------------------------------------------------------- W4: Eingang


def test_W4_eingang_zeigt_je_zeile_quelle_kategorie_zielname_status_beleg(client, stapel):
    html = client.get("/eingang").text
    assert (
        MIETVERTRAG in html,
        "Wohnung Nord" in html,
        "2024-01-01_Mietvertrag_Meier.pdf" in html,
        'data-status="sicher"' in html,
        "Vertragsdatum 01.01.2024" in html,  # Beleg-Kurzfassung der Zeile
        ANLEITUNG in html,
        'data-status="unklar"' in html,
        BILD in html,
        'data-status="ocr_unsicher"' in html,
        'data-status="konflikt"' in html,
    ) == (True,) * 10


def test_W4b_nur_sichere_zeilen_sind_ankreuzbar(client, stapel):
    html = client.get("/eingang").text
    zeilen = {name: _zeile(html, stapel[name]) for name in (MIETVERTRAG, ANLEITUNG, BILD)}
    assert (
        'name="hashes"' in zeilen[MIETVERTRAG],
        "disabled" in zeilen[MIETVERTRAG],
        "disabled" in zeilen[ANLEITUNG],
        "disabled" in zeilen[BILD],
    ) == (True, False, True, True)


def test_W4c_freigabeknopf_steht_oben_und_unten(client, stapel):
    assert client.get("/eingang").text.count("Bestätigte Kopien erzeugen") == 2


# --------------------------------------------------------------- W5–W7: Aktionen


def test_W5_freigeben_ruft_freigeben_mit_genau_den_angehakten_hashes(client, werkstatt, stapel):
    gerufen: list[tuple[str, ...]] = []
    echt = werkstatt.freigeben

    def spion(hashes):
        gerufen.append(hashes)
        return echt(hashes)

    werkstatt.freigeben = spion
    antwort = client.post(
        "/eingang/freigeben",
        data={"hashes": [stapel[MIETVERTRAG], stapel[RECHNUNG]]},
    )
    assert (antwort.status_code, gerufen) == (
        200,
        [(stapel[MIETVERTRAG], stapel[RECHNUNG])],
    )


def test_W6_korrigieren_ruft_korrigiere(client, werkstatt, stapel):
    gerufen: list[dict] = []
    echt = werkstatt.korrigiere

    def spion(hash, kategorie=None, zielname=None):
        gerufen.append({"hash": hash, "kategorie": kategorie, "zielname": zielname})
        return echt(hash, kategorie=kategorie, zielname=zielname)

    werkstatt.korrigiere = spion
    erwartet = {
        "hash": stapel[ANLEITUNG],
        "kategorie": "Wohnung Nord",
        "zielname": "2025-01-01_Anleitung_FB-7530.pdf",
    }
    antwort = client.post("/eingang/korrigieren", data=erwartet)
    vorschlag = next(v for v in werkstatt.index.vorschlaege() if v.datei_hash == stapel[ANLEITUNG])
    assert (antwort.status_code, gerufen, vorschlag.status) == (200, [erwartet], "sicher")


def test_W7_konflikt_entscheiden_ruft_entscheide_konflikt(client, werkstatt, stapel):
    gerufen: list[tuple] = []
    echt = werkstatt.entscheide_konflikt

    def spion(id, entscheidung, eigener_wert=None):
        gerufen.append((id, entscheidung, eigener_wert))
        return echt(id, entscheidung, eigener_wert)

    werkstatt.entscheide_konflikt = spion
    konflikt = werkstatt.index.konflikte(offen=True)[0]
    antwort = client.post(f"/konflikt/{konflikt.id}", data={"entscheidung": "ersetzt"})
    assert (
        antwort.status_code,
        gerufen,
        werkstatt.index.konflikte(offen=True),
        werkstatt.index.konflikte(offen=False)[0].entscheidung,
    ) == (200, [(konflikt.id, "ersetzt", None)], (), "ersetzt")


def test_W7b_konfliktkarte_zeigt_beide_werte_belege_und_vier_optionen(client, stapel):
    html = client.get("/eingang").text
    assert (
        "1.240,00 EUR" in html,
        "1.180,00 EUR" in html,
        'value="ersetzt"' in html,
        'value="verschiedene_sachverhalte"' in html,
        'value="nicht_entscheidbar"' in html,
        'value="eigener_wert"' in html,
        'name="eigener_wert"' in html,
    ) == (True,) * 7


# --------------------------------------------------------------- W8: Detailseite


def test_W8_detailseite_zeigt_original_links_und_belege_mit_mark(client, stapel, werkstatt):
    seite = client.get(f"/eingang/{stapel[MIETVERTRAG]}")
    html = seite.text
    assert (
        seite.status_code,
        "<mark>Kaltmiete 780,00 EUR</mark>" in html,
        "Nebenkosten 120,00 EUR monatlich" in html,  # Original-Absatz vollständig
        werkstatt.index.fundstelle(f"{MIETVERTRAG}#S2#A1").id in html,
        "aussteller" in html,
    ) == (200, True, True, True, True)


def test_detailseite_zeigt_mehrseitigen_fundstellenbereich(client, stapel, werkstatt):
    from dataclasses import replace
    from dokumentenassistent.typen import SeitenSpanne

    f = werkstatt.index.fundstelle(f"{MIETVERTRAG}#S2#A1")
    grenze = f.text.index("\n")
    werkstatt.index.speichere_fundstellen((replace(f, spannen=(
        SeitenSpanne(2, 0, grenze), SeitenSpanne(3, grenze + 1, len(f.text)))),))
    assert "Seiten 2–3" in client.get(f"/eingang/{stapel[MIETVERTRAG]}").text


# ------------------------------------------------------------- W9/W10: Finden


def test_W9_finden_rendert_belegkarten_mit_datei_seite_wortlaut(client, stapel):
    client.post("/eingang/freigeben", data={"hashes": [stapel[MIETVERTRAG]]})
    seite = client.post("/finden", data={"frage": FRAGE_KALTMIETE})
    html = seite.text
    assert 'data-antwortstuetzung="ungeprueft"' in html
    assert 'Geprüft ist: Jedes Zitat steht wörtlich im Dokument.' in html
    assert (
        seite.status_code,
        'data-zustand="gefunden"' in html,
        MIETVERTRAG in html,
        "Seite 2" in html,
        "Kaltmiete 780,00 EUR" in html,
    ) == (200, True, True, True, True)


def test_W10_nicht_gefunden_ist_ein_eigener_ruhiger_zustand(client, stapel):
    seite = client.post("/finden", data={"frage": FRAGE_OHNE_BELEG})
    html = seite.text
    assert (
        seite.status_code,
        'data-zustand="nicht_gefunden"' in html,
        'data-zustand="gefunden"' in html,
        "Kein Beleg" in html,
    ) == (200, True, False, True)


# ---------------------------------------------------------------- W11: Bestand


def test_W11_bestand_zeigt_ablage_duplikate_konflikte_und_protokoll(client, stapel):
    client.post("/eingang/freigeben", data={"hashes": [stapel[MIETVERTRAG]]})
    html = client.get("/bestand").text
    assert (
        "2024-01-01_Mietvertrag_Meier.pdf" in html,
        "Wohnung Nord" in html,
        KOPIE in html,  # Duplikat
        "Profil bestätigt" in html,  # Protokoll, lesbar formatiert
        "Kopie erzeugt" in html,
    ) == (True,) * 5


# ------------------------------------------------------- W12: Fehler statt 500


def test_W12_providerfehler_wird_als_lesbare_meldung_gezeigt(tmp_path):
    provider = FakeProvider(
        json_antworten=[ProviderFehler("Ollama nicht erreichbar unter http://localhost:11434")]
    )
    client = TestClient(create_app(_werkstatt(tmp_path, provider)))
    _einlesen(client)
    seite = client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    assert (seite.status_code, "Ollama nicht erreichbar" in seite.text) == (200, True)


def test_W12b_unbekannter_hash_ergibt_eine_lesbare_seite(client, stapel):
    seite = client.get("/eingang/gibtsnicht")
    assert (seite.status_code, "gibtsnicht" in seite.text) == (200, True)


# ------------------------------------------------------ W13–W15: Ordner-Wähler


def _leerer_client(tmp_path: Path, provider_laden=None, modelle: Path | None = None) -> TestClient:
    """Server ohne Werkstatt — so startet `main()` ohne --quelle/--ziel."""
    return TestClient(
        create_app(
            None,
            modelle=modelle or tmp_path / "modelle.yaml",
            zuletzt=tmp_path / "zuletzt.json",
            provider_laden=provider_laden,
            provider_suche_laden=lambda: None,
            # Standardwerte statt Lesen: die Tests hier prüfen den Ordner-Wähler,
            # nicht das Laden von modelle.yaml (W14d deckt die fehlende Datei ab).
            sucheinstellungen_laden=Sucheinstellungen,
            # Ebenso die OCR — und zusätzlich, damit hier nie paddleocr geladen wird.
            ocr_laden=OcrEinstellungen,
            seitenuebergreifend_laden=lambda: False,
        ),
        follow_redirects=False,
    )


def _quelle_mit_korpus(tmp_path: Path) -> Path:
    quelle = tmp_path / "Belege 2025"
    quelle.mkdir()
    _schreibe_korpus(quelle)
    return quelle


def test_W13_start_antwortet_ohne_werkstatt(tmp_path):
    seite = _leerer_client(tmp_path).get("/start")
    assert (seite.status_code, 'name="quelle"' in seite.text, "Bestand öffnen" in seite.text) == (200, True, True)


def test_W13b_eingang_ohne_werkstatt_leitet_auf_start(tmp_path):
    antwort = _leerer_client(tmp_path).get("/eingang")
    assert (antwort.status_code, antwort.headers["location"]) == (303, "/start")


def test_W14_start_mit_gueltigen_pfaden_setzt_werkstatt_und_leitet_auf_profil(tmp_path):
    quelle = _quelle_mit_korpus(tmp_path)
    client = _leerer_client(tmp_path, provider_laden=lambda: FakeProvider())
    antwort = client.post("/start", data={"quelle": str(quelle), "ziel": str(tmp_path / "ablage"), "zweck": ZWECK})
    werkstatt = client.app.state.werkstatt
    assert (
        antwort.status_code,
        antwort.headers["location"],
        werkstatt.quelle,
        werkstatt.zielablage,
        ZWECK in client.get("/profil").text,  # Zweck ist vorbelegt
    ) == (303, "/profil", quelle, tmp_path / "ablage", True)


def test_start_uebernimmt_seitenuebergreifendes_chunking_aus_modelle_yaml(tmp_path):
    quelle = _quelle_mit_korpus(tmp_path)
    konfig = tmp_path / 'modelle.yaml'
    konfig.write_text('seitenuebergreifend: true\n')
    client = TestClient(create_app(
        None, modelle=konfig, zuletzt=tmp_path / 'zuletzt.json',
        provider_laden=lambda: FakeProvider(), provider_suche_laden=lambda: None,
        sucheinstellungen_laden=Sucheinstellungen, ocr_laden=OcrEinstellungen,
    ), follow_redirects=False)
    antwort = client.post('/start', data={'quelle': str(quelle), 'ziel': str(tmp_path / 'ablage')})
    assert antwort.status_code == 303
    assert client.app.state.werkstatt.seitenuebergreifend is True


def test_W14b_ungueltige_quelle_ergibt_fehlermeldung_kein_500(tmp_path):
    client = _leerer_client(tmp_path, provider_laden=lambda: FakeProvider())
    seite = client.post("/start", data={"quelle": str(tmp_path / "gibtsnicht"), "ziel": ""})
    assert (seite.status_code, "gibtsnicht" in seite.text, client.app.state.werkstatt) == (200, True, None)


def test_W14c_ziel_in_quelle_ergibt_fehlermeldung(tmp_path):
    quelle = _quelle_mit_korpus(tmp_path)
    client = _leerer_client(tmp_path, provider_laden=lambda: FakeProvider())
    seite = client.post("/start", data={"quelle": str(quelle), "ziel": str(quelle / "sortiert")})
    assert (seite.status_code, "innerhalb" in seite.text, client.app.state.werkstatt) == (200, True, None)


def test_W14d_fehlende_modelldatei_ergibt_fehlermeldung(tmp_path):
    quelle = _quelle_mit_korpus(tmp_path)
    client = _leerer_client(tmp_path, modelle=tmp_path / "fehlt.yaml")
    seite = client.post("/start", data={"quelle": str(quelle), "ziel": ""})
    assert (seite.status_code, "fehlt.yaml" in seite.text, client.app.state.werkstatt) == (200, True, None)


def test_W14e_fehlendes_ocr_extra_meldet_sich_auf_start_statt_still_zu_wechseln(tmp_path):
    """Kein stiller Rückfall auf Tesseract: der Bestand wird gar nicht erst geöffnet."""
    from dokumentenassistent.auslesen import OcrNichtVerfuegbar

    quelle = _quelle_mit_korpus(tmp_path)
    client = _leerer_client(tmp_path, provider_laden=lambda: FakeProvider())

    def bricht_ab():
        raise OcrNichtVerfuegbar("... nachinstallieren: uv sync --extra ocr-paddle")

    client.app.state.ocr_laden = bricht_ab
    seite = client.post("/start", data={"quelle": str(quelle), "ziel": str(tmp_path / "ablage")})
    assert seite.status_code == 200
    assert "uv sync --extra ocr-paddle" in seite.text
    assert client.app.state.werkstatt is None


def test_W15_zuletzt_enthaelt_den_geoeffneten_eintrag(tmp_path):
    quelle = _quelle_mit_korpus(tmp_path)
    client = _leerer_client(tmp_path, provider_laden=lambda: FakeProvider())
    client.post("/start", data={"quelle": str(quelle), "ziel": ""})
    seite = client.get("/start")
    gespeichert = json.loads((tmp_path / "zuletzt.json").read_text(encoding="utf-8"))
    assert (
        gespeichert[0]["quelle"],
        gespeichert[0]["ziel"],
        str(quelle) in seite.text,
        "Zuletzt geöffnet" in seite.text,
    ) == (str(quelle), str(tmp_path / "Belege 2025_sortiert"), True, True)


# -------------------------------------------------- W16: Einordnen im Hintergrund


class Schleuse:
    """Hält den ersten Modellaufruf fest, bis der Test ihn freigibt — so ist
    der Zustand „Job läuft“ deterministisch beobachtbar, ohne zu schlafen."""

    def __init__(self, provider: FakeProvider) -> None:
        self.angekommen = threading.Event()
        self.frei = threading.Event()
        self._echt = provider.generate_json
        provider.generate_json = self._gebremst

    def _gebremst(self, prompt, schema):
        if not self.angekommen.is_set():
            self.angekommen.set()
            self.frei.wait(timeout=10)
        return self._echt(prompt, schema)


@pytest.fixture
def vorbereitet(client):
    """Quelle eingelesen, Profil bestätigt — noch nichts eingeordnet."""
    _einlesen(client)
    client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    client.post("/profil/bestaetigen", data=PROFIL_FORMULAR)


def _job(client):
    return client.app.state.job


def test_W15b_einlesen_kehrt_sofort_zurueck_und_zeigt_den_ocr_fortschritt(
    client, werkstatt, monkeypatch
):
    """Bis 24.09.2026 lief `/profil/einlesen` synchron: der Browser hing die ganze
    OCR-Zeit (gemessen 403 s über 126 echte Dateien, bei einem Scan-Bestand Stunden),
    ohne Balken, ohne Zähler. Kein Modellaufruf — aber der teuerste Schritt je Datei."""
    import threading as th

    from dokumentenassistent import werkstatt as modul

    angekommen, frei = th.Event(), th.Event()
    echt = modul.lies_seiten

    def gebremst(pfad, ocr):
        if not angekommen.is_set():
            angekommen.set()
            frei.wait(timeout=10)
        return echt(pfad, ocr)

    monkeypatch.setattr(modul, "lies_seiten", gebremst)
    antwort = client.post("/profil/einlesen", follow_redirects=False)
    angekommen.wait(timeout=10)
    html = client.get("/profil").text
    job = _job(client)
    laeuft, phase = job.laeuft, job.phase
    frei.set()
    job.thread.join(timeout=30)
    assert (
        antwort.status_code,
        laeuft,
        phase,
        'class="fortschritt"' in html,
        "Auslesen läuft" in html,
        'http-equiv="refresh"' in html,
        # Auslesen ist nicht abbrechbar: es gibt keinen Teilzustand, den ein Abbruch
        # retten würde, und ein Knopf ohne Wirkung wäre eine Lüge.
        "abbrechen" in html,
    ) == (303, True, "auslesen", True, True, True, False)


def test_W15c_nach_dem_auslesen_nennt_die_meldung_das_auslesen_nicht_das_einordnen(client, werkstatt):
    _einlesen(client)
    html = client.get("/profil").text
    assert "Dateien gefunden und ausgelesen" in html
    assert "Vorschläge erzeugt" not in html


def test_W16_einordnen_kehrt_sofort_zurueck_und_zeigt_fortschritt_solange_der_job_laeuft(
    client, werkstatt, vorbereitet
):
    schleuse = Schleuse(werkstatt.provider)
    antwort = client.post("/eingang/einordnen", follow_redirects=False)
    schleuse.angekommen.wait(timeout=10)
    html = client.get("/eingang").text
    laeuft = _job(client).laeuft
    schleuse.frei.set()
    _job(client).thread.join(timeout=10)
    assert (
        antwort.status_code,
        laeuft,
        'class="fortschritt"' in html,
        "Datei 1 von 4" in html,
        MIETVERTRAG in html,
        'http-equiv="refresh"' in html,
        "/eingang/abbrechen" in html,
    ) == (303, True, True, True, True, True, True)


def test_W16b_nach_jobende_zeigt_die_seite_die_vorschlaege(client, werkstatt, vorbereitet):
    client.post("/eingang/einordnen")
    _job(client).thread.join(timeout=10)
    html = client.get("/eingang").text
    job = _job(client)
    assert (
        job.laeuft,
        job.fehler,
        "5 Vorschläge erzeugt" in html,
        'http-equiv="refresh"' in html,
        "2024-01-01_Mietvertrag_Meier.pdf" in html,
    ) == (False, None, True, False, True)


def test_W16c_abbrechen_setzt_abgebrochen_und_laesst_wiederaufnahme_zu(client, werkstatt, vorbereitet):
    schleuse = Schleuse(werkstatt.provider)
    client.post("/eingang/einordnen")
    schleuse.angekommen.wait(timeout=10)
    client.post("/eingang/abbrechen")
    schleuse.frei.set()
    _job(client).thread.join(timeout=10)
    html = client.get("/eingang").text
    assert (
        _job(client).abgebrochen,
        len(werkstatt.index.vorschlaege()),
        "abgebrochen nach 1 von 4" in html,
        "Stapel einordnen" in html,
    ) == (True, 1, True, True)


def test_W16d_zweiter_start_waehrend_des_laufs_startet_keinen_zweiten_job(client, werkstatt, vorbereitet):
    schleuse = Schleuse(werkstatt.provider)
    client.post("/eingang/einordnen")
    schleuse.angekommen.wait(timeout=10)
    erster = _job(client).thread
    antwort = client.post("/eingang/einordnen")
    schleuse.frei.set()
    erster.join(timeout=10)
    assert (antwort.status_code, _job(client).thread is erster, "läuft bereits" in antwort.text) == (200, True, True)


def test_W16e_fehler_im_thread_wird_lesbar_gezeigt_kein_500(client):
    _einlesen(client)  # kein Profil → ProfilFehler im Thread
    client.post("/eingang/einordnen")
    _job(client).thread.join(timeout=10)
    html = client.get("/eingang").text
    assert (_job(client).laeuft, "Kein bestätigtes Profil" in html) == (False, True)


# ---------------------------------------------- W17/W18: Übersicht und Filter

SCANS = "Scans"
VERTRAEGE = "Verträge"


def _schreibe_korpus_mit_ordnern(quelle: Path) -> None:
    """Derselbe Korpus, verteilt: Rechnungen in Scans/, Mietvertrag+Kopie in Verträge/,
    Bild und Anleitung direkt in der Quelle."""
    (quelle / SCANS).mkdir()
    (quelle / VERTRAEGE).mkdir()
    _schreibe_korpus(quelle)
    for name in (RECHNUNG, KORREKTUR):
        (quelle / name).rename(quelle / SCANS / name)
    for name in (MIETVERTRAG, KOPIE):
        (quelle / name).rename(quelle / VERTRAEGE / name)


@pytest.fixture
def client_ordner(tmp_path):
    """Verarbeitungsreihenfolge (nach Pfad): IMG (ocr), Scans/Rechnung (2), Scans/Rechnung (3),
    Untitled, Verträge/Dokument1 Kopie, Verträge/Dokument1 (Duplikat)."""
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    _schreibe_korpus_mit_ordnern(quelle)
    provider = FakeProvider(
        json_antworten=[PROFIL_ANTWORT, EIN_RECHNUNG, EIN_KORREKTUR, EIN_ANLEITUNG, EIN_MIETVERTRAG]
    )
    werkstatt = Werkstatt(
        quelle=quelle, zielablage=tmp_path / "ablage", provider=provider, arbeitsordner=tmp_path / "arbeit"
    )
    client = TestClient(create_app(werkstatt))
    _einlesen(client)
    client.post("/profil/vorschlagen", data={"zweck": ZWECK})
    client.post("/profil/bestaetigen", data=PROFIL_FORMULAR)
    client.post("/eingang/einordnen")
    client.app.state.job.thread.join(timeout=10)
    return client


def _ordnerzeile(html: str, ordner: str) -> str:
    start = html.index(f'data-ordner="{ordner}"')
    return html[start : html.index("</li>", start)]


def _zahlen(ausschnitt: str) -> dict[str, int]:
    return {
        status: int(zahl)
        for status, zahl in re.findall(r'data-status="(\w+)"[^>]*>\s*(\d+)\s*<', ausschnitt)
    }


def _tabelle(html: str) -> str:
    return html[html.index("<tbody>") : html.index("</tbody>")]


def test_W17_uebersicht_zeigt_je_unterordner_die_richtigen_zahlen(client_ordner):
    html = client_ordner.get("/eingang").text
    assert (
        _zahlen(_ordnerzeile(html, "(Quelle)")),
        _zahlen(_ordnerzeile(html, SCANS)),
        _zahlen(_ordnerzeile(html, VERTRAEGE)),
        "6 von 6" in html,  # alle Dateien haben einen Befund — das Duplikat zählt als abgearbeitet
    ) == (
        {"unklar": 1, "ocr_unsicher": 1},
        {"konflikt": 2},
        {"sicher": 1, "duplikat": 1},
        True,
    )


def test_W17b_uebersicht_gesamt_zaehlt_alle_dateien(client_ordner):
    html = client_ordner.get("/eingang").text
    gesamt = html[html.index('class="uebersicht-balken"') : html.index("</nav>", html.index('class="uebersicht-balken"'))]
    assert _zahlen(gesamt) == {"sicher": 1, "unklar": 1, "konflikt": 2, "duplikat": 1, "ocr_unsicher": 1}


def test_W18_filter_status_zeigt_nur_unklare_zeilen(client_ordner):
    tabelle = _tabelle(client_ordner.get("/eingang?status=unklar").text)
    assert (ANLEITUNG in tabelle, RECHNUNG in tabelle, MIETVERTRAG in tabelle) == (True, False, False)


def test_W18b_filter_ordner_zeigt_nur_den_ordner(client_ordner):
    tabelle = _tabelle(client_ordner.get(f"/eingang?ordner={SCANS}").text)
    assert (RECHNUNG in tabelle, KORREKTUR in tabelle, MIETVERTRAG in tabelle, BILD in tabelle) == (
        True, True, False, False,
    )


def test_W18c_freitext_filtert_auf_dateiname(client_ordner):
    tabelle = _tabelle(client_ordner.get("/eingang?suche=rechnung").text)
    assert (RECHNUNG in tabelle, KORREKTUR in tabelle, ANLEITUNG in tabelle, BILD in tabelle) == (
        True, True, False, False,
    )


def test_W18d_filter_kombiniert_leer_zeigt_hinweis_statt_tabelle(client_ordner):
    html = client_ordner.get(f"/eingang?ordner={SCANS}&status=sicher").text
    assert ("Keine Datei passt" in html, "Filter löschen" in html, "<tbody>" in html) == (True, True, False)


def test_W18e_sammelfreigabe_zaehlt_nur_die_gefilterte_sicht(client_ordner):
    html = client_ordner.get(f"/eingang?ordner={VERTRAEGE}").text
    assert 'class="leiste-zahl">(1)</span>' in html


# ------------------------------------------------------- W19: Ordnerbrowser


def _ordner(client, pfad=None):
    """GET /ordner — ohne `pfad` beginnt der Browser im Heimatverzeichnis."""
    antwort = client.get("/ordner", params={} if pfad is None else {"pfad": str(pfad)})
    return antwort, antwort.json()


def test_W19_ordner_listet_nur_unterordner_keine_dateien(tmp_path):
    (tmp_path / "Belege 2025").mkdir()
    (tmp_path / "Archiv").mkdir()
    (tmp_path / "Rechnung.pdf").write_text("x", encoding="utf-8")
    antwort, daten = _ordner(_leerer_client(tmp_path), tmp_path)
    assert (
        antwort.status_code,
        [e["name"] for e in daten["ordner"]],
        daten["pfad"],
    ) == (200, ["Archiv", "Belege 2025"], str(tmp_path.resolve()))


def test_W19b_jeder_eintrag_nennt_seinen_absoluten_pfad(tmp_path):
    (tmp_path / "Belege").mkdir()
    _, daten = _ordner(_leerer_client(tmp_path), tmp_path)
    assert daten["ordner"][0]["pfad"] == str((tmp_path / "Belege").resolve())


def test_W19c_versteckte_ordner_bleiben_unsichtbar(tmp_path):
    (tmp_path / "Belege").mkdir()
    (tmp_path / ".dokumentenassistent").mkdir()
    _, daten = _ordner(_leerer_client(tmp_path), tmp_path)
    assert [e["name"] for e in daten["ordner"]] == ["Belege"]


def test_W19d_symlinks_werden_nicht_verfolgt(tmp_path):
    echt = tmp_path / "Belege"
    echt.mkdir()
    (tmp_path / "Verweis").symlink_to(echt, target_is_directory=True)
    _, daten = _ordner(_leerer_client(tmp_path), tmp_path)
    assert [e["name"] for e in daten["ordner"]] == ["Belege"]


def test_W19e_ohne_pfad_beginnt_der_browser_im_heimatverzeichnis(tmp_path, monkeypatch):
    heim = tmp_path / "heim"
    (heim / "Belege").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(heim))
    _, daten = _ordner(_leerer_client(tmp_path))
    assert (daten["pfad"], [e["name"] for e in daten["ordner"]]) == (
        str(heim.resolve()),
        ["Belege"],
    )


def test_W19f_ein_schritt_nach_oben_ist_moeglich(tmp_path):
    tief = tmp_path / "a" / "b"
    tief.mkdir(parents=True)
    _, daten = _ordner(_leerer_client(tmp_path), tief)
    assert daten["eltern"] == str((tmp_path / "a").resolve())


def test_W19g_die_wurzel_hat_keinen_schritt_nach_oben(tmp_path):
    _, daten = _ordner(_leerer_client(tmp_path), "/")
    assert daten["eltern"] is None


def test_W19h_fehlender_ordner_ergibt_lesbare_meldung_kein_500(tmp_path):
    antwort, daten = _ordner(_leerer_client(tmp_path), tmp_path / "gibtsnicht")
    assert (antwort.status_code, "gibtsnicht" in daten["fehler"], "Traceback" in antwort.text) == (
        400,
        True,
        False,
    )


def test_W19i_datei_statt_ordner_ergibt_lesbare_meldung(tmp_path):
    datei = tmp_path / "Rechnung.pdf"
    datei.write_text("x", encoding="utf-8")
    antwort, daten = _ordner(_leerer_client(tmp_path), datei)
    assert (antwort.status_code, "kein Ordner" in daten["fehler"]) == (400, True)


def test_W19j_ordner_ohne_leseberechtigung_ergibt_lesbare_meldung(tmp_path):
    gesperrt = tmp_path / "gesperrt"
    gesperrt.mkdir()
    gesperrt.chmod(0o000)
    try:
        antwort, daten = _ordner(_leerer_client(tmp_path), gesperrt)
    finally:
        gesperrt.chmod(0o700)
    assert (antwort.status_code, "Leseberechtigung" in daten["fehler"]) == (400, True)


def test_W19k_tilde_und_punkte_loest_der_server_auf(tmp_path, monkeypatch):
    (tmp_path / "heim" / "Belege").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "heim"))
    daten = ansicht.unterordner("~/Belege/..")
    assert (daten["pfad"], [e["name"] for e in daten["ordner"]]) == (
        str((tmp_path / "heim").resolve()),
        ["Belege"],
    )


def test_W19l_leerer_pfad_zaehlt_wie_kein_pfad(tmp_path, monkeypatch):
    (tmp_path / "heim" / "Belege").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "heim"))
    _, daten = _ordner(_leerer_client(tmp_path), "")
    assert daten["pfad"] == str((tmp_path / "heim").resolve())


def test_W19m_jeder_pfad_hat_ein_feld_und_einen_knopf(tmp_path):
    html = _leerer_client(tmp_path).get("/start").text
    assert (
        'name="quelle"' in html,
        'name="ziel"' in html,
        'data-feld="quelle"' in html,
        'data-feld="ziel"' in html,
    ) == (True, True, True, True)


def test_W19o_der_browser_steht_im_dialog_nicht_im_formular(tmp_path):
    """Der Durchklick-Bereich ist ein Fenster über der Seite, kein Abschnitt im Formular."""
    html = _leerer_client(tmp_path).get("/start").text
    assert (
        "<dialog" in html,
        html.index("<dialog") > html.index('id="start"'),
        html.index('id="browser-liste"') > html.index("<dialog"),
        'id="ordnerbrowser"' in html,
    ) == (True, True, True, False)


def test_W19p_leere_felder_nennen_quellordner_und_zielordner(tmp_path):
    html = _leerer_client(tmp_path).get("/start").text
    assert ('placeholder="Quellordner"' in html, 'placeholder="Zielordner"' in html) == (True, True)


def test_W19n_ein_unlesbarer_eintrag_kippt_die_liste_nicht(tmp_path):
    """Ein gesperrter Unterordner darf nur sich selbst kosten, nicht die ganze Liste."""
    (tmp_path / "Belege").mkdir()
    gesperrt = tmp_path / "gesperrt"
    gesperrt.mkdir()
    gesperrt.chmod(0o000)
    try:
        antwort, daten = _ordner(_leerer_client(tmp_path), tmp_path)
    finally:
        gesperrt.chmod(0o700)
    assert (antwort.status_code, "Belege" in [e["name"] for e in daten["ordner"]]) == (200, True)

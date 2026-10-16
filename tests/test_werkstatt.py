"""Stufe 2 · Verdrahtung — V1–V16.

Prüft ausschließlich, dass der Orchestrator die Modul-APIs in der richtigen
Reihenfolge aufruft, die Statusübergänge setzt und jede Entscheidung
protokolliert. Keine Fachlogik wird hier erneut geprüft (das tun M1–M11).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from dokumentenassistent.profil import ProfilFehler
from dokumentenassistent.provider import SchemaFehler
from dokumentenassistent.werkstatt import Werkstatt
from tests.conftest import FakeProvider, schreibe_bild, schreibe_text_pdf

ZWECK = "Steuererklärung 2025"

MIETVERTRAG = "Dokument1 Kopie.pdf"  # bytegleiche Kopie, steht nach Pfadsortierung VOR Dokument1.pdf
KOPIE = "Dokument1.pdf"  # zweiter Fundort desselben Hashes → Duplikat
BILD = "IMG_8831.jpg"
RECHNUNG = "Rechnung (2).pdf"
KORREKTUR = "Rechnung (3).pdf"
ANLEITUNG = "Untitled.pdf"

# Verarbeitungsreihenfolge = Reihenfolge von erfasse_ordner (sortiert nach Pfad).
EINGEORDNET = (MIETVERTRAG, BILD, RECHNUNG, KORREKTUR, ANLEITUNG)

PROFIL_ANTWORT = {
    "kategorien": ["Wohnung Nord", "Einkommen"],
    "dokumenttypen": ["Rechnung", "Mietvertrag"],
    "felder": ["datum", "aussteller", "betrag", "rechnungsnummer"],
    "namensschema": "{datum}_{typ}_{aussteller}",
}


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
        _feld("rechnungsnummer", "2025-0815-K", f"{KORREKTUR}#S1#A1", "Korrekturrechnung Nr. 2025-0815-K"),
    ],
}
EIN_ANLEITUNG = {
    "kategorie": "unbekannt",
    "typ": "unbekannt",
    "begruendung": "Bedienungsanleitung ohne Bezug zum Zweck",
    "felder": [],
}

ANTWORT_KALTMIETE = f"Die Kaltmiete beträgt 780,00 EUR [{MIETVERTRAG}#S2#A1]."
# 21.09.: Suche ist dense allein mit Kosinus-Schwelle 0.49. Der Bag-of-Words-FakeProvider gibt für
# „Wie hoch ist die Kaltmiete?" gegen den Kaltmiete-Absatz nur 0.105; vier Treffer-Wörter ergeben 0.566.
FRAGE_KALTMIETE = "Kaltmiete und Nebenkosten monatlich in EUR?"
FRAGE_OHNE_BELEG = "Welchen Kilometerstand hat das Auto?"


def _schreibe_korpus(quelle: Path) -> None:
    schreibe_text_pdf(
        quelle / RECHNUNG,
        [
            (
                "Rechnung Nr. 2025-0815\n"
                "Rechnungsdatum 14.05.2025\n"
                "Heizung Sanitär Krause GmbH\n"
                "Rechnungsbetrag 1.240,00 EUR\n"
                "Leistung: Reparatur Heizung, Musterstraße 3, Wohnung Nord"
            )
        ],
    )
    schreibe_text_pdf(
        quelle / KORREKTUR,
        [
            (
                "Korrekturrechnung Nr. 2025-0815-K\n"
                "Korrektur zu Rechnung Nr. 2025-0815\n"
                "Rechnungsdatum 02.06.2025\n"
                "Heizung Sanitär Krause GmbH\n"
                "Rechnungsbetrag 1.180,00 EUR"
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
                "Bedienungsanleitung Router Modell FB-7530\n"
                "Kapitel 1 Inbetriebnahme\n"
                "Stecken Sie das Netzteil ein und warten Sie auf die Power-LED."
            )
        ],
    )


@pytest.fixture
def werkstatt(tmp_path):
    """Mini-Korpus, Zielablage und Werkstatt mit eingereihten FakeProvider-Antworten.

    Verarbeitungsreihenfolge (= sortiert nach Pfad, so liefert sie `erfassen()`):

    | # | Datei                | Rolle                    | Modellaufruf |
    |---|----------------------|--------------------------|--------------|
    | 1 | Dokument1 Kopie.pdf  | Mietvertrag, 3 Seiten    | ja           |
    | 2 | Dokument1.pdf        | Duplikat (bytegleich)    | nein         |
    | 3 | IMG_8831.jpg         | unscharf → ocr_unsicher  | nein         |
    | 4 | Rechnung (2).pdf     | Rechnung 1.240,00 EUR    | ja           |
    | 5 | Rechnung (3).pdf     | Korrektur 1.180,00 EUR   | ja           |
    | 6 | Untitled.pdf         | Bedienungsanleitung      | ja           |

    " Dokument1 Kopie.pdf" sortiert vor "Dokument1.pdf" (Leerzeichen < Punkt),
    also ist die Kopie der erste Fundort und "Dokument1.pdf" das Duplikat.
    Duplikate und ocr_unsichere Dateien bekommen KEINEN Modellaufruf; deshalb
    stehen in der JSON-Schlange genau fünf Antworten: erst das Profil, dann die
    vier Einordnungen in Verarbeitungsreihenfolge.
    """
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    _schreibe_korpus(quelle)
    provider = FakeProvider(
        json_antworten=[PROFIL_ANTWORT, EIN_MIETVERTRAG, EIN_RECHNUNG, EIN_KORREKTUR, EIN_ANLEITUNG],
        text_antworten=[ANTWORT_KALTMIETE],
    )
    return Werkstatt(
        quelle=quelle,
        zielablage=tmp_path / "ablage",
        provider=provider,
        arbeitsordner=tmp_path / "arbeit",
    )


def _protokoll(w: Werkstatt) -> list[dict]:
    pfad = w.arbeitsordner / ".dokumentenassistent" / "protokoll.jsonl"
    if not pfad.exists():
        return []
    return [json.loads(zeile) for zeile in pfad.read_text(encoding="utf-8").splitlines()]


def _vorbereiten(w: Werkstatt) -> dict[str, str]:
    """Aufbau für alles ab V4: erfassen → auslesen → Profil bestätigen. Gibt Name → Hash."""
    dateien = w.erfassen()
    w.auslesen()
    w.profil_bestaetigen(w.profil_vorschlagen(ZWECK))
    return {d.name: d.hash for d in dateien}


def _quelle_hashes(quelle: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(quelle.rglob("*"))
        if p.is_file()
    }


def test_V1_erfassen_registriert_alle_und_markiert_duplikat(werkstatt):
    dateien = werkstatt.erfassen()
    duplikate = [e for e in _protokoll(werkstatt) if e["art"] == "duplikat"]
    assert (
        [d.name for d in dateien],
        all(werkstatt.index.datei(d.hash) is not None for d in dateien),
        [Path(p).name for p in duplikate[0]["pfade"]],
    ) == (
        [MIETVERTRAG, KOPIE, BILD, RECHNUNG, KORREKTUR, ANLEITUNG],
        True,
        [MIETVERTRAG, KOPIE],
    )


def test_V2_auslesen_liefert_fundstellen_je_datei_und_markiert_ocr_unsicher(werkstatt):
    hashes = {d.name: d.hash for d in werkstatt.erfassen()}
    je_datei = werkstatt.auslesen()
    assert (
        {name: len(je_datei[hashes[name]]) for name in EINGEORDNET},
        werkstatt.ocr_unsichere_hashes,
    ) == (
        {MIETVERTRAG: 3, BILD: 0, RECHNUNG: 1, KORREKTUR: 1, ANLEITUNG: 1},
        frozenset({hashes[BILD]}),
    )


def test_auslesen_reicht_opt_in_fuer_seitenuebergreifende_fundstellen_weiter(tmp_path, monkeypatch):
    from dokumentenassistent.typen import Datei, Seite
    from dokumentenassistent import werkstatt as modul

    w = Werkstatt(quelle=tmp_path / "quelle", zielablage=tmp_path / "ziel",
                 provider=FakeProvider(), arbeitsordner=tmp_path / "arbeit",
                 seitenuebergreifend=True)
    datei = Datei(hash="hash", pfad=tmp_path / "quelle" / "a.pdf", name="a.pdf", groesse=1)
    w.index.registriere(datei, "unklar")
    monkeypatch.setattr(modul, "lies_seiten", lambda *_: (
        Seite(1, "Erster Teil", False, None), Seite(2, "zweiter Teil", False, None)))
    monkeypatch.setattr(w, "_bette_nach_ein", lambda: None)

    result = w.auslesen()[datei.hash]
    assert len(result) == 1
    assert result[0].seiten == (1, 2)
    assert w.index.fundstelle(result[0].id).seiten == (1, 2)


def test_V2b_auslesen_meldet_fortschritt_je_datei(werkstatt):
    """OCR ist die zweitlängste Phase (gemessen 24.09.2026: 403 s über 126 echte Dateien,
    bei einem Bestand aus Scans Stunden) und hatte als einzige gar keine Rückmeldung —
    weder in der Oberfläche noch im Skript."""
    werkstatt.erfassen()
    gemeldet: list[tuple[int, int, str]] = []
    werkstatt.auslesen(fortschritt=lambda *args: gemeldet.append(args))
    assert [(e, g) for e, g, _ in gemeldet] == [(i, 5) for i in range(5)]
    # Vor jeder Datei gemeldet, mit ihrem Namen — nicht nach ihr, sonst hängt die
    # Anzeige während des längsten Schritts auf der vorigen Datei.
    assert sorted(name for _, _, name in gemeldet) == sorted(EINGEORDNET)


def test_V2c_auslesen_macht_jede_datei_durchsuchbar_auch_ohne_einordnung(werkstatt):
    """Gemessen 24.09.2026 am echten Bestand: 31 von 85 Fragen waren unbeantwortbar,
    weil ihre Datei keine Kategorie bekommen hatte — ohne Ablage kein Embedding, ohne
    Embedding unsichtbar für jede Suche. Auffindbarkeit und Einordnung sind zwei
    verschiedene Dinge: gerade das unsortierte Dokument will man finden können.
    Die Einordnung bleibt, was sie ist — sie entscheidet über die Ablage, nicht über
    den Index."""
    werkstatt.erfassen()
    werkstatt.auslesen()
    durchsuchbar = werkstatt.index.durchsuchbare_fundstellen()
    # Kein Profil, keine Einordnung, keine Freigabe — trotzdem alles auffindbar.
    assert {f.datei_name for f, _ in durchsuchbar} == {MIETVERTRAG, RECHNUNG, KORREKTUR, ANLEITUNG}
    assert all(len(v) > 0 for _, v in durchsuchbar)


def test_V3_profil_vorschlagen_nutzt_stichprobe_und_speichert_nach_bestaetigung(werkstatt):
    werkstatt.erfassen()
    werkstatt.auslesen()
    profil = werkstatt.profil_vorschlagen(ZWECK)
    pfad = werkstatt.arbeitsordner / ".dokumentenassistent" / "profil.yaml"
    vorher = pfad.exists()
    werkstatt.profil_bestaetigen(profil)
    assert (
        "Kaltmiete 780,00 EUR" in werkstatt.provider.aufrufe[0][1],
        vorher,
        pfad.exists(),
    ) == (True, False, True)


def test_V4_einordnen_erzeugt_je_datei_einen_vorschlag_ausser_duplikat(werkstatt):
    _vorbereiten(werkstatt)
    vorschlaege = werkstatt.einordnen()
    assert tuple(v.datei_name for v in vorschlaege) == EINGEORDNET


def test_V5_einordnen_erzeugt_konflikt_rechnung_korrektur(werkstatt):
    hashes = _vorbereiten(werkstatt)
    vorschlaege = {v.datei_name: v for v in werkstatt.einordnen()}
    konflikte = werkstatt.index.konflikte(offen=True)
    assert (
        len(konflikte),
        konflikte[0].feld,
        konflikte[0].vorschlag,
        sorted((konflikte[0].hash_a, konflikte[0].hash_b)),
        (vorschlaege[RECHNUNG].status, vorschlaege[KORREKTUR].status),
    ) == (
        1,
        "betrag",
        "ersetzt",
        sorted((hashes[RECHNUNG], hashes[KORREKTUR])),
        ("konflikt", "konflikt"),
    )


def test_V6_bedienungsanleitung_ist_unklar(werkstatt):
    _vorbereiten(werkstatt)
    vorschlaege = {v.datei_name: v for v in werkstatt.einordnen()}
    assert (vorschlaege[ANLEITUNG].status, vorschlaege[ANLEITUNG].kategorie) == ("unklar", None)


def test_V7_freigeben_ignoriert_unklare_und_konfliktbehaftete(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    pfade = werkstatt.freigeben(tuple(hashes[name] for name in EINGEORDNET))
    uebersprungen = {e["name"]: e["grund"] for e in _protokoll(werkstatt) if e["art"] == "uebersprungen"}
    assert ([p.name for p in pfade], sorted(uebersprungen)) == (
        ["2024-01-01_Mietvertrag_Meier.pdf"],
        [BILD, RECHNUNG, KORREKTUR, ANLEITUNG],
    )


def test_V8_freigeben_nach_konfliktentscheidung_klappt(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.entscheide_konflikt(werkstatt.index.konflikte(offen=True)[0].id, "ersetzt")
    pfade = werkstatt.freigeben((hashes[RECHNUNG], hashes[KORREKTUR]))
    assert [p.name for p in pfade] == [
        "2025-05-14_Rechnung_Krause.pdf",
        "2025-06-02_Rechnung_Krause.pdf",
    ]


def test_V9_freigeben_laesst_quelle_unveraendert(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    vorher = _quelle_hashes(werkstatt.quelle)
    werkstatt.freigeben(tuple(hashes[name] for name in EINGEORDNET))
    assert _quelle_hashes(werkstatt.quelle) == vorher


def test_V10_frage_findet_auch_ohne_freigabe(werkstatt):
    """Bis 24.09.2026 hieß dieser Test `..._nur_bestaetigte` und schrieb fest, dass
    eine Datei erst NACH der Ablage auffindbar ist. Das war eine Architekturentscheidung,
    keine Notwendigkeit, und sie hat am echten Bestand 31 von 85 Fragen gekostet: wer
    keine Kategorie bekam, war unsichtbar. Seither gilt die Trennung — die Einordnung
    entscheidet über die ABLAGE, nicht über den INDEX. Die Freigabe ändert an der
    Auffindbarkeit nichts mehr; sie kopiert."""
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    # Zwei Antworten in der Schlange: seit der Trennung gelingt schon die ERSTE Frage,
    # vorher lief sie ins "nicht gefunden" und verbrauchte keinen Modellaufruf.
    werkstatt.provider.text_antworten.append(ANTWORT_KALTMIETE)
    vorher = werkstatt.frage(FRAGE_KALTMIETE)
    werkstatt.freigeben((hashes[MIETVERTRAG],))
    nachher = werkstatt.frage(FRAGE_KALTMIETE)
    assert (vorher.status, vorher.karten[0].fundstelle.id, nachher.status) == (
        "gefunden",
        werkstatt.index.fundstelle(f"{MIETVERTRAG}#S2#A1").id,
        "gefunden",
    )


def test_V11_frage_zu_fehlendem_dokument_ist_nicht_gefunden(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.freigeben((hashes[MIETVERTRAG],))
    antwort = werkstatt.frage(FRAGE_OHNE_BELEG)
    assert (antwort.status, antwort.karten) == ("nicht_gefunden", ())


def test_V10b_frage_nutzt_provider_suche_wenn_gesetzt(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.freigeben((hashes[MIETVERTRAG],))
    provider_suche = FakeProvider(text_antworten=[ANTWORT_KALTMIETE])
    werkstatt.provider_suche = provider_suche
    werkstatt.frage(FRAGE_KALTMIETE)
    assert ("text", ) not in [a[:1] for a in werkstatt.provider.aufrufe]
    assert [a[0] for a in provider_suche.aufrufe] == ["text"]


def test_V10c_frage_reicht_sucheinstellungen_an_suche_durch(werkstatt, monkeypatch, tmp_path):
    """Die Werkstatt entscheidet nichts über Reranker/top_n — sie reicht durch, was aus
    modelle.yaml kam. Ohne Angabe gelten die Standardwerte (heutiges Verhalten)."""
    from dokumentenassistent import werkstatt as werkstatt_modul
    from dokumentenassistent.provider import Sucheinstellungen
    from dokumentenassistent.typen import Antwort

    gesehen: dict = {}

    def fake_suche(frage, paare, provider, **kwargs):
        gesehen.update(kwargs)
        return Antwort(status="nicht_gefunden", text="", karten=())

    monkeypatch.setattr(werkstatt_modul, "suche", fake_suche)
    werkstatt.frage("egal")
    assert (gesehen["reranker"], gesehen["rerank_k"], gesehen["top_n"]) == (None, 20, 8)

    class FakeReranker:
        def bewerte(self, frage, texte):
            return [0.0] * len(texte)

    reranker = FakeReranker()
    mit = Werkstatt(
        quelle=werkstatt.quelle,
        zielablage=werkstatt.zielablage,
        provider=werkstatt.provider,
        arbeitsordner=tmp_path / "arbeit2",
        sucheinstellungen=Sucheinstellungen(reranker=reranker, rerank_k=30, top_n=12),
    )
    mit.frage("egal")
    assert (gesehen["reranker"], gesehen["rerank_k"], gesehen["top_n"]) == (reranker, 30, 12)


def test_V12_korrigiere_ueberschreibt_vorschlag_und_protokolliert_mensch(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    korrigiert = werkstatt.korrigiere(
        hashes[ANLEITUNG], kategorie="Wohnung Nord", zielname="2025-01-01_Anleitung_FB-7530.pdf"
    )
    letzter = _protokoll(werkstatt)[-1]
    assert (
        korrigiert.status,
        korrigiert.kategorie,
        korrigiert.zielname,
        letzter["art"],
        letzter["quelle"],
    ) == ("sicher", "Wohnung Nord", "2025-01-01_Anleitung_FB-7530.pdf", "korrektur", "mensch")


def test_V13_protokoll_enthaelt_jede_entscheidung_in_reihenfolge(werkstatt):
    hashes = _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.entscheide_konflikt(werkstatt.index.konflikte(offen=True)[0].id, "ersetzt")
    werkstatt.freigeben((hashes[MIETVERTRAG],))
    werkstatt.frage(FRAGE_KALTMIETE)
    # Sieben "vorschlag", nicht fünf: seit 24.09.2026 speichert `einordnen` jede Datei
    # sofort (fünf Rohstände), und der Konfliktdurchgang schreibt die beiden strittigen
    # danach erneut. Das Protokoll bildet damit ab, was wirklich passiert ist —
    # "erst sicher, dann konflikt" ist eine Entscheidung und gehört hinein.
    assert [e["art"] for e in _protokoll(werkstatt)] == [
        "duplikat",
        "profil_bestaetigt",
        *["vorschlag"] * 5,
        *["vorschlag"] * 2,
        "konflikt_entschieden",
        "freigabe",
        "frage",
    ]


def test_V14_einordnen_vor_profil_ergibt_fehler(werkstatt):
    werkstatt.erfassen()
    werkstatt.auslesen()
    with pytest.raises(ProfilFehler, match="Profil"):
        werkstatt.einordnen()


def test_V15_freigeben_unbekannter_hash_ergibt_fehler(werkstatt):
    _vorbereiten(werkstatt)
    werkstatt.einordnen()
    with pytest.raises(ValueError, match="gibtsnicht"):
        werkstatt.freigeben(("gibtsnicht",))


def test_V16_providerfehler_beim_einordnen_stoppt_nicht_den_stapel(werkstatt):
    _vorbereiten(werkstatt)
    # Nach dem Profilaufruf steht die Einordnung von Rechnung (2).pdf an Position 1.
    werkstatt.provider.json_antworten[1] = SchemaFehler("Ollama weg")
    vorschlaege = {v.datei_name: v for v in werkstatt.einordnen()}
    assert (
        vorschlaege[RECHNUNG].status,
        "Ollama weg" in vorschlaege[RECHNUNG].begruendung,
        [vorschlaege[name].status for name in (MIETVERTRAG, KORREKTUR, ANLEITUNG)],
    ) == ("unklar", True, ["sicher", "sicher", "unklar"])


# --- Nachlegen (Befund 19.09.: einordnen schickte jede Datei bei jedem Durchlauf erneut ans Modell)


def test_V17_zweites_einordnen_ruft_kein_modell_und_behaelt_vorschlaege(werkstatt):
    _vorbereiten(werkstatt)
    erste = {v.datei_name: v.status for v in werkstatt.einordnen()}
    assert werkstatt.provider.json_antworten == []  # Schlange leer: jeder weitere Modellaufruf würde werfen
    zweite = {v.datei_name: v.status for v in werkstatt.einordnen()}
    assert zweite == erste


def test_V18_nachgelegte_datei_bekommt_genau_einen_modellaufruf(werkstatt):
    _vorbereiten(werkstatt)
    werkstatt.einordnen()
    from tests.conftest import schreibe_text_pdf
    schreibe_text_pdf(werkstatt.quelle / "Beleg_neu.pdf", ["Spendenquittung 250,00 EUR\nTierschutzverein Neustadt e.V."])
    werkstatt.erfassen(); werkstatt.auslesen()
    werkstatt.provider.json_antworten.append({**EIN_ANLEITUNG, "kategorie": "Sonstiges"})
    vorschlaege = {v.datei_name: v for v in werkstatt.einordnen()}
    assert ("Beleg_neu.pdf" in vorschlaege, werkstatt.provider.json_antworten) == (True, [])


def test_V19_entschiedener_konflikt_wird_beim_zweiten_einordnen_nicht_wieder_geoeffnet(werkstatt):
    _vorbereiten(werkstatt)
    werkstatt.einordnen()
    werkstatt.entscheide_konflikt(werkstatt.index.konflikte(offen=True)[0].id, "ersetzt")
    werkstatt.einordnen()
    assert werkstatt.index.konflikte(offen=True) == ()


# --- Fortschritt und Abbruch (Hintergrundjob der Web-Oberfläche)


def test_V20_fortschritt_wird_je_modellaufruf_mit_steigendem_zaehler_gerufen(werkstatt):
    _vorbereiten(werkstatt)
    gerufen: list[tuple[int, int, str]] = []
    werkstatt.einordnen(fortschritt=lambda erledigt, gesamt, name: gerufen.append((erledigt, gesamt, name)))
    # Duplikat und ocr_unsicher gehen nicht ans Modell: vier Aufrufe, gesamt = 4.
    assert gerufen == [
        (0, 4, MIETVERTRAG),
        (1, 4, RECHNUNG),
        (2, 4, KORREKTUR),
        (3, 4, ANLEITUNG),
    ]


def test_V21_abbruch_nach_erster_datei_und_wiederaufnahme_rechnet_nichts_doppelt(werkstatt):
    import threading

    _vorbereiten(werkstatt)
    abbruch = threading.Event()
    erste = werkstatt.einordnen(fortschritt=lambda *_: abbruch.set(), abbruch=abbruch)
    abgebrochen = [e for e in _protokoll(werkstatt) if e["art"] == "einordnen_abgebrochen"]
    zweite = werkstatt.einordnen()
    assert (
        [v.datei_name for v in erste],
        (abgebrochen[0]["erledigt"], abgebrochen[0]["gesamt"]),
        tuple(v.datei_name for v in zweite),
        werkstatt.provider.json_antworten,  # Schlange leer: die erste Datei wurde nicht neu gerechnet
    ) == ([MIETVERTRAG], (1, 4), EINGEORDNET, [])


def test_V22_absturz_mitten_im_stapel_laesst_die_fertigen_vorschlaege_im_index(werkstatt):
    """Gemessen 24.09.2026: 63 min Einordnen am echten Bestand standen 63 min lang
    NICHT auf der Platte — `einordnen` schrieb erst nach der letzten Datei. Ein
    Absturz (kein ProviderFehler, den M7 abfängt) hätte alles gekostet."""
    _vorbereiten(werkstatt)
    werkstatt.provider.json_antworten[1] = RuntimeError("Prozess weg")
    with pytest.raises(RuntimeError):
        werkstatt.einordnen()
    # MIETVERTRAG lief durchs Modell, IMG_8831.jpg ist ocr_unsicher und braucht keins —
    # beide stehen im Index, obwohl der Stapel bei der dritten Datei gestorben ist.
    assert sorted(v.datei_name for v in werkstatt.index.vorschlaege()) == sorted(
        [MIETVERTRAG, "IMG_8831.jpg"]
    )


# ------------------------------------------------- OCR-Einstellungen durchreichen (24.09.2026)


def test_V23_werkstatt_reicht_die_ocr_einstellungen_an_lies_seiten_durch(werkstatt, monkeypatch):
    """Die Werkstatt entscheidet nichts an der OCR — sie reicht durch, was modelle.yaml sagt."""
    from dokumentenassistent import werkstatt as modul
    from dokumentenassistent.auslesen import OcrEinstellungen

    gesehen: list[OcrEinstellungen] = []
    monkeypatch.setattr(
        modul, "lies_seiten", lambda pfad, ocr: gesehen.append(ocr) or ()
    )
    werkstatt.ocr = OcrEinstellungen(engine="paddleocr", sprache="german", schwelle=0.80)
    werkstatt.erfassen()
    werkstatt.auslesen()
    assert set(gesehen) == {werkstatt.ocr}


def test_V24_schwelle_kommt_aus_den_einstellungen_nicht_aus_dem_code(werkstatt):
    """Dieselbe Datei, andere Schwelle, anderes Urteil — sonst wäre die Schwelle wirkungslos."""
    from dokumentenassistent.auslesen import OcrEinstellungen

    hashes = {d.name: d.hash for d in werkstatt.erfassen()}
    werkstatt.ocr = OcrEinstellungen(schwelle=0.0)
    werkstatt.auslesen()
    ohne_schwelle = werkstatt.ocr_unsichere_hashes
    werkstatt.ocr = OcrEinstellungen(schwelle=0.6)
    werkstatt.auslesen()
    assert (ohne_schwelle, werkstatt.ocr_unsichere_hashes) == (frozenset(), frozenset({hashes[BILD]}))


def test_V25_ohne_argument_bleibt_es_bei_tesseract_und_null_komma_sechs(werkstatt):
    assert (werkstatt.ocr.engine, werkstatt.ocr.schwelle) == ("tesseract", 0.6)

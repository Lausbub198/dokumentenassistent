import json
import threading
from pathlib import Path
import pytest
from dokumentenassistent.index import Index
from dokumentenassistent.typen import Datei, Fundstelle, Vorschlag, Feld, Beleg, Konflikt

D = Datei(hash="h1", pfad=Path("/q/a.pdf"), name="a.pdf", groesse=3)
F = Fundstelle(id="a.pdf#S1#A1", datei_hash="h1", datei_name="a.pdf", seite=1, absatz=1, text="Betrag 10 EUR")
V = Vorschlag(datei_hash="h1", datei_name="a.pdf", kategorie="Nord", typ="Rechnung", felder=(), zielname="2025_R.pdf", status="sicher")


def test_M5_G1_legt_dateien_an(tmp_path):
    Index(tmp_path)
    assert (tmp_path / ".dokumentenassistent" / "index.sqlite").exists()


def test_M5_G2_registrieren_und_lesen(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "sicher")
    assert ix.datei("h1") == D


def test_M5_G3_registrieren_ist_idempotent(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "sicher"); ix.registriere(D, "sicher")
    assert len(ix.vorschlaege()) == 0 and ix.datei("h1") == D


def test_M5_G4_fundstellen_je_datei(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "sicher"); ix.speichere_fundstellen((F,))
    assert ix.fundstellen("h1") == (F,)


def test_M5_G5_fundstelle_per_id(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "sicher"); ix.speichere_fundstellen((F,))
    assert ix.fundstelle("a.pdf#S1#A1") == F


def test_M5_G6_vorschlag_wird_je_hash_ersetzt(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "sicher")
    ix.speichere_vorschlag(V); ix.speichere_vorschlag(V.__class__(**{**V.__dict__, "kategorie": "Sued"}))
    assert [v.kategorie for v in ix.vorschlaege()] == ["Sued"]


def test_M5_G7_konflikt_offen_filter(tmp_path):
    ix = Index(tmp_path)
    b = Beleg("a.pdf#S1#A1", "10 EUR")
    k = Konflikt(id="k1", feld="betrag", hash_a="h1", hash_b="h2", wert_a="10", wert_b="12", beleg_a=b, beleg_b=b, vorschlag="ersetzt")
    ix.speichere_konflikt(k); ix.speichere_konflikt(k.__class__(**{**k.__dict__, "id": "k2", "entscheidung": "ersetzt"}))
    assert [x.id for x in ix.konflikte(offen=True)] == ["k1"]


def test_M5_G8_durchsuchbar_ist_unabhaengig_von_der_ablage(tmp_path):
    """Bis 24.09.2026 hiess dieser Test `embeddings_nur_fuer_bestaetigte` und schrieb
    fest, dass nur abgelegte Dateien auffindbar sind. Am echten Bestand kostete das
    31 von 85 Fragen. Was ein Embedding hat, ist durchsuchbar -- die Ablage ist eine
    andere Entscheidung."""
    ix = Index(tmp_path); ix.registriere(D, "sicher"); ix.speichere_fundstellen((F,))
    assert ix.fundstellen_ohne_embedding() == (F,)
    ix.speichere_embeddings(((F.id, [0.1, 0.2]),), modell_revision='synthetic-v1', erwartete_texte={F.id: F.text})
    assert ix.fundstellen_ohne_embedding() == ()
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)
    ix.markiere_bestaetigt("h1", Path("/z/2025_R.pdf"))
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)  # Ablage aendert nichts


def test_M5_G9_protokoll_ist_append_only_jsonl(tmp_path):
    ix = Index(tmp_path); ix.protokolliere("freigabe", hash="h1"); ix.protokolliere("freigabe", hash="h2")
    zeilen = (tmp_path / ".dokumentenassistent" / "protokoll.jsonl").read_text().splitlines()
    assert [json.loads(z)["hash"] for z in zeilen] == ["h1", "h2"]


def test_M5_G10_protokoll_hat_zeitstempel(tmp_path):
    ix = Index(tmp_path); ix.protokolliere("x")
    z = json.loads((tmp_path / ".dokumentenassistent" / "protokoll.jsonl").read_text())
    assert "zeit" in z and z["art"] == "x"


def test_M5_B1_unbekannter_hash_ergibt_none(tmp_path):
    assert Index(tmp_path).datei("nope") is None


def test_M5_B2_fundstelle_ohne_datei_ergibt_fehler(tmp_path):
    with pytest.raises(ValueError, match="nicht registriert"):
        Index(tmp_path).speichere_fundstellen((F,))


def test_M5_B3_index_ueberlebt_neuoeffnen(tmp_path):
    Index(tmp_path).registriere(D, "sicher")
    assert Index(tmp_path).datei("h1") == D


def test_M5_G11_setze_status_und_status(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "unklar"); ix.setze_status("h1", "ocr_unsicher")
    assert ix.status("h1") == "ocr_unsicher"


def test_M5_G12_duplikat_wird_getrennt_gefuehrt(tmp_path):
    ix = Index(tmp_path); ix.registriere(D, "unklar")
    ix.registriere_duplikat(Datei(hash="h1", pfad=Path("/q/a Kopie.pdf"), name="a Kopie.pdf", groesse=3))
    assert ([d.name for d in ix.duplikate()], [d.name for d in ix.dateien()]) == (["a Kopie.pdf"], ["a.pdf"])


def test_M5_G13_protokoll_lesen_liefert_zeilen_in_reihenfolge(tmp_path):
    ix = Index(tmp_path); ix.protokolliere("a", n=1); ix.protokolliere("b", n=2)
    assert [z["art"] for z in ix.protokoll()] == ["a", "b"]


def test_M5_B4_setze_status_unbekannter_hash_ergibt_fehler(tmp_path):
    with pytest.raises(ValueError, match="nicht registriert"):
        Index(tmp_path).setze_status("nope", "unklar")


def test_M5_B5_leeres_protokoll_ergibt_leeres_tupel(tmp_path):
    assert Index(tmp_path).protokoll() == ()


def test_M5_G14_gleichzeitiger_zugriff_aus_zwei_threads(tmp_path):
    """Die Web-Oberflaeche liest die Seite, waehrend der Einordnen-Thread schreibt.
    Eine ungeschuetzte sqlite3-Verbindung teilt ihren Statement-Cache zwischen beiden
    und quittiert das mit `InterfaceError: bad parameter or other API misuse`."""
    ix = Index(tmp_path)
    for i in range(50):
        ix.registriere(Datei(hash=f"h{i}", pfad=Path(f"/q/{i}.pdf"), name=f"{i}.pdf", groesse=i + 1), "unklar")
    fehler: list[BaseException] = []
    los = threading.Barrier(2)

    def schreibe():
        los.wait()
        try:
            for i in range(300):
                ix.setze_status(f"h{i % 50}", "sicher" if i % 2 else "unklar")
        except BaseException as f:  # noqa: BLE001 — der Test meldet jeden Fehler
            fehler.append(f)

    def lies():
        los.wait()
        try:
            for i in range(300):
                assert ix.datei(f"h{i % 50}") is not None
                ix.dateien()
        except BaseException as f:  # noqa: BLE001
            fehler.append(f)

    threads = [threading.Thread(target=schreibe), threading.Thread(target=lies)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert fehler == []

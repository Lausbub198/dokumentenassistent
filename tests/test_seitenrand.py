from dokumentenassistent.seitenrand import bereinige_seiten
from dokumentenassistent.typen import Seite


def _seiten(*texte, per_ocr=False):
    return tuple(Seite(i, t, per_ocr, 0.9 if per_ocr else None, "x", "1") for i, t in enumerate(texte, 1))


_INHALT = ("Die Miete ist monatlich im Voraus zu zahlen.", "Schönheitsreparaturen trägt der Mieter.",
           "Die Kaution beträgt drei Monatsmieten.", "Tierhaltung bedarf der Zustimmung.")


def _doc(n, kopf="Hausverwaltung Sommer & Partner · Mietvertrag Wohnung Nord"):
    return _seiten(*(f"{kopf}\n\n{_INHALT[i % 4]}\nNoch eine Zeile zu Punkt {i}.\n\nSeite {i + 1} von {n}\n"
                     for i in range(n)))


def test_wiederkehrende_kopfzeile_und_seitenzahl_werden_entfernt():
    raus = bereinige_seiten(_doc(4))
    assert all("Hausverwaltung" not in s.text and "von 4" not in s.text for s in raus)
    assert all(_INHALT[s.nummer - 1] in s.text for s in raus)


def test_seitenzahl_als_strich_oder_bruch_wird_entfernt():
    raus = bereinige_seiten(_seiten("Text eins.\n\n- 1 -", "Text zwei.\n\n2/3", "Text drei.\n\n3"))
    assert [s.text.strip() for s in raus] == ["Text eins.", "Text zwei.", "Text drei."]


def test_zahl_mitten_auf_der_seite_bleibt():
    raus = bereinige_seiten(_seiten("Kopf\nBetrag:\n780\nweiter im Text\nmehr Text\nnoch mehr\nEnde",
                                    "Kopf\nzweite Seite\nTextzeile\nTextzeile\nTextzeile\nEnde zwei"))
    assert "780" in raus[0].text


def test_zeile_auf_zu_wenigen_seiten_bleibt():
    texte = ["Sondervermerk Wasserschaden\nText A." if i < 2 else f"Text {i}." for i in range(5)]
    raus = bereinige_seiten(_seiten(*texte))
    assert sum("Sondervermerk" in s.text for s in raus) == 2


def test_einseitiges_dokument_bleibt_unveraendert():
    seiten = _seiten("Kopf\n\nInhalt\n\nSeite 1 von 1")
    assert bereinige_seiten(seiten) == seiten


def test_silbentrennung_am_zeilenende_wird_zusammengefuehrt():
    raus = bereinige_seiten(_seiten("Die Woh-\nnung ist hell.\nHaus-\nund Grundbesitz bleibt."))
    assert "Die Wohnung ist hell." in raus[0].text
    assert "Haus-\nund Grundbesitz" in raus[0].text


def test_metadaten_der_seiten_bleiben_erhalten():
    seiten = _doc(3)
    raus = bereinige_seiten(seiten)
    assert [(s.nummer, s.per_ocr, s.sicherheit, s.extraktor, s.extraktor_version) for s in raus] == \
           [(s.nummer, s.per_ocr, s.sicherheit, s.extraktor, s.extraktor_version) for s in seiten]


def test_schalter_wird_aus_modelle_yaml_gelesen(tmp_path):
    from dokumentenassistent import provider as p
    basis = "host: http://localhost:11434\nembedding: e\nllm: l\nocr: tesseract\n"
    (tmp_path / "a.yaml").write_text(basis)
    (tmp_path / "b.yaml").write_text(basis + "seitenbereinigung: true\n")
    (tmp_path / "c.yaml").write_text(basis + "seitenbereinigung: ja\n")
    assert (p.lade_ocr_einstellungen(tmp_path / "a.yaml").seitenbereinigung,
            p.lade_ocr_einstellungen(tmp_path / "b.yaml").seitenbereinigung) == (False, True)
    import pytest
    with pytest.raises(p.ProviderFehler, match="seitenbereinigung"):
        p.lade_ocr_einstellungen(tmp_path / "c.yaml")


def _pdf(pfad):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(pfad))
    for i, satz in enumerate(_INHALT[:3], 1):
        c.drawString(72, 800, "Hausverwaltung Sommer & Partner - Mietvertrag Wohnung Nord")
        c.drawString(72, 700, satz)
        c.drawString(72, 40, f"Seite {i} von 3")
        c.showPage()
    c.save()
    return pfad


def test_lies_seiten_bereinigt_nur_mit_schalter_und_markiert_die_version(tmp_path):
    from dokumentenassistent.auslesen import OcrEinstellungen, lies_seiten
    pdf = _pdf(tmp_path / "v.pdf")
    ohne = lies_seiten(pdf, OcrEinstellungen(pdf_extraktion="pypdf"))
    mit = lies_seiten(pdf, OcrEinstellungen(pdf_extraktion="pypdf", seitenbereinigung=True))
    assert all("Hausverwaltung" in s.text for s in ohne)
    assert not any("Hausverwaltung" in s.text or "von 3" in s.text for s in mit)
    assert all(s.extraktor_version.endswith("+seitenrand-v1") for s in mit)

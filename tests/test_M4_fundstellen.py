from pathlib import Path

from dokumentenassistent.typen import Datei, Seite
from dokumentenassistent.fundstellen import zerlege

D = Datei(hash="h1", pfad=Path("Rechnung (2).pdf"), name="Rechnung (2).pdf", groesse=1)


def _s(n, text, ocr=False):
    return Seite(nummer=n, text=text, per_ocr=ocr, sicherheit=None)


def test_M4_G1_absaetze_werden_an_leerzeilen_getrennt():
    # min_woerter=0 prüft das Trennen für sich; das Verschmelzen hat G11.
    f = zerlege(D, (_s(1, "Absatz eins.\n\nAbsatz zwei."),), min_woerter=0)
    assert [x.text for x in f] == ["Absatz eins.", "Absatz zwei."]


def test_M4_G11_kurze_absaetze_werden_bis_zur_mindestgroesse_verschmolzen():
    """Gemessen 24.09.2026 am echten Bestand: ohne Untergrenze waren 1103 von 2458
    Absätzen kürzer als 10 Wörter — Kopfzeilen, Seitenzahlen, Tabellenzellen. Die
    Zielabsätze der Fragen hatten dagegen 94 Wörter im Median. Verschmelzen bis 120
    Wörter hob MRR von 0,495 auf 0,596 und R@20 von 72 auf 80 % (54 Fragen).
    `max_woerter` war nie wirksam: es ist eine OBERgrenze, und fast nichts erreichte sie."""
    seite = _s(1, "\n\n".join(["Kurz eins.", "Kurz zwei.", "Kurz drei."]))
    f = zerlege(D, (seite,), min_woerter=4)
    assert [x.text for x in f] == ["Kurz eins.\nKurz zwei.", "Kurz drei."]


def test_M4_G12_ueber_seitengrenzen_wird_nicht_verschmolzen():
    """Ein Beleg muss auf genau eine Seite zeigen — sonst stimmt die Fundstelle nicht."""
    f = zerlege(D, (_s(1, "Kurz eins."), _s(2, "Kurz zwei.")), min_woerter=50)
    assert [(x.seite, x.text) for x in f] == [(1, "Kurz eins."), (2, "Kurz zwei.")]


def test_M4_G13_verschmelzen_ueberschreitet_die_obergrenze_nicht():
    lang = " ".join(["wort"] * 300)
    f = zerlege(D, (_s(1, f"{lang}\n\n{lang}"),), max_woerter=380, min_woerter=380)
    assert [len(x.text.split()) for x in f] == [300, 300]


def test_M4_G2_id_enthaelt_dokumentidentitaet_seite_absatz_textfingerprint():
    # min_woerter=0: sonst verschmelzen "A" und "B" zu einer Fundstelle (siehe G11).
    f = zerlege(D, (_s(1, "A\n\nB"), _s(2, "C")), min_woerter=0)
    assert [x.id for x in f] == [
        "Dh1#S1#A1#T559aead08264d5795d39",
        "Dh1#S1#A2#Tdf7e70e5021544f4834b",
        "Dh1#S2#A1#T6b23c0d5f35d1b11f9b6",
    ]


def test_M4_G3_fundstelle_traegt_datei_hash():
    assert zerlege(D, (_s(1, "A"),))[0].datei_hash == "h1"


def test_M4_G4_langer_absatz_wird_in_fenster_geteilt():
    lang = " ".join(f"w{i}" for i in range(1000))
    f = zerlege(D, (_s(1, lang),), max_woerter=380, ueberlapp=30)
    assert len(f) == 3


def test_M4_G5_fenster_ueberlappen():
    lang = " ".join(f"w{i}" for i in range(1000))
    f = zerlege(D, (_s(1, lang),), max_woerter=380, ueberlapp=30)
    assert f[0].text.split()[-30:] == f[1].text.split()[:30]


def test_M4_G6_ids_bleiben_bei_erneutem_lauf_gleich():
    seiten = (_s(1, "A\n\nB"),)
    assert [x.id for x in zerlege(D, seiten)] == [x.id for x in zerlege(D, seiten)]


def test_M4_B1_leere_seite_erzeugt_keine_fundstelle():
    assert zerlege(D, (_s(1, "   \n\n  "),)) == ()


def test_M4_B2_seite_ohne_leerzeilen_ist_ein_absatz():
    assert len(zerlege(D, (_s(1, "Zeile 1\nZeile 2\nZeile 3"),))) == 1


def test_M4_B3_keine_seiten_ergibt_leeres_tupel():
    assert zerlege(D, ()) == ()


def test_M4_B4_whitespace_wird_normalisiert():
    assert zerlege(D, (_s(1, "  A   B \n C "),))[0].text == "A B\nC"


def test_seitenuebergreifend_verbindet_fortsetzung_mit_exakten_spannen():
    fundstellen = zerlege(D, (_s(1, "Erster Teil"), _s(2, "zweiter Teil.")),
                         seitenuebergreifend=True)
    assert len(fundstellen) == 1
    f = fundstellen[0]
    assert f.text == "Erster Teil\nzweiter Teil."
    assert f.seiten == (1, 2)
    assert f.text[f.spannen[0].start:f.spannen[0].ende] == "Erster Teil"
    assert f.text[f.spannen[1].start:f.spannen[1].ende] == "zweiter Teil."


def test_seitenuebergreifend_bindet_kurze_unterschrift_am_dokumentende_zurueck():
    haupttext = " ".join(["Begleitschreiben"] * 120)
    fundstellen = zerlege(
        D, (_s(1, haupttext + "\n\n"), _s(2, "Name der Vertretung")),
        seitenuebergreifend=True,
    )
    assert len(fundstellen) == 1
    assert fundstellen[0].text == haupttext + "\nName der Vertretung"
    assert fundstellen[0].seiten == (1, 2)
    assert fundstellen[0].text[fundstellen[0].spannen[-1].start:
                               fundstellen[0].spannen[-1].ende] == "Name der Vertretung"


def test_seitenuebergreifend_erhaelt_siebenwortigen_schlussabsatz_als_suchsignal():
    haupttext = " ".join(["Begleitschreiben"] * 120)
    schluss = "Gesonderter Hinweis mit eigenem wichtigen Suchsignal heute"
    fundstellen = zerlege(
        D, (_s(1, haupttext + "\n\n"), _s(2, schluss)),
        seitenuebergreifend=True,
    )
    assert [f.text for f in fundstellen] == [haupttext, schluss]


def test_seitenuebergreifend_respektiert_absatzbruch_ohne_minimum():
    fundstellen = zerlege(D, (_s(1, "Eins.\n\nZwei"), _s(2, "fortgesetzt.")),
                         min_woerter=0, seitenuebergreifend=True)
    assert [f.text for f in fundstellen] == ["Eins.", "Zwei\nfortgesetzt."]


def test_seitenuebergreifend_ueberspringt_leere_seite_ohne_falsche_provenienz():
    f, = zerlege(D, (_s(1, "Vorher"), _s(2, "  \n "), _s(3, "Nachher")),
                 seitenuebergreifend=True)
    assert f.seiten == (1, 3)
    assert 2 not in f.seiten


def test_seitenuebergreifend_fenster_ueberlappen_mit_eigenen_offsets():
    seiten = (_s(1, " ".join(f"w{i}" for i in range(8))),
              _s(2, " ".join(f"w{i}" for i in range(8, 18))))
    fundstellen = zerlege(D, seiten, max_woerter=10, ueberlapp=3,
                         min_woerter=0, seitenuebergreifend=True)
    assert len(fundstellen) == 3
    assert fundstellen[0].text.split()[-3:] == fundstellen[1].text.split()[:3]
    for f in fundstellen:
        assert f.spannen
        assert f.spannen[0].start >= 0
        assert all(0 <= s.start < s.ende <= len(f.text) for s in f.spannen)
        assert f.seiten == tuple(dict.fromkeys(s.seite for s in f.spannen))
    assert fundstellen[0].seiten == (1, 2)
    assert fundstellen[1].seiten == (1, 2)
    assert fundstellen[2].seiten == (2,)


def test_seitenuebergreifend_erfindet_keine_enttrennung():
    f, = zerlege(D, (_s(1, "Rech-"), _s(2, "nung")), seitenuebergreifend=True)
    assert f.text == "Rech-\nnung"


def test_seitenuebergreifend_ueberschreitet_keine_dateigrenzen():
    other = Datei(hash="h2", pfad=Path("andere.pdf"), name="andere.pdf", groesse=1)
    first, = zerlege(D, (_s(1, "Ende"),), seitenuebergreifend=True)
    second, = zerlege(other, (_s(1, "Anfang"),), seitenuebergreifend=True)
    assert first.text == "Ende" and second.text == "Anfang"
    assert first.datei_hash != second.datei_hash


def test_einzelseiten_ids_und_text_bleiben_im_opt_in_stabil():
    seiten = (_s(1, "  A   B \n C\n\nD "),)
    alt = zerlege(D, seiten, min_woerter=0)
    neu = zerlege(D, seiten, min_woerter=0, seitenuebergreifend=True)
    assert [(f.id, f.text) for f in neu] == [(f.id, f.text) for f in alt]


def test_eingefuegter_trenner_gehoert_keiner_seitenspanne():
    f, = zerlege(D, (_s(1, "A\n\nB"),), seitenuebergreifend=True)
    assert f.text == "A\nB"
    assert [(s.seite, s.start, s.ende) for s in f.spannen] == [(1, 0, 1), (1, 2, 3)]


def test_absatzbruch_unmittelbar_vor_oder_nach_seitenwechsel_bleibt_erhalten():
    for seiten in ((_s(1, "Ende.\n\n"), _s(2, "Neuer Absatz.")),
                   (_s(1, "Ende."), _s(2, "\n\nNeuer Absatz."))):
        fundstellen = zerlege(D, seiten, min_woerter=0, seitenuebergreifend=True)
        assert [f.text for f in fundstellen] == ["Ende.", "Neuer Absatz."]


def test_einzelner_zeilenumbruch_am_seitenrand_ist_keine_absatzgrenze():
    for seiten in ((_s(1, "Ende.\n"), _s(2, "Fortsetzung.")),
                   (_s(1, "Ende."), _s(2, "\nFortsetzung."))):
        fundstellen = zerlege(D, seiten, min_woerter=0, seitenuebergreifend=True)
        assert len(fundstellen) == 1

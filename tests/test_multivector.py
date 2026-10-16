"""Multi-Vector-Retrieval: MaxSim und Ranking. Ohne Modell, ohne Netz.

Der Kodierer ist ein Parameter, deshalb reicht hier ein gefälschter: ein Vektor je
Wort, einer je Buchstabe im Alphabet. Das prüft die Mathematik und die Sortierung —
ob ein ECHTES ColBERT-Modell auf deutschen Geschäftstexten trägt, prüft keine
Zusicherung hier, sondern die Messung auf dem echten Bestand.
"""
from __future__ import annotations

import pytest

torch = pytest.importorskip("torch", reason="braucht das Reranker-Extra")

from dokumentenassistent.multivector import MultiVectorFehler, maxsim, rang  # noqa: E402
from tests.conftest import fs  # noqa: E402

A = fs("D.pdf#S1#A1", "rechnung notar grundschuld", datei="D.pdf")
B = fs("D.pdf#S1#A2", "mietvertrag kaltmiete wohnung", datei="D.pdf", absatz=2)
C = fs("D.pdf#S1#A3", "anleitung router netzteil", datei="D.pdf", absatz=3)
FSET = (A, B, C)


def _kodierer(texte):
    """Ein Einheitsvektor je Wort: Buchstabe -> Achse. Gleiche Wörter -> Skalarprodukt 1."""
    raus = []
    for text in texte:
        zeilen = []
        for wort in text.split():
            v = torch.zeros(26)
            for zeichen in wort:
                if "a" <= zeichen <= "z":
                    v[ord(zeichen) - 97] += 1.0
            zeilen.append(v / (v.norm() or 1.0))
        raus.append(torch.stack(zeilen) if zeilen else torch.zeros(0, 26))
    return raus


def test_MV_G1_maxsim_summiert_ueber_fragetoken():
    """Zwei identische Tokenpaare ergeben 2.0 — die Summe, nicht den Mittelwert."""
    q = _kodierer(["notar grundschuld"])[0]
    d = _kodierer(["rechnung notar grundschuld"])[0]
    assert maxsim(q, d) == pytest.approx(2.0, abs=1e-5)


def test_MV_G2_ein_fehlendes_wort_kostet_nicht_den_ganzen_treffer():
    """Der Vorteil gegenüber einem Vektor je Absatz: Teiltreffer bleiben sichtbar."""
    q = _kodierer(["notar zahnarzt"])[0]
    d = _kodierer(["rechnung notar grundschuld"])[0]
    assert 1.0 < maxsim(q, d) < 2.0


def test_MV_G3_rang_sortiert_absteigend_und_trifft_den_richtigen_absatz():
    ergebnis = rang("notar grundschuld", FSET, _kodierer)
    assert ergebnis[0][0] == A.id
    assert [i for i, _ in ergebnis] == [A.id, B.id, C.id] or ergebnis[0][0] == A.id
    assert all(ergebnis[i][1] >= ergebnis[i + 1][1] for i in range(len(ergebnis) - 1))


def test_MV_G4_vorberechnete_absatzvektoren_werden_benutzt():
    """Die Kodierung ist der teure Teil; über 85 Fragen darf sie nur einmal laufen."""
    vektoren = _kodierer([f.text for f in FSET])
    aufrufe = []

    def zaehlend(texte):
        aufrufe.append(list(texte))
        return _kodierer(texte)

    rang("kaltmiete wohnung", FSET, zaehlend, absatz_vektoren=vektoren)
    assert aufrufe == [["kaltmiete wohnung"]]  # nur die Frage, nicht der Bestand


def test_MV_B1_leere_frage_und_leerer_bestand_werfen():
    with pytest.raises(MultiVectorFehler):
        rang("   ", FSET, _kodierer)
    with pytest.raises(MultiVectorFehler):
        rang("notar", (), _kodierer)


def test_MV_B2_falsche_zahl_vorberechneter_vektoren_wirft_statt_still_zu_verrutschen():
    """Ein Vektor zu wenig würde sonst alle Absätze um eins verschieben — und die
    Messung sähe plausibel aus, wäre aber durchgehend falsch."""
    with pytest.raises(MultiVectorFehler):
        rang("notar", FSET, _kodierer, absatz_vektoren=_kodierer([A.text, B.text]))

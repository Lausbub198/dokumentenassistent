from dokumentenassistent.agentisches_retrieval import iterativ_suchen
from dokumentenassistent.typen import Antwort, Belegkarte
from tests.conftest import fs


def nicht_gefunden():
    return Antwort(status="nicht_gefunden", text="nicht gefunden", karten=())


def gefunden():
    quelle = fs("synthetisch.pdf#S1#A1", "synthetischer Beleg", datei="synthetisch.pdf")
    return Antwort(status="gefunden", text="Antwort", karten=(Belegkarte(quelle, quelle.text),))


def test_iterativ_suchen_stoppt_nach_belegter_erstantwort():
    aufrufe = []

    def suchen(frage, suchtext, timeout_s):
        aufrufe.append((frage, suchtext))
        return gefunden()

    antwort = iterativ_suchen("synthetische Frage", suchen, lambda *_: "andere Formulierung")

    assert antwort.status == "gefunden"
    assert len(antwort.karten) == 1
    assert aufrufe == [("synthetische Frage", None)]


def test_iterativ_suchen_begrenzt_nachfragen_auf_zwei():
    suchaufrufe = []
    anfragen = iter(("Alternative eins", "Alternative zwei", "dritte Alternative"))

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        return nicht_gefunden()

    antwort = iterativ_suchen(
        "synthetische Frage", suchen, lambda *_: next(anfragen), max_nachfragen=2
    )

    assert antwort.status == "nicht_gefunden"
    assert suchaufrufe == [None, "Alternative eins", "Alternative zwei"]


def test_iterativ_suchen_akzeptiert_keine_unbelegte_antwort_mit_falscher_id():
    suchaufrufe = []

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        if suchtext is None:
            return nicht_gefunden()
        return Antwort(status="gefunden", text="[erfunden.pdf#S1#A1]", karten=())

    antwort = iterativ_suchen(
        "synthetische Frage", suchen, lambda *_: "Alternative eins", max_nachfragen=1
    )

    assert antwort.status != "gefunden" or antwort.karten
    assert not antwort.karten
    assert suchaufrufe == [None, "Alternative eins"]


def test_kontrollfrage_bleibt_ohne_beleg_nach_hoechstens_zwei_nachfragen_abgewiesen():
    suchaufrufe = []
    anfragen = iter(("Kontrollvariante eins", "Kontrollvariante zwei", "dritte Variante"))

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        return nicht_gefunden()

    antwort = iterativ_suchen(
        "synthetische Kontrollfrage", suchen, lambda *_: next(anfragen)
    )

    assert (antwort.status, antwort.karten) == ("nicht_gefunden", ())
    assert len(suchaufrufe) == 3


def test_iterativ_suchen_bricht_bei_identischer_umformulierung_ab():
    suchaufrufe = []

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        return nicht_gefunden()

    antwort = iterativ_suchen(
        "synthetische Frage", suchen, lambda *_: " synthetische   Frage "
    )

    assert antwort.status == "nicht_gefunden"
    assert suchaufrufe == [None]


def test_iterativ_suchen_bricht_beim_timeout_der_umformulierung_ab():
    suchaufrufe = []

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        return nicht_gefunden()

    def timeout(*_):
        raise TimeoutError

    antwort = iterativ_suchen("synthetische Frage", suchen, timeout)

    assert antwort.status == "nicht_gefunden"
    assert suchaufrufe == [None]


def test_iterativ_suchen_startet_keine_nachfrage_nach_zeitbudget():
    now = [0.0]
    suchaufrufe = []

    def suchen(frage, suchtext, timeout_s):
        suchaufrufe.append(suchtext)
        return nicht_gefunden()

    def umformulieren(frage, bisherige, timeout_s):
        now[0] += 5.0
        return "Alternative"

    antwort = iterativ_suchen(
        "synthetische Frage", suchen, umformulieren, zeitbudget_s=5,
        monotonic=lambda: now[0],
    )

    assert antwort.status == "nicht_gefunden"
    assert suchaufrufe == [None]

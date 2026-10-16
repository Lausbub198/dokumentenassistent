from dokumentenassistent import schwelle_kalibrierung as sk


def _z(nr, stufe, mehrfach=False, status='gefunden', abgewiesen=False):
    return {'nr': nr, 'stufe': stufe, 'mehrfach': mehrfach, 'streng': mehrfach, 'wert_in_antwort': mehrfach,
            'status': status, 'abgewiesen': abgewiesen}


MS = {1: 0.70, 2: 0.60, 3: 0.55, 4: 0.50}


def test_schwelle_wirkt_nur_auf_stufe_2():
    zs = [_z(1, 1, True), _z(2, 2, True), _z(4, 2, status='nicht_gefunden')]
    neu = sk.mit_schwelle(zs, MS, 0.58)
    assert neu[0]['mehrfach'] and neu[1]['mehrfach'] and neu[2]['abgewiesen']
    assert not sk.mit_schwelle(zs, MS, 0.65)[1]['mehrfach']
    assert zs[2]['abgewiesen'] is False  # Original unverändert


def test_kalibrierung_kleinster_wert_korrekter_stufe2_fragen_der_haelfte():
    laeufe = [[_z(1, 2, True), _z(2, 2, True), _z(3, 2, False)], [_z(3, 2, True)]]
    assert sk.kalibriere(laeufe, MS, {1, 2}) == 0.60
    assert sk.kalibriere(laeufe, MS, {1, 2, 3}) == 0.55
    assert sk.kalibriere(laeufe, MS, {4}) == 0.0


def test_wirkung_verloren_und_negative():
    laeufe = [[_z(2, 2, True), _z(4, 2, status='nicht_gefunden')]]
    w = sk.wirkung(laeufe, MS, 0.65, {2, 4})
    assert w == {'positiv_verloren': [2], 'negativ_falsch_vorher': [4], 'negativ_falsch_nachher': []}

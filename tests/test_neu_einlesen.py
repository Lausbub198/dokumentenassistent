import json
import sys

import pytest

from dokumentenassistent import neu_einlesen as ne
from dokumentenassistent.typen import Antwort, Belegkarte, Fundstelle


def test_arbeitsordner_darf_nicht_die_quelle_sein(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['x', 'einlesen', '--quelle', str(tmp_path), '--arbeitsordner', str(tmp_path),
                                      '--modelle', str(tmp_path / 'm.yaml')])
    with pytest.raises(SystemExit):
        ne.main()


class _Index:
    def __init__(self, fs):
        self.fs = fs

    def dateien(self):
        from pathlib import Path
        from dokumentenassistent.typen import Datei
        return (Datei('h', Path('/q/Vertrag.pdf'), 'Vertrag.pdf', 1),)

    def fundstellen(self, h):
        return self.fs


class _Werkstatt:
    def __init__(self, fs, antworten):
        self.index, self.antworten = _Index(fs), antworten

    def frage(self, text):
        return self.antworten[text]


def test_pruefen_bewertet_und_ist_wiederaufnehmbar(tmp_path):
    gold = Fundstelle('g', 'h', 'Vertrag.pdf', 1, 0, 'Die Miete beträgt 750,00 EUR.')
    fragen = [{'nr': 1, 'frage': 'Miete?', 'status': 'gefunden', 'datei': 'Vertrag.pdf',
               'wortlaut_enthaelt': '750,00 EUR', 'zielabsatz': 'Die Miete beträgt 750,00 EUR.'},
              {'nr': 2, 'frage': 'Garage?', 'status': 'nicht_gefunden'}]
    w = _Werkstatt([gold], {'Miete?': Antwort('gefunden', '750,00 EUR [g]', (Belegkarte(gold, gold.text),)),
                            'Garage?': Antwort('nicht_gefunden', 'nicht gefunden', ())})
    aus = tmp_path / 'p.jsonl'
    b = ne.pruefen(w, fragen, tmp_path / 'keine-sichtung.md', aus)
    assert (b['mehrfach'], b['streng'], b['negativ_abgewiesen'], b['positiv_abgewiesen']) == (1, 1, 1, 0)
    # Zitierte IDs werden mitgeschrieben, damit sich ein Lauf später ohne Modellaufruf neu bewerten lässt.
    assert [json.loads(z)['karten'] for z in aus.read_text().splitlines()] == [['g'], []]
    w.antworten = {}  # zweiter Aufruf darf nichts neu fragen
    assert ne.pruefen(w, fragen, tmp_path / 'keine-sichtung.md', aus)['fragen'] == 2
    assert len(aus.read_text().splitlines()) == 2


def test_ladevorgaenge_zaehlt_nur_seit_beginn(tmp_path):
    from datetime import datetime
    log = tmp_path / 'server.log'
    log.write_text('time=2026-10-03T11:20:00.100+02:00 level=INFO msg="loading model via llama-server" model=a\n'
                   'time=2026-10-03T11:23:21.230+02:00 level=INFO msg="loading model via llama-server" model=b\n'
                   'time=2026-10-03T11:24:00.000+02:00 level=INFO msg="etwas anderes"\n'
                   'time=2026-10-03T11:25:55.231+02:00 level=INFO msg="loading model via llama-server" model=a\n')
    assert ne.ladevorgaenge(datetime(2026, 10, 3, 11, 22), log) == 2
    assert ne.ladevorgaenge(datetime(2026, 10, 3, 11, 22), tmp_path / 'fehlt.log') is None


def test_einordnen_zaehlt_status_je_datei():
    from types import SimpleNamespace as NS

    class W:
        def __init__(self): self.aufgerufen = False
        def einordnen(self, fortschritt=None): self.aufgerufen = True
        _st = {'a': 'sicher', 'b': 'sicher', 'c': 'unklar', 'd': 'ocr_unsicher'}
        # wie das echte Index: Datei ohne Status-Feld, Status über index.status(hash)
        index = NS(dateien=lambda: [NS(hash=h) for h in 'abcd'], status=lambda h, _st=_st: _st[h])
    w = W()
    b = ne.einordnen(w)
    assert w.aufgerufen and (b['dateien'], b['status']) == (4, {'sicher': 2, 'unklar': 1, 'ocr_unsicher': 1})

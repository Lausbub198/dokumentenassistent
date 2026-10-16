"""Produktprüfungen (`neu_einlesen pruefen`) nachträglich und gleich bewerten, ohne Modellaufruf (06.10.2026).

Anlass: Die Seitenrand-Bereinigung ändert die Chunk-Texte. Das Mehrfach-Gold findet den Gold-Absatz aber
per exakter Enthaltenseins-Prüfung, und manche Goldtexte tragen noch Reste der alten Auslesung
(Kopfzeilen-Wörter, getrennte Wörter). Ein bereinigter Index würde dadurch schlechter bewertet, obwohl
er besser ist. Hier gilt für BEIDE Läufe dieselbe tolerante Regel:

    Gold-Chunk  = Chunk der Zieldatei, der mindestens `MINDESTANTEIL` der Gold-Wörter in Reihenfolge
                  enthält (Vergleich nach Kleinschreibung, ohne Satzzeichen, Trennung zusammengeführt)
    korrekt     = ein zitierter Chunk ist Gold-Chunk, ODER er stammt aus der Zieldatei und enthält den
                  Sollwert (nicht bei kurzen Sollwerten) — wie `gold_mehrfach`, ohne Nutzersichtung

Ausgabe nur Kennzahlen und Fragenummern.
"""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
import re

from dokumentenassistent.gold_mehrfach import kurz
from dokumentenassistent.antwort_eval import normalisiere_whitespace as ws
from dokumentenassistent.index import Index
from dokumentenassistent.seitenvergleich import _ziel_dateien
from dokumentenassistent.pfade_privat import FRAGEN

MINDESTANTEIL = 0.9


def woerter(text: str) -> list[str]:
    text = re.sub(r'([a-zäöüß])-\s+([a-zäöüß])', r'\1\2', text.casefold())
    return re.sub(r'[^\w]+', ' ', text).split()


def deckung(gold: list[str], chunk: list[str]) -> float:
    """Anteil der Gold-Wörter, die in Reihenfolge im Chunk vorkommen."""
    if not gold:
        return 0.0
    sm = difflib.SequenceMatcher(None, gold, chunk, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(gold)


def gold_ids(frage: dict, index: Index) -> set[str]:
    gold = woerter(frage.get('zielabsatz') or '')
    return {f.id for d in _ziel_dateien(frage, index) for f in index.fundstellen(d.hash)
            if deckung(gold, woerter(f.text)) >= MINDESTANTEIL}


def bewerte(zeilen: list[dict], fragen: dict[int, dict], index: Index) -> dict:
    nach_id = {f.id: f for d in index.dateien() for f in index.fundstellen(d.hash)}
    korrekt, gold_leer = set(), []
    for z in zeilen:
        f = fragen[z['nr']]
        if f['status'] != 'gefunden':
            continue
        gold = gold_ids(f, index)
        if not gold:
            gold_leer.append(z['nr'])
        dateien = {d.hash for d in _ziel_dateien(f, index)}
        wert = f.get('wortlaut_enthaelt') or ''
        for kid in z.get('karten', []):
            k = nach_id.get(kid)
            if k and (kid in gold or (k.datei_hash in dateien and not kurz(wert) and ws(wert) in ws(k.text))):
                korrekt.add(z['nr'])
                break
    neg = [z for z in zeilen if fragen[z['nr']]['status'] != 'gefunden']
    return {'fragen': len(zeilen), 'korrekt': len(korrekt), 'korrekt_nr': sorted(korrekt),
            'negativ_abgewiesen': sum(not z.get('karten') for z in neg), 'negativ': len(neg),
            'gold_nicht_gefunden_nr': gold_leer}


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--lauf', nargs=2, metavar=('ARBEITSORDNER', 'PRUEFUNG_JSONL'), action='append', required=True)
    a.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    args = a.parse_args()
    fragen = {f['nr']: f for f in json.loads(args.gold.read_text(encoding='utf-8'))['fragen']}
    ergebnisse = {}
    for ordner, datei in args.lauf:
        zeilen = [json.loads(z) for z in (Path(ordner) / datei).read_text().splitlines()]
        ergebnisse[datei] = bewerte(zeilen, fragen, Index(Path(ordner)))
    if len(ergebnisse) == 2:
        (na, a_), (nb, b_) = ergebnisse.items()
        ergebnisse['paarweise'] = {f'nur_{na}': sorted(set(a_['korrekt_nr']) - set(b_['korrekt_nr'])),
                                   f'nur_{nb}': sorted(set(b_['korrekt_nr']) - set(a_['korrekt_nr']))}
    print(json.dumps(ergebnisse, indent=1))


if __name__ == '__main__':
    main()

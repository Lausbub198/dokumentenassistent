"""C6 (Testprogramm 2026-09-30): Schwelle für den Kaskaden-Nachgriff kalibrieren. Nur IDs/Kennzahlen.

Ohne Modellaufruf: Der beste 8B-Ähnlichkeitswert je Frage stammt aus C1 (Arm e8B), die Antworten beider
Kaskaden-Stufen aus den gespeicherten Läufen. Regeln (vorab festgelegt, 02.10.2026):

- Die Schwelle steuert nur Stufe 2 (Nachgriff auf Top 20). Liegt der beste Ähnlichkeitswert darunter,
  entfällt der Nachgriff und die Antwort ist „nicht gefunden“. Stufe 1 bleibt unverändert.
- Feste Aufteilung: ungerade gegen gerade Fragenummer. Kalibrieren auf einer Hälfte, prüfen auf der anderen,
  dann tauschen.
- Kalibrierregel: höchste Schwelle, die auf der Kalibrierhälfte keine positive Frage verliert, die in einer
  der Reihenfolgen über Stufe 2 korrekt beantwortet wurde (= kleinster Ähnlichkeitswert dieser Fragen).
- Endgültige Schwelle: die niedrigere der beiden Hälften (behält im Zweifel Antworten).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dokumentenassistent import antwortstufe as ab
from dokumentenassistent import gold_mehrfach as gm
from dokumentenassistent import seitenvergleich as sv
from dokumentenassistent.index import Index
from dokumentenassistent.pfade_privat import FRAGEN, LAEUFE


def mit_schwelle(zeilen: list[dict], max_score: dict[int, float], t: float) -> list[dict]:
    """Kaskade nachrechnen: Stufe-2-Antworten unter der Schwelle werden zu „nicht gefunden“."""
    raus = []
    for z in zeilen:
        if z.get('stufe') == 2 and max_score[z['nr']] < t:
            z = {**z, 'abgewiesen': True, 'mehrfach': False, 'streng': False, 'wert_in_antwort': False}
        raus.append(z)
    return raus


def kalibriere(laeufe: list[list[dict]], max_score: dict[int, float], nummern: set[int]) -> float:
    """Kleinster Ähnlichkeitswert unter den positiven Fragen, die in einem Lauf über Stufe 2 korrekt sind."""
    werte = [max_score[z['nr']] for zs in laeufe for z in zs
             if z['nr'] in nummern and z['status'] == 'gefunden' and z.get('stufe') == 2 and z['mehrfach']]
    return min(werte) if werte else 0.0


def wirkung(laeufe: list[list[dict]], max_score: dict[int, float], t: float, nummern: set[int]) -> dict:
    vorher = [[z for z in zs if z['nr'] in nummern] for zs in laeufe]
    nachher = [mit_schwelle(zs, max_score, t) for zs in vorher]
    def korrekt(zs):
        return {z['nr'] for z in zs if z['status'] == 'gefunden' and z['mehrfach']}
    def neg_falsch(zs):
        return {z['nr'] for z in zs if z['status'] != 'gefunden' and not z['abgewiesen']}
    return {'positiv_verloren': sorted(set().union(*(korrekt(a) - korrekt(b) for a, b in zip(vorher, nachher)))),
            'negativ_falsch_vorher': sorted(set().union(*(neg_falsch(a) for a in vorher))),
            'negativ_falsch_nachher': sorted(set().union(*(neg_falsch(b) for b in nachher)))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--c1', type=Path, default=LAEUFE / 'c1-embedding-2026-09-30/ergebnisse.json')
    p.add_argument('--phase-b', type=Path, default=LAEUFE / 'phase-b')
    p.add_argument('--retrieval', type=Path, default=LAEUFE / 'retrieval-2026-09-29')
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--sichtung', type=Path, default=LAEUFE / 'gold-mehrfach/sichtung.md')
    p.add_argument('--arm', default='e8B')
    p.add_argument('--lauf', default='e8B-b6-kaskade')
    a = p.parse_args()
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    max_score = {int(n): v['max_score'] for n, v in json.loads(a.c1.read_text())[a.arm].items()}
    index = Index(a.retrieval / 'seitenuebergreifend')
    fundstellen, _ = sv._matrix(index, json.loads((a.retrieval / 'manifest.json').read_text())['embedding_revision'])
    nach_id, nach_nr = {f.id: f for f in fundstellen}, {f['nr']: f for f in fragen}
    mf = gm.Mehrfach(fragen, index, gm.lies_entscheidungen(a.sichtung))
    laeufe = [ab.neu_bewerten(a.phase_b / n / 'ergebnisse.jsonl', nach_nr, nach_id, mf)
              for n in (a.lauf, a.lauf + '-umgekehrt')]
    alle = {f['nr'] for f in fragen}
    ungerade, gerade = {n for n in alle if n % 2}, {n for n in alle if not n % 2}
    bericht = {'max_score_negativ_falsch': {n: round(max_score[n], 4) for n in wirkung(laeufe, max_score, 0, alle)['negativ_falsch_vorher']}}
    for name, kal, test in (('kal_ungerade_test_gerade', ungerade, gerade), ('kal_gerade_test_ungerade', gerade, ungerade)):
        t = kalibriere(laeufe, max_score, kal)
        bericht[name] = {'schwelle': round(t, 4), 'test': wirkung(laeufe, max_score, t, test)}
    t_end = min(bericht['kal_ungerade_test_gerade']['schwelle'], bericht['kal_gerade_test_ungerade']['schwelle'])
    gesamt = [mit_schwelle(zs, max_score, t_end) for zs in laeufe]
    bericht['endgueltig'] = {'schwelle': t_end, 'wirkung_alle': wirkung(laeufe, max_score, t_end, alle),
                             'robustheit': {k: (len(v) if isinstance(v, list) else v)
                                            for k, v in ab.gleich_je_frage(*gesamt).items()}}
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

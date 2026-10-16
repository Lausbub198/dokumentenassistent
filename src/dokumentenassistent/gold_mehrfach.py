"""A1/A2 (Testprogramm 2026-09-30): Mehrfach-Gold. CLI gibt nur IDs und Kennzahlen aus.

Ein Gold-Absatz pro Frage unterschätzt Retrieval und Zitate, weil dieselbe Tatsache oft mehrfach im
Bestand steht. Regel (vorab festgelegt):

    akzeptiert  = Gold-Zielabsatz
                  ODER Chunk einer namenspassenden Zieldatei, der den Sollwert enthält
                       (nicht bei kurzen Sollwerten, siehe `kurz`)
                  ODER vom Nutzer in der Sichtung als „trägt die Antwort“ markiert
    abgelehnt   = vom Nutzer als „trägt nicht“ markiert (schlägt die automatische Regel)

Schritte:
    sichtung   schreibt eine private Markdown-Liste: jeder in den Antwortläufen zitierte Chunk, der
               nicht der Gold-Absatz ist, plus Wert-Treffer bei kurzen Sollwerten. Der Nutzer kreuzt an.
    bewerten   bewertet Antwortlauf (praefix_e2e) und Präfix-Retrieval neu: streng gegen Mehrfach-Gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from dokumentenassistent.antwort_eval import normalisiere_whitespace as ws
from dokumentenassistent.index import Index
from dokumentenassistent.seitenvergleich import _ausserhalb_git, _ziel_dateien, _ziel_ids
from dokumentenassistent.suche import _karten
from dokumentenassistent.pfade_privat import FRAGEN, LAEUFE

_ENTSCHEIDUNG = re.compile(r'^<!-- (?P<nr>\d+):(?P<h>[0-9a-f]{16}) -->\s*$')
_KREUZ = re.compile(r'^- \[(?P<ja>[ xX])\] trägt die Antwort\s+- \[(?P<nein>[ xX])\] trägt nicht', re.M)


def kurz(wert: str) -> bool:
    w = ws(wert)
    return len(w) < 6 or (len(w) < 8 and re.fullmatch(r'[\d\s.,:/-]+', w) is not None)


def texthash(text: str) -> str:
    return hashlib.sha256(ws(text).encode()).hexdigest()[:16]


class Mehrfach:
    def __init__(self, fragen: list[dict], index: Index, entscheidungen: dict[tuple[int, str], bool]):
        self.index, self.ent = index, entscheidungen
        self.frage = {f['nr']: f for f in fragen}
        self.gold = {f['nr']: _ziel_ids(f, index) for f in fragen if f['status'] == 'gefunden'}
        self.dateien = {f['nr']: {d.hash for d in _ziel_dateien(f, index)} for f in fragen if f['status'] == 'gefunden'}

    def akzeptiert(self, nr: int, fundstelle) -> bool:
        entscheidung = self.ent.get((nr, texthash(fundstelle.text)))
        if entscheidung is not None:
            return entscheidung
        if fundstelle.id in self.gold.get(nr, set()):
            return True
        wert = self.frage[nr].get('wortlaut_enthaelt') or ''
        return (fundstelle.datei_hash in self.dateien.get(nr, set()) and not kurz(wert)
                and bool(ws(wert)) and ws(wert) in ws(fundstelle.text))


def lies_entscheidungen(pfad: Path) -> dict[tuple[int, str], bool]:
    if not pfad.exists():
        return {}
    raus, schluessel = {}, None
    for zeile in pfad.read_text(encoding='utf-8').splitlines():
        m = _ENTSCHEIDUNG.match(zeile)
        if m:
            schluessel = (int(m['nr']), m['h'])
            continue
        k = _KREUZ.match(zeile)
        if k and schluessel:
            ja, nein = k['ja'] != ' ', k['nein'] != ' '
            if ja != nein:  # genau ein Kreuz, sonst unentschieden
                raus[schluessel] = ja
            schluessel = None
    return raus


def _alle_fundstellen(index: Index) -> dict:
    return {fs.id: fs for d in index.dateien() for fs in index.fundstellen(d.hash)}


def sichtung(fragen, index, e2e_zeilen, ziel: Path) -> int:
    fs_nach_id = _alle_fundstellen(index)
    frage = {f['nr']: f for f in fragen}
    gold = {f['nr']: _ziel_ids(f, index) for f in fragen if f['status'] == 'gefunden'}
    posten: dict[tuple[int, str], object] = {}
    for z in e2e_zeilen:
        if z['nr'] not in gold or not z.get('antwort'):
            continue
        top = tuple(fs_nach_id[i] for i in z['kontext_ids'])
        for k in _karten(z['antwort'], top):
            if k.fundstelle.id not in gold[z['nr']]:
                posten[(z['nr'], texthash(k.fundstelle.text))] = k.fundstelle
    for nr, f in frage.items():
        if nr in gold and kurz(f.get('wortlaut_enthaelt') or ''):
            for d in _ziel_dateien(f, index):
                for fs in index.fundstellen(d.hash):
                    if fs.id not in gold[nr] and ws(f['wortlaut_enthaelt']) in ws(fs.text):
                        posten[(nr, texthash(fs.text))] = fs
    teile = ['# Sichtung Mehrfach-Gold (privat)\n',
             'Je Eintrag genau ein Kästchen ankreuzen: `[x]`. „Trägt die Antwort“ heißt: Wer nur diesen '
             'Absatz liest, kann die Frage richtig beantworten. Datei speichern, fertig.\n']
    for (nr, h), fs in sorted(posten.items()):
        f = frage[nr]
        gold_text = ' / '.join(fs_nach_id[i].text for i in sorted(gold[nr]))[:1500]
        teile += [f'\n---\n\n## Frage {nr}\n', f'**Frage:** {f["frage"]}\n', f'**Sollwert:** {f.get("wortlaut_enthaelt")}\n',
                  f'**Gold-Absatz:**\n\n> {ws(gold_text)}\n', f'**Zu prüfen** (Datei: {fs.datei_name}):\n\n> {ws(fs.text)}\n',
                  f'<!-- {nr}:{h} -->', '- [ ] trägt die Antwort   - [ ] trägt nicht\n']
    ziel.write_text('\n'.join(teile), encoding='utf-8')
    return len(posten)


def bewerte_e2e(zeilen, mf: Mehrfach, fs_nach_id: dict) -> dict:
    raus = {}
    for arm in sorted({z['arm'] for z in zeilen}):
        eigene = [z for z in zeilen if z['arm'] == arm and z['nr'] in mf.gold]
        streng = mehrfach = 0
        treffer = set()
        for z in eigene:
            if not z.get('antwort'):
                continue
            top = tuple(fs_nach_id[i] for i in z['kontext_ids'])
            karten = _karten(z['antwort'], top)
            streng += any(k.fundstelle.id in mf.gold[z['nr']] for k in karten)
            if any(mf.akzeptiert(z['nr'], k.fundstelle) for k in karten):
                mehrfach += 1
                treffer.add(z['nr'])
        raus[arm] = {'streng': streng, 'mehrfach': mehrfach, '_treffer': treffer}
    arme = sorted(raus)
    if len(arme) == 2:
        a, b = arme
        raus['gepaart_mehrfach'] = {'gewinne': sorted(raus[b]['_treffer'] - raus[a]['_treffer']),
                                    'verluste': sorted(raus[a]['_treffer'] - raus[b]['_treffer'])}
    for arm in arme:
        raus[arm].pop('_treffer')
    return raus


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('schritt', choices=('sichtung', 'bewerten'))
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--index', type=Path, default=LAEUFE / 'retrieval-2026-09-29/seitenuebergreifend')
    p.add_argument('--e2e', type=Path, default=LAEUFE / 'praefix-e2e-2026-09-29/ergebnisse.jsonl')
    p.add_argument('--sichtung', type=Path, default=LAEUFE / 'gold-mehrfach/sichtung.md')
    a = p.parse_args()
    _ausserhalb_git(a.sichtung.resolve().parent)
    a.sichtung.parent.mkdir(parents=True, exist_ok=True)
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    index = Index(a.index)
    zeilen = [json.loads(z) for z in a.e2e.read_text(encoding='utf-8').splitlines()]
    if a.schritt == 'sichtung':
        if a.sichtung.exists():
            p.error(f'{a.sichtung} existiert bereits – Entscheidungen würden überschrieben')
        print(json.dumps({'posten': sichtung(fragen, index, zeilen, a.sichtung)}))
        return
    ent = lies_entscheidungen(a.sichtung)
    mf = Mehrfach(fragen, index, ent)
    bericht = {'entscheidungen': len(ent), 'e2e': bewerte_e2e(zeilen, mf, _alle_fundstellen(index))}
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

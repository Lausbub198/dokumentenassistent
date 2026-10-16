"""Gepaarter Antwortlauf zum Kontext-Präfix (Plan 2026-09-29, nach Schritt 1.1). CLI: nur IDs/Kennzahlen.

Arm A (ohne Präfix) gegen einen Präfix-Arm (Standard B: Ordnerpfad + Dateiname). Beide Arme nutzen
dieselbe Schwelle (Standard 0,47: dort stoppen A und B je 6 der 15 Negativfragen, siehe
2026-09-29-praefix-test.md), denselben Reranker, dieselben Top 20 und denselben Antwortpfad wie das
Produkt (`suche._prompt`, `suche._karten`, Provider aus modelle.yaml). Der Präfix wirkt nur auf
Auswahl und Reihenfolge; im Prompt stehen die unveränderten Chunk-Texte mit ihren IDs.

Bewertung je Antwort: formal gültiges Zitat, Zitat aus der Zieldatei, Sollwert im zitierten Beleg,
**zitierter Chunk ist ein Gold-Zielabsatz** (golden-v2), Sollwert in der Antwort; Negativfragen:
abgewiesen ja/nein. Inhaltliche Richtigkeit wird nicht automatisch geprüft.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from dokumentenassistent import praefix_test as pt
from dokumentenassistent import seitenvergleich as sv
from dokumentenassistent.antwort_eval import bewerte_antwort, normalisiere_whitespace as ws
from dokumentenassistent.index import Index
from dokumentenassistent.suche import _karten, _prompt
from dokumentenassistent.typen import Antwort
from dokumentenassistent.pfade_privat import ARBEIT, BESTAND, FRAGEN, LAEUFE


def kontext(frage: str, vektor, fundstellen, texte, m, reranker, schwelle: float, k: int = 20) -> list | None:
    """None = an der Schwelle abgewiesen; sonst Indizes der Top k nach Reranking."""
    q = np.asarray(vektor, dtype=np.float32)
    scores = m @ (q / np.linalg.norm(q))
    order = sorted(range(len(fundstellen)), key=lambda i: (-float(scores[i]), fundstellen[i].id))
    if scores[order[0]] < schwelle:
        return None
    kandidaten = order[:k]
    neu = reranker.bewerte(frage, [texte[i] for i in kandidaten])
    return [i for _, i in sorted(zip(neu, kandidaten), key=lambda p: -p[0])]


def bewerte(frage: dict, text: str | None, top: list, ziel_ids: set[str]) -> dict:
    if text is None:  # Schwelle
        return {'abgewiesen': True, 'an_schwelle': True, 'zitat_zielabsatz': False, 'quellen_id_gueltig': False,
                'zieldatei_getroffen': False, 'beleg_whitespace': False, 'antwort_enthaelt_wert': False}
    karten = _karten(text, tuple(top))
    antwort = Antwort('gefunden' if karten else 'nicht_gefunden', text, karten)
    wert = frage.get('wortlaut_enthaelt') or ''
    werte = bewerte_antwort(antwort, frage.get('datei') or '', wert)
    return {'abgewiesen': not karten, 'an_schwelle': False,
            'zitat_zielabsatz': any(k.fundstelle.id in ziel_ids for k in karten),
            'quellen_id_gueltig': werte['quellen_id_gueltig'], 'zieldatei_getroffen': werte['zieldatei_getroffen'],
            'beleg_whitespace': werte['beleg_whitespace'],
            'antwort_enthaelt_wert': bool(ws(wert)) and bool(karten) and ws(wert) in ws(text)}


def auswerten(zeilen: list[dict], arme: tuple[str, str]) -> dict:
    raus = {}
    for arm in arme:
        eigene = {z['nr']: z for z in zeilen if z['arm'] == arm}
        pos = [z for z in eigene.values() if z['status'] == 'gefunden']
        neg = [z for z in eigene.values() if z['status'] != 'gefunden']
        raus[arm] = {
            'fragen': len(eigene), 'technische_fehler': sum('fehler' in z for z in eigene.values()),
            'zitat_zielabsatz': sum(z.get('zitat_zielabsatz', False) for z in pos),
            'beleg_whitespace': sum(z.get('beleg_whitespace', False) for z in pos),
            'zieldatei_getroffen': sum(z.get('zieldatei_getroffen', False) for z in pos),
            'antwort_enthaelt_wert': sum(z.get('antwort_enthaelt_wert', False) for z in pos),
            'positiv_abgewiesen': sum(z.get('abgewiesen', False) for z in pos),
            'negativ_abgewiesen': sum(z.get('abgewiesen', False) for z in neg),
            'negativ_an_schwelle': sum(z.get('an_schwelle', False) for z in neg),
            'sekunden_median': float(np.median([z['sekunden'] for z in eigene.values()])) if eigene else None,
        }
    if len(arme) == 2:
        a, b = arme
        ta = {z['nr'] for z in zeilen if z['arm'] == a and z.get('zitat_zielabsatz')}
        tb = {z['nr'] for z in zeilen if z['arm'] == b and z.get('zitat_zielabsatz')}
        raus['gepaart_zitat_zielabsatz'] = {'gewinne': sorted(tb - ta), 'verluste': sorted(ta - tb)}
    return raus


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--retrieval', type=Path, default=LAEUFE / 'retrieval-2026-09-29')
    p.add_argument('--praefix', type=Path, default=LAEUFE / 'praefix-2026-09-29')
    p.add_argument('--quelle', type=Path, default=BESTAND)
    p.add_argument('--einordnung', type=Path, default=ARBEIT)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--modelle', type=Path, default=Path(__file__).resolve().parents[2] / 'modelle.yaml')
    p.add_argument('--private', type=Path, default=LAEUFE / 'praefix-e2e-2026-09-29')
    p.add_argument('--arm', default='B', choices=[x for x in pt.ARME if x != 'A'])
    p.add_argument('--schwelle', type=float, default=0.47)
    p.add_argument('--top-n', type=int, default=20, help='Chunks im Antwortprompt (Reranker sieht immer 20)')
    p.add_argument('--ohne-a', action='store_true', help='nur den Präfix-Arm laufen lassen (A liegt schon vor)')
    a = p.parse_args()
    sv._ausserhalb_git(a.private.resolve())
    a.private.mkdir(parents=True, exist_ok=True)
    import os
    os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from huggingface_hub import try_to_load_from_cache
    from dokumentenassistent.provider import lade_modelle, lade_provider_suche
    from dokumentenassistent.retrieval_reranker import CrossEncoderReranker

    provider = lade_provider_suche(a.modelle) or lade_modelle(a.modelle)
    einbetter = lade_modelle(a.modelle)
    revision = einbetter.embedding_revision()
    if revision != json.loads((a.retrieval / 'manifest.json').read_text())['embedding_revision']:
        p.error('Embedding-Revision weicht vom gespeicherten Retrievallauf ab')
    konfig = try_to_load_from_cache('BAAI/bge-reranker-v2-m3', 'config.json')
    if not isinstance(konfig, str):
        p.error('Reranker-Snapshot fehlt im lokalen Cache')
    reranker = CrossEncoderReranker(str(Path(konfig).parent))
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    vektoren = json.loads((a.retrieval / 'fragenvektoren.json').read_text())['vektoren']
    index = Index(a.retrieval / 'seitenuebergreifend')
    fundstellen, _ = sv._matrix(index, revision)
    pfad, meta, kopf = pt.pfade(a.quelle), pt.einordnung(a.einordnung), pt.koepfe(fundstellen)
    abschnitt = pt.abschnitte(fundstellen)
    arme = (a.arm,) if a.ohne_a else ('A', a.arm)
    daten = {}
    for arm in arme:
        texte = pt.texte_je_arm(arm, fundstellen, pfad, meta, kopf, abschnitt)
        daten[arm] = (texte, pt.matrix(texte, einbetter, a.praefix / f'vektoren-{arm}', revision))
    manifest = {'arme': list(arme), 'schwelle': a.schwelle, 'top_n': a.top_n, 'llm': provider.llm_modell,
                'kontext': provider.kontext, 'think': provider.think, 'revision': revision, 'gold': str(a.gold)}
    mpfad = a.private / 'manifest.json'
    if mpfad.exists() and json.loads(mpfad.read_text()) != manifest:
        p.error('Manifest weicht vom begonnenen Lauf ab – anderen --private-Ordner wählen')
    mpfad.write_text(json.dumps(manifest, indent=1))
    ausgabe = a.private / 'ergebnisse.jsonl'
    fertig = {(z['arm'], z['nr']) for z in map(json.loads, ausgabe.read_text().splitlines())} if ausgabe.exists() else set()
    for n, (frage, vektor) in enumerate(zip(fragen, vektoren)):
        for arm in (arme if n % 2 == 0 else arme[::-1]):
            if (arm, frage['nr']) in fertig:
                continue
            texte, m = daten[arm]
            start = time.monotonic()
            zeile = {'arm': arm, 'nr': frage['nr'], 'status': frage['status']}
            idx = kontext(frage['frage'], vektor, fundstellen, texte, m, reranker, a.schwelle)
            idx = idx[:a.top_n] if idx else idx
            top = [fundstellen[i] for i in idx] if idx else []
            try:
                text = provider.generate_text(_prompt(tuple(top), frage['frage'])) if idx else None
            except Exception as exc:  # protokollieren, Lauf fortsetzen; erneuter Start holt die Frage nach
                print(f'Frage {frage["nr"]}/{arm}: {type(exc).__name__}', flush=True)
                continue
            ziel = sv._ziel_ids(frage, index) if frage['status'] == 'gefunden' else set()
            zeile.update(bewerte(frage, text, top, ziel), sekunden=round(time.monotonic() - start, 1),
                         kontext_ids=[f.id for f in top], antwort=text)  # privat
            with ausgabe.open('a', encoding='utf-8') as f:
                f.write(json.dumps(zeile, ensure_ascii=False) + '\n')
        if (n + 1) % 10 == 0:
            print(f'Fragen: {n + 1}/{len(fragen)}', flush=True)
    zeilen = [json.loads(z) for z in ausgabe.read_text().splitlines()]
    bericht = auswerten(zeilen, arme)
    (a.private / 'bericht.json').write_text(json.dumps(bericht, indent=1))
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

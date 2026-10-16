"""Pilot strukturierte Auslesung (Plan 2026-09-29, Schritt 1.5, Stufe 1). CLI gibt nur IDs/Kennzahlen aus.

Zwei Fragen, ohne Embedding und ohne LLM:
    1. Auslesung: Steht der ORIGINAL-Gold-Zielabsatz (golden.json, nicht v2) wortgetreu im
       Docling-Text? Verglichen mit dem pdftotext-Index derselben Datei.
    2. Struktur: Hat der Zielabsatz bei den Verlustfällen eine erkannte Überschrift über sich?

Private Markdown-Exporte und Überschriften landen nur in --private (zum Nachlesen).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from dokumentenassistent.antwort_eval import normalisiere_whitespace as ws
from dokumentenassistent.gold_bereinigung import locker
from dokumentenassistent.index import Index
from dokumentenassistent.seitenvergleich import _ausserhalb_git, _ziel_dateien
from dokumentenassistent.pfade_privat import FRAGEN, LAEUFE


def enthalten(ziel: str, text: str) -> dict:
    return {'exakt': bool(ziel) and ws(ziel) in ws(text), 'locker': bool(ziel) and locker(ziel) in locker(text)}


def ueberschrift_vor(elemente: list[tuple[str, str]], ziel: str, wert: str) -> list[str]:
    """elemente: [(art, text)] in Lesereihenfolge; art 'titel'|'ueberschrift'|'text'.
    Liefert die Überschriften vor dem Element, in dem der Zielabsatz (sonst der Sollwert) beginnt."""
    texte = [ws(t) for _, t in elemente]
    gesamt, starts = '', []
    for t in texte:
        starts.append(len(gesamt))
        gesamt += t + ' '
    for suche in (ws(ziel)[:80], ws(wert)):
        pos = gesamt.find(suche) if suche else -1
        if pos >= 0:
            idx = max(i for i, s in enumerate(starts) if s <= pos)
            return [t for (art, t), i in zip(elemente, range(idx)) if art in ('titel', 'ueberschrift')]
    return []


def _elemente(doc) -> list[tuple[str, str]]:
    from docling_core.types.doc import SectionHeaderItem, TitleItem
    raus = []
    for item, _ in doc.iterate_items():
        text = getattr(item, 'text', None)
        if text is None:
            continue
        art = 'titel' if isinstance(item, TitleItem) else 'ueberschrift' if isinstance(item, SectionHeaderItem) else 'text'
        raus.append((art, text))
    return raus


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden.json')
    p.add_argument('--index', type=Path, default=LAEUFE / 'struktur-2026-09-29/seitenuebergreifend')
    p.add_argument('--retrieval-bericht', type=Path,
                   default=LAEUFE / 'retrieval-2026-09-29/bericht.json')
    p.add_argument('--private', type=Path, default=LAEUFE / 'docling-2026-09-29')
    a = p.parse_args()
    _ausserhalb_git(a.private.resolve())
    (a.private / 'md').mkdir(parents=True, exist_ok=True)
    from docling.document_converter import DocumentConverter
    konverter = DocumentConverter()
    fragen = [f for f in json.loads(a.gold.read_text(encoding='utf-8'))['fragen'] if f['status'] == 'gefunden']
    index = Index(a.index)
    b = json.loads(a.retrieval_bericht.read_text())
    verluste = set(b['ranking_verluste']['seitenuebergreifend']) | set(b['schwelle_blockiert']['seitenuebergreifend'])
    zustand_pfad = a.private / 'zustand.json'
    zustand = json.loads(zustand_pfad.read_text()) if zustand_pfad.exists() else {'dateien': {}, 'fehler': {}}
    dateien = {d.hash: d for f in fragen for d in _ziel_dateien(f, index)}
    for n, (h, datei) in enumerate(sorted(dateien.items()), 1):
        if h in zustand['dateien'] or h in zustand['fehler']:
            continue
        start = time.monotonic()
        try:
            doc = konverter.convert(datei.pfad).document
        except Exception as exc:  # Docling-Fehler je Datei protokollieren, Lauf fortsetzen
            zustand['fehler'][h] = type(exc).__name__
        else:
            (a.private / 'md' / f'{h[:16]}.md').write_text(doc.export_to_markdown(), encoding='utf-8')
            (a.private / 'md' / f'{h[:16]}.elemente.json').write_text(
                json.dumps(_elemente(doc), ensure_ascii=False), encoding='utf-8')
            zustand['dateien'][h] = {'sekunden': round(time.monotonic() - start, 1)}
        zustand_pfad.write_text(json.dumps(zustand), encoding='utf-8')
        print(f'{n}/{len(dateien)} Dateien', flush=True)
    zeilen = []
    for f in fragen:
        ziel, wert = f.get('zielabsatz') or '', f.get('wortlaut_enthaelt') or ''
        kandidaten = [d.hash for d in _ziel_dateien(f, index)]
        index_text = ' '.join(fs.text for h in kandidaten for fs in index.fundstellen(h))
        z = {'nr': f['nr'], 'verlust': f['nr'] in verluste,
             'index': enthalten(ziel, index_text), 'docling': {'exakt': False, 'locker': False},
             'docling_fehler': all(h in zustand['fehler'] for h in kandidaten), 'ueberschriften': 0}
        for h in kandidaten:
            elemente_pfad = a.private / 'md' / f'{h[:16]}.elemente.json'
            if not elemente_pfad.exists():
                continue
            elemente = [tuple(e) for e in json.loads(elemente_pfad.read_text(encoding='utf-8'))]
            treffer = enthalten(ziel, ' '.join(t for _, t in elemente))
            z['docling'] = {k: z['docling'][k] or v for k, v in treffer.items()}
            z['ueberschriften'] = max(z['ueberschriften'], len(ueberschrift_vor(elemente, ziel, wert)))
        zeilen.append(z)
    (a.private / 'fragen.json').write_text(json.dumps(zeilen), encoding='utf-8')
    zaehle = lambda bed: sorted(z['nr'] for z in zeilen if bed(z))
    bericht = {
        'dateien': len(dateien), 'docling_fehler': len(zustand['fehler']),
        'sekunden_median': sorted(v['sekunden'] for v in zustand['dateien'].values())[len(zustand['dateien']) // 2]
        if zustand['dateien'] else None,
        'zielabsatz_exakt': {'index': len(zaehle(lambda z: z['index']['exakt'])),
                             'docling': len(zaehle(lambda z: z['docling']['exakt']))},
        'zielabsatz_locker': {'index': len(zaehle(lambda z: z['index']['locker'])),
                              'docling': len(zaehle(lambda z: z['docling']['locker']))},
        'nur_docling_exakt': zaehle(lambda z: z['docling']['exakt'] and not z['index']['exakt']),
        'nur_index_exakt': zaehle(lambda z: z['index']['exakt'] and not z['docling']['exakt']),
        'verluste': len(zaehle(lambda z: z['verlust'])),
        'verluste_mit_ueberschrift': zaehle(lambda z: z['verlust'] and z['ueberschriften'] > 0),
        'alle_mit_ueberschrift': len(zaehle(lambda z: z['ueberschriften'] > 0)),
    }
    (a.private / 'bericht.json').write_text(json.dumps(bericht, indent=1), encoding='utf-8')
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

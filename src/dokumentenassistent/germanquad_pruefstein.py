"""GermanQuAD als zweiter, unabhängiger Prüfstein für das Produkt (Testprogramm, 03.10.2026).

Fragen und Texte stammen von Dritten (deutsche Wikipedia, menschliche Annotatoren; CC-BY-4.0, siehe
`beweise/germanquad/README.md`). Regeln, vorab festgelegt:

- Bestand: je Korpus-Absatz eine Textdatei `<corpus-id>.txt`. Der Datensatz enthält keine Antworttexte;
  bewertet wird deshalb auf Absatzebene: Treffer = Beleg bzw. Kontext-Chunk aus der Datei des Soll-Absatzes.
- Verglichen werden zwei vollständige Konfigurationen (alt: modelle.yaml des Repos; neu: Kaskade-Konfiguration),
  jeweils mit eigenem Index über `neu_einlesen einlesen`.
- `suche`: alle 2204 Fragen, ohne Antwortmodell: Soll-Datei unter den Top 20 nach Reranking, auf Rang 1.
- `antworten`: feste Stichprobe von 200 Fragen (Seed 42) über `Werkstatt.frage`, also den Produktpfad.
- Keine Negativfragen im Datensatz: Abweisung ist hier nicht messbar. Die Dateinamen sind Kennungen, ein
  Pfad-Präfix trägt hier keine Information.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import time
from dokumentenassistent.pfade_privat import GERMANQUAD

STICHPROBE, SEED = 200, 42


def vorbereiten(quelle: Path, ziel: Path) -> dict:
    from dokumentenassistent.germanquad import _spalten
    korpus = _spalten(quelle / 'corpus.arrow', ('_id', 'text'))
    fragen = _spalten(quelle / 'queries.arrow', ('_id', 'text'))
    qrels = _spalten(quelle / 'qrels.arrow', ('query-id', 'corpus-id'))
    bestand = ziel / 'bestand'
    bestand.mkdir(parents=True, exist_ok=True)
    for z in korpus:
        (bestand / f"{z['_id']}.txt").write_text(z['text'], encoding='utf-8')
    soll = {q['query-id']: q['corpus-id'] for q in qrels}
    gold = [{'nr': i, 'frage': q['text'], 'status': 'gefunden', 'datei': f"{soll[q['_id']]}.txt"}
            for i, q in enumerate(fragen, 1)]
    (ziel / 'gold.json').write_text(json.dumps({'fragen': gold}, ensure_ascii=False), encoding='utf-8')
    return {'absaetze': len(korpus), 'fragen': len(gold)}


def stichprobe(gold: list[dict]) -> list[dict]:
    return sorted(random.Random(SEED).sample(gold, min(STICHPROBE, len(gold))), key=lambda f: f['nr'])


def einbetten_in_bloecken(provider, texte: list[str], block: int = 32) -> list:
    """Wie das Produkt (Werkstatt.EMBED_BLOCK): alle 2204 Fragen in einem Aufruf lehnte Ollama mit HTTP 400 ab."""
    return [v for i in range(0, len(texte), block) for v in provider.embed(texte[i:i + block])]


def suche_ohne_llm(w, gold: list[dict]) -> dict:
    """Soll-Datei unter den Top 20 nach Reranking (mit Präfix, wie im Produkt) und auf Rang 1."""
    import dataclasses
    import numpy as np
    from dokumentenassistent.retrieval_reranker import rerank
    from dokumentenassistent.suche import dense_rang
    provider = w.provider_suche or w.provider
    paare = w.index.durchsuchbare_fundstellen(modell_revision=provider.embedding_revision(),
                                              vorverarbeitung=w._vorverarbeitung())
    nach_id, praefixe = {f.id: f for f, _ in paare}, w._praefixe()
    fuer_reranker = {i: dataclasses.replace(f, text=praefixe.get(f.datei_hash, '') + f.text) for i, f in nach_id.items()}
    vektoren = einbetten_in_bloecken(provider, [f['frage'] for f in gold])
    top20 = rang1 = 0
    for f, v in zip(gold, vektoren):
        rangliste = rerank(dense_rang(v, paare), fuer_reranker, f['frage'], w.sucheinstellungen.reranker,
                           w.sucheinstellungen.rerank_k)[:20]
        namen = [nach_id[i].datei_name for i, _ in rangliste]
        top20 += f['datei'] in namen
        rang1 += bool(namen) and namen[0] == f['datei']
    return {'fragen': len(gold), 'top20': top20, 'rang1': rang1, 'absaetze_im_index': len({f.datei_hash for f, _ in paare})}


def antworten(w, fragen: list[dict], ausgabe: Path) -> dict:
    fertig = {json.loads(z)['nr'] for z in ausgabe.read_text().splitlines()} if ausgabe.exists() else set()
    for f in fragen:
        if f['nr'] in fertig:
            continue
        start = time.monotonic()
        a = w.frage(f['frage'])
        zeile = {'nr': f['nr'], 'korrekt': any(k.fundstelle.datei_name == f['datei'] for k in a.karten),
                 'abgewiesen': not a.karten, 'sekunden': round(time.monotonic() - start, 1)}
        with ausgabe.open('a', encoding='utf-8') as out:
            out.write(json.dumps(zeile) + '\n')
    zeilen = [json.loads(z) for z in ausgabe.read_text().splitlines()]
    return {'fragen': len(zeilen), 'korrekt': sum(z['korrekt'] for z in zeilen),
            'abgewiesen': sum(z['abgewiesen'] for z in zeilen),
            'sekunden_median': sorted(z['sekunden'] for z in zeilen)[len(zeilen) // 2] if zeilen else None}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('schritt', choices=('vorbereiten', 'suche', 'antworten'))
    p.add_argument('--ordner', type=Path, default=GERMANQUAD)
    p.add_argument('--quelle', type=Path, default=Path(__file__).resolve().parents[2] / 'beweise/germanquad')
    p.add_argument('--arbeitsordner', type=Path, help='Index der zu messenden Konfiguration')
    p.add_argument('--modelle', type=Path, help='Konfiguration passend zum Arbeitsordner')
    a = p.parse_args()
    if a.schritt == 'vorbereiten':
        print(json.dumps(vorbereiten(a.quelle, a.ordner)))
        return
    if not (a.arbeitsordner and a.modelle):
        p.error('--arbeitsordner und --modelle sind nötig')
    from dokumentenassistent.neu_einlesen import werkstatt
    w = werkstatt(a.ordner / 'bestand', a.arbeitsordner / 'zielablage', a.modelle, a.arbeitsordner)
    gold = json.loads((a.ordner / 'gold.json').read_text(encoding='utf-8'))['fragen']
    if a.schritt == 'suche':
        bericht = suche_ohne_llm(w, gold)
    else:
        bericht = antworten(w, stichprobe(gold), a.arbeitsordner / 'antworten.jsonl')
    (a.arbeitsordner / f'bericht-{a.schritt}.json').write_text(json.dumps(bericht, indent=1))
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

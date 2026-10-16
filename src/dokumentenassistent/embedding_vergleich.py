"""C1 (Testprogramm 2026-09-30): Embedding-Modelle fair vergleichen. CLI gibt nur IDs und Kennzahlen aus.

Das Embedding liefert die Kandidaten für den Reranker; entscheidend ist deshalb, ob der Zielabsatz
unter den ersten 20/50 Kandidaten ist und nach dem Reranking im Top-20-Kontext landet – nicht R@1.
Der frühere 8B-Test (25.09.) hat R@1 ohne Reranker bewertet.

Arme, gleiche Chunks (seitenübergreifend, ohne Präfix), gleicher Reranker (bge-reranker-v2-m3):
    e06   qwen3-embedding:0.6b, Frage ohne Anweisung (heutiger Stand)
    e06i  qwen3-embedding:0.6b, Frage mit offizieller Qwen-Anweisung
    e8    Qwen3-Embedding-8B Q4_K_M, Frage ohne Anweisung
    e8i   Qwen3-Embedding-8B Q4_K_M, Frage mit offizieller Qwen-Anweisung
    e8B   Qwen3-Embedding-8B Q4_K_M + Pfad-Präfix (wie Präfix-Arm B, auch für den Reranker)
    e4B   qwen3-embedding:4b + Pfad-Präfix (03.10.: 8B und gemma passen nicht gleichzeitig in den Speicher)
Die Anweisung ist Qwens dokumentierte Standardformulierung, nicht an diesen Bestand angepasst.
Keine Schwelle: sie ist modellspezifisch und wird getrennt kalibriert (C6).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dokumentenassistent import praefix_test as pt
from dokumentenassistent import seitenvergleich as sv
from dokumentenassistent.index import Index, validiere_vektoren
from dokumentenassistent.pfade_privat import BESTAND, FRAGEN, LAEUFE

ANWEISUNG = 'Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:'
MODELLE = {'e06': ('qwen3-embedding:0.6b', False), 'e06i': ('qwen3-embedding:0.6b', True),
           'e8': ('hf.co/Qwen/Qwen3-Embedding-8B-GGUF:Q4_K_M', False),
           'e8i': ('hf.co/Qwen/Qwen3-Embedding-8B-GGUF:Q4_K_M', True),
           'e8B': ('hf.co/Qwen/Qwen3-Embedding-8B-GGUF:Q4_K_M', False),
           'e4B': ('qwen3-embedding:4b', False)}
PRAEFIX = {'e8B': 'B', 'e4B': 'B'}


def frage_text(frage: str, anweisung: bool) -> str:
    return f'{ANWEISUNG}{frage}' if anweisung else frage


def messe(fragen, qvek: np.ndarray, m: np.ndarray, fundstellen, index, reranker, texte=None) -> dict[int, dict]:
    texte = texte or [f.text for f in fundstellen]
    raus = {}
    for f, q in zip(fragen, qvek):
        scores = m @ q
        order = sorted(range(len(fundstellen)), key=lambda i: (-float(scores[i]), fundstellen[i].id))
        ziel = sv._ziel_ids(f, index) if f['status'] == 'gefunden' else set()
        rang = next((r for r, i in enumerate(order, 1) if fundstellen[i].id in ziel), None)
        zeile = {'dense_rang': rang, 'max_score': float(scores[order[0]])}
        for pool in (20, 50):
            kand = order[:pool]
            neu = reranker.bewerte(f['frage'], [texte[i] for i in kand])
            kontext = [i for _, i in sorted(zip(neu, kand), key=lambda p: -p[0])][:20]
            zeile[f'kontext_pool{pool}'] = any(fundstellen[i].id in ziel for i in kontext)
            zeile[f'rang1_pool{pool}'] = bool(kontext) and fundstellen[kontext[0]].id in ziel
        raus[f['nr']] = zeile
    return raus


def auswerten(fragen, je_arm: dict[str, dict[int, dict]]) -> dict:
    pos = [f['nr'] for f in fragen if f['status'] == 'gefunden']
    bericht = {}
    for arm, r in je_arm.items():
        r = {int(k): v for k, v in r.items()}
        bericht[arm] = {
            **{f'dense_top{k}': sum(1 for n in pos if r[n]['dense_rang'] and r[n]['dense_rang'] <= k) for k in (1, 20, 50)},
            **{f'kontext_pool{p}': sum(r[n][f'kontext_pool{p}'] for n in pos) for p in (20, 50)},
            **{f'rang1_pool{p}': sum(r[n][f'rang1_pool{p}'] for n in pos) for p in (20, 50)},
        }
    if 'e06' in je_arm:
        basis = {int(k) for k, v in je_arm['e06'].items() if v['kontext_pool20'] and int(k) in pos}
        for arm, r in je_arm.items():
            t = {int(k) for k, v in r.items() if v['kontext_pool20'] and int(k) in pos}
            bericht[arm]['pool20_gewinne_vs_e06'] = sorted(t - basis)
            bericht[arm]['pool20_verluste_vs_e06'] = sorted(basis - t)
    return bericht


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--retrieval', type=Path, default=LAEUFE / 'retrieval-2026-09-29')
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--private', type=Path, default=LAEUFE / 'c1-embedding-2026-09-30')
    p.add_argument('--arme', default=','.join(MODELLE))
    a = p.parse_args()
    sv._ausserhalb_git(a.private.resolve())
    a.private.mkdir(parents=True, exist_ok=True)
    import os
    os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from huggingface_hub import try_to_load_from_cache
    from dokumentenassistent.provider import OllamaProvider
    from dokumentenassistent.retrieval_reranker import CrossEncoderReranker

    reranker = CrossEncoderReranker(str(Path(try_to_load_from_cache('BAAI/bge-reranker-v2-m3', 'config.json')).parent))
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    basis_rev = json.loads((a.retrieval / 'manifest.json').read_text())['embedding_revision']
    index = Index(a.retrieval / 'seitenuebergreifend')
    fundstellen, _ = sv._matrix(index, basis_rev)  # feste Chunk-Reihenfolge für alle Arme
    ergebnispfad = a.private / 'ergebnisse.json'
    je_arm = json.loads(ergebnispfad.read_text()) if ergebnispfad.exists() else {}
    for arm in a.arme.split(','):
        modell, anweisung = MODELLE[arm]
        texte = (pt.texte_je_arm(PRAEFIX[arm], fundstellen, pt.pfade(BESTAND), {}, {})
                 if arm in PRAEFIX else [f.text for f in fundstellen])
        provider = OllamaProvider('http://localhost:11434', modell, '', timeout=600)
        revision = provider.embedding_revision()
        m = pt.matrix(texte, provider, a.private / f'chunks-{modell.replace("/", "_").replace(":", "_")}', revision)
        qv = provider.embed([frage_text(f['frage'], anweisung) for f in fragen])
        validiere_vektoren(qv, len(fragen))
        q = np.asarray(qv, dtype=np.float32)
        q = q / np.linalg.norm(q, axis=1)[:, None]
        je_arm[arm] = messe(fragen, q, m, fundstellen, index, reranker, texte)
        ergebnispfad.write_text(json.dumps(je_arm), encoding='utf-8')
        print(f'Arm {arm} gemessen', flush=True)
    bericht = auswerten(fragen, je_arm)
    (a.private / 'bericht.json').write_text(json.dumps(bericht, indent=1), encoding='utf-8')
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

"""Kontext-Präfix je Chunk: Retrieval-Gate ohne Antwort-LLM. CLI gibt nur IDs und Kennzahlen aus.

Hypothese (2026-09-29-gold-bereinigung-und-retrieval.md): Bei 20 von 24 Verlusten ist die richtige
Datei in den dichten Top 20, aber nicht der Zielabsatz. Der Absatz trägt die Dokument-Identität
(welcher Vertrag, welche Wohnung, welches Jahr) nicht in sich. Getestet wird, ob ein Präfix vor dem
Chunk – nur für Embedding und Reranker, nicht im Index – den Zielabsatz nach vorn bringt.

Arme, identisch bis auf den eingebetteten/gerankten Text:
    A  ohne Präfix (Kontrolle; muss den gespeicherten Retrievallauf reproduzieren)
    B  Ordnerpfad + Dateiname
    C  Einordnung: Typ, Kategorie, belegte Felder (Datum, Aussteller, Betrag, Rechnungsnummer)
    D  B + C
    E  Dokumentkopf: die ersten 40 Wörter des Dokuments
    F  Abschnittsüberschrift (Regeln unten)
    G  D + F
    H  B + F  (ohne LLM-Einordnung verfügbar)

Überschrift-Regeln, vor der Messung festgelegt und allgemein gehalten (keine korpusspezifischen
Begriffe, nichts aus Gold oder Fehlfällen abgeleitet): Eine Zeile ist eine Überschrift, wenn sie
höchstens 10 Wörter hat, mindestens ein Wort aus 3+ Buchstaben, nicht auf . , ; endet, keine
Datumszeile ist und (a) mit einer Abschnittsnummerierung beginnt (§ 5, Art. 3, Artikel 3, 2., 2.1,
IV., a), B)) oder (b) überwiegend groß geschrieben ist (≥ 4 Buchstaben, ≥ 80 % Großbuchstaben).
Präfix eines Chunks ist die letzte Überschrift vor ihm im Dokument; beginnt der Chunk selbst mit
einer Überschrift, bekommt er keinen Abschnittspräfix.

Gemessen wird einmal ohne Schwelle; das Schwellen-Ergebnis (0,49 auf den besten Kosinus) wird daraus
abgeleitet. Präfixe verschieben die Kosinusverteilung – deshalb werden beide Zahlen berichtet.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import numpy as np

from dokumentenassistent import seitenvergleich as sv
from dokumentenassistent.index import Index, validiere_vektoren
from dokumentenassistent.pfade_privat import ARBEIT, BESTAND, FRAGEN, LAEUFE

ARME = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')
KOPF_WOERTER = 40
FELDER = ('datum', 'aussteller', 'betrag', 'rechnungsnummer')
_NUMMERIERUNG = re.compile(r'^(§+\s*\d+[a-z]?|(Art\.|Artikel)\s*\d+[a-z]?|\d+(\.\d+)*\.?|[IVXLC]+\.|[A-Za-z]\))\s+\S')
_MONATE = r'(Jan|Feb|Mär|Mar|Apr|Mai|May|Jun|Jul|Aug|Sep|Okt|Oct|Nov|Dez|Dec)'
_DATUM = re.compile(rf'^\d{{1,2}}\.\s*{_MONATE}|\b\d{{1,2}}\.\d{{1,2}}\.\d{{2,4}}\b', re.I)


def ist_ueberschrift(zeile: str) -> bool:
    z = zeile.strip()
    woerter = z.split()
    if not z or len(woerter) > 10 or z[-1] in '.,;' or _DATUM.search(z):
        return False
    if not re.search(r'[^\W\d_]{3}', z):
        return False
    buchstaben = [c for c in z if c.isalpha()]
    gross = len(buchstaben) >= 4 and sum(c.isupper() for c in buchstaben) / len(buchstaben) >= 0.8
    return bool(_NUMMERIERUNG.match(z)) or gross


def abschnitte(fundstellen: list) -> dict[str, str]:
    """Je Fundstellen-ID die letzte Überschrift davor im selben Dokument ('' wenn keine/Chunk beginnt mit einer)."""
    raus: dict[str, str] = {}
    je_datei: dict[str, list] = {}
    for f in fundstellen:
        je_datei.setdefault(f.datei_hash, []).append(f)
    for chunks in je_datei.values():
        letzte = ''
        for f in sorted(chunks, key=lambda f: (f.seite, f.absatz)):
            zeilen = [z for z in f.text.split('\n') if z.strip()]
            raus[f.id] = '' if zeilen and ist_ueberschrift(zeilen[0]) else letzte
            for z in zeilen:
                if ist_ueberschrift(z):
                    letzte = ' '.join(z.split())
    return raus


def pfade(quelle: Path) -> dict[str, str]:
    db = quelle / '.dokumentenassistent' / 'index.sqlite'
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as v:
        return {h: str(Path(p).relative_to(quelle)) for h, p in v.execute('SELECT hash, pfad FROM dateien')}


def einordnung(arbeit: Path) -> dict[str, dict]:
    db = arbeit / '.dokumentenassistent' / 'index.sqlite'
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as v:
        rows = v.execute('SELECT datei_hash, kategorie, typ, felder FROM vorschlaege').fetchall()
    raus = {}
    for h, kat, typ, felder in rows:
        belegt = {f['name']: f['wert'] for f in json.loads(felder)
                  if f.get('status') == 'belegt' and f.get('name') in FELDER and f.get('wert')}
        raus[h] = {'kategorie': kat, 'typ': typ, **belegt}
    return raus


def praefix(arm: str, pfad: str | None, meta: dict | None, kopf: str, abschnitt: str = '') -> str:
    teile = []
    if arm in ('B', 'D', 'G', 'H') and pfad:
        teile.append(f'Dokument: {pfad}')
    if arm in ('C', 'D', 'G') and meta:
        werte = [f'{k}: {meta[k]}' for k in ('typ', 'kategorie', *FELDER) if meta.get(k)]
        if werte:
            teile.append('; '.join(werte))
    if arm == 'E' and kopf:
        teile.append(f'Dokumentanfang: {kopf}')
    if arm in ('F', 'G', 'H') and abschnitt:
        teile.append(f'Abschnitt: {abschnitt}')
    return ('\n'.join(teile) + '\n\n') if teile else ''


def koepfe(fundstellen: list) -> dict[str, str]:
    erste: dict[str, list] = {}
    for f in sorted(fundstellen, key=lambda f: (f.datei_hash, f.seite, f.absatz)):
        erste.setdefault(f.datei_hash, []).append(f.text)
    return {h: ' '.join(' '.join(t).split()[:KOPF_WOERTER]) for h, t in erste.items()}


def texte_je_arm(arm: str, fundstellen: list, pfad: dict, meta: dict, kopf: dict,
                 abschnitt: dict | None = None) -> list[str]:
    abschnitt = abschnitt or {}
    return [praefix(arm, pfad.get(f.datei_hash), meta.get(f.datei_hash), kopf.get(f.datei_hash, ''),
                    abschnitt.get(f.id, '')) + f.text
            for f in fundstellen]


def matrix(texte: list[str], provider, cache: Path, revision: str) -> np.ndarray:
    schluessel = hashlib.sha256(('\x00'.join(texte) + revision).encode()).hexdigest()[:16]
    pfad = cache.with_name(f'{cache.name}-{schluessel}.npy')
    if pfad.exists():
        m = np.load(pfad)
    else:
        vektoren = []
        for i in range(0, len(texte), 16):
            vektoren.extend(provider.embed(texte[i:i + 16]))
        validiere_vektoren(vektoren, len(texte))
        if provider.embedding_revision() != revision:
            raise ValueError('Embedding-Revision wechselte während des Laufs')
        m = np.asarray(vektoren, dtype=np.float32)
        np.save(pfad, m)
    return m / np.linalg.norm(m, axis=1)[:, None]


def messe_arm(fragen, vektoren, index, fundstellen, texte, m, reranker) -> dict[int, dict]:
    mit_praefix = [dataclasses.replace(f, text=t) for f, t in zip(fundstellen, texte)]
    alt, sv._SCHWELLE = sv._SCHWELLE, -1.0  # Schwelle hier aus; unten abgeleitet
    try:
        return {f['nr']: sv._messe_frage(f, v, index, mit_praefix, m, reranker)
                for f, v in zip(fragen, vektoren)}
    finally:
        sv._SCHWELLE = alt


def auswerten(fragen: list[dict], je_arm: dict[str, dict[int, dict]], schwelle: float = 0.49) -> dict:
    pos = [f['nr'] for f in fragen if f['status'] == 'gefunden']
    neg = [f['nr'] for f in fragen if f['status'] != 'gefunden']
    def treffer(r, gate):
        return r['kontexttreffer'] and (not gate or r['max_score'] >= schwelle)
    bericht = {}
    for arm, r in je_arm.items():
        mit = {n for n in pos if treffer(r[n], True)}
        bericht[arm] = {
            'kontexttreffer_mit_schwelle': len(mit),
            'kontexttreffer_ohne_schwelle': sum(treffer(r[n], False) for n in pos),
            'dense_top20': sum(1 for n in pos if r[n]['zielchunk_rang_dense'] and r[n]['zielchunk_rang_dense'] <= 20),
            'reranked_rang1': sum(1 for n in pos if r[n]['zielchunk_rang_reranked'] == 1),
            'positiv_an_schwelle': sorted(n for n in pos if r[n]['max_score'] < schwelle),
            'negativ_an_schwelle_gestoppt': sum(1 for n in neg if r[n]['max_score'] < schwelle),
            'max_score_median_pos': round(float(np.median([r[n]['max_score'] for n in pos])), 3),
            'max_score_median_neg': round(float(np.median([r[n]['max_score'] for n in neg])), 3),
            'verluste_mit_schwelle': sorted(set(pos) - mit),
        }
    basis = set(pos) - set(bericht['A']['verluste_mit_schwelle'])
    for arm in je_arm:
        treffer_arm = set(pos) - set(bericht[arm]['verluste_mit_schwelle'])
        bericht[arm]['gewinne_vs_A'] = sorted(treffer_arm - basis)
        bericht[arm]['verluste_vs_A'] = sorted(basis - treffer_arm)
    return bericht


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--retrieval', type=Path, default=LAEUFE / 'retrieval-2026-09-29')
    p.add_argument('--quelle', type=Path, default=BESTAND)
    p.add_argument('--einordnung', type=Path, default=ARBEIT)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--private', type=Path, default=LAEUFE / 'praefix-2026-09-29')
    p.add_argument('--arme', default=','.join(ARME))
    a = p.parse_args()
    sv._ausserhalb_git(a.private.resolve())
    a.private.mkdir(parents=True, exist_ok=True)
    import os
    os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from huggingface_hub import try_to_load_from_cache
    from dokumentenassistent.provider import OllamaProvider
    from dokumentenassistent.retrieval_reranker import CrossEncoderReranker

    manifest = json.loads((a.retrieval / 'manifest.json').read_text())
    provider = OllamaProvider('http://localhost:11434', 'qwen3-embedding:0.6b', '')
    revision = provider.embedding_revision()
    if revision != manifest['embedding_revision']:
        p.error('Embedding-Revision weicht vom gespeicherten Retrievallauf ab')
    konfig = try_to_load_from_cache('BAAI/bge-reranker-v2-m3', 'config.json')
    if not isinstance(konfig, str):
        p.error('Reranker-Snapshot fehlt im lokalen Cache')
    reranker = CrossEncoderReranker(str(Path(konfig).parent))
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    vektoren = json.loads((a.retrieval / 'fragenvektoren.json').read_text())['vektoren']
    index = Index(a.retrieval / 'seitenuebergreifend')
    fundstellen, _ = sv._matrix(index, revision)
    pfad, meta, kopf = pfade(a.quelle), einordnung(a.einordnung), koepfe(fundstellen)
    abschnitt = abschnitte(fundstellen)
    print(f'Chunks mit Abschnittspräfix: {sum(1 for v in abschnitt.values() if v)}/{len(abschnitt)}', flush=True)
    ergebnispfad = a.private / 'ergebnisse.json'
    je_arm = json.loads(ergebnispfad.read_text()) if ergebnispfad.exists() else {}
    je_arm = {arm: {int(k): v for k, v in r.items()} for arm, r in je_arm.items()}
    for arm in a.arme.split(','):
        texte = texte_je_arm(arm, fundstellen, pfad, meta, kopf, abschnitt)
        m = matrix(texte, provider, a.private / f'vektoren-{arm}', revision)
        je_arm[arm] = messe_arm(fragen, vektoren, index, fundstellen, texte, m, reranker)
        print(f'Arm {arm} gemessen', flush=True)
        ergebnispfad.write_text(json.dumps(je_arm), encoding='utf-8')
    bericht = auswerten(fragen, je_arm)
    (a.private / 'bericht.json').write_text(json.dumps(bericht, indent=1), encoding='utf-8')
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

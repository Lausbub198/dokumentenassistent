"""Bestand in einen neuen Arbeitsordner einlesen und über den Produktpfad prüfen (Phase D, Schritt 3).

    einlesen  erfassen → auslesen → einbetten, genau wie das Produkt (Aufbau wie mcp_server.main).
              Die Quelle wird nur gelesen; Index und Vektoren entstehen im --arbeitsordner.
              Wiederaufnehmbar: bereits eingebettete Blöcke bleiben erhalten.
    einbetten nur die fehlenden Vektoren für die Konfiguration berechnen (z. B. anderes Embedding auf einer
              Indexkopie), ohne neu auszulesen.
    pruefen   die Goldfragen über `Werkstatt.frage` stellen und mit Mehrfach-Gold bewerten. Zeigt, ob das
              Produkt erreicht, was die Messung (antwortstufe, Kontext-Cache) vorhersagt. Antworten bleiben
              privat im Arbeitsordner; die Ausgabe enthält nur Kennzahlen, dazu die Zahl der Modell-
              Ladevorgänge in Ollama während des Laufs (Umladen kostet Zeit).
    einordnen jede Datei mit dem Profil des Arbeitsordners einordnen; Status je Datei zählen (Einordnungsquote).
    promptlaenge  je Frage den größten möglichen Antwortprompt (Nachgriff, Top-n, mit Stufe-2-Zusatz) bauen und
              von Ollama zählen lassen. Zeigt vor einem Lauf mit kleinerem Kontextfenster, ob Prompts
              abgeschnitten würden (Ollama kürzt still).
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import time
from dokumentenassistent.pfade_privat import FRAGEN, LAEUFE

OLLAMA_LOG = Path.home() / '.ollama/logs/server.log'


def ladevorgaenge(seit: datetime, log: Path = OLLAMA_LOG) -> int | None:
    """Zahl der Modell-Ladevorgänge im Ollama-Serverprotokoll seit `seit` (None, wenn kein Protokoll)."""
    if not log.exists():
        return None
    n = 0
    for zeile in log.read_text(errors='replace').splitlines():
        if 'loading model' not in zeile:
            continue
        m = re.match(r'time=(\S+?)(?:[+-]\d\d:\d\d|Z)?\s', zeile)
        if m and datetime.fromisoformat(m.group(1)) >= seit:
            n += 1
    return n


def werkstatt(quelle: Path, ziel: Path, modelle: Path, arbeitsordner: Path):
    from dokumentenassistent.provider import (lade_modelle, lade_ocr_einstellungen, lade_provider_suche,
                                              lade_seitenuebergreifend, lade_sucheinstellungen)
    from dokumentenassistent.werkstatt import Werkstatt
    return Werkstatt(quelle=quelle, zielablage=ziel, provider=lade_modelle(modelle), arbeitsordner=arbeitsordner,
                     provider_suche=lade_provider_suche(modelle), sucheinstellungen=lade_sucheinstellungen(modelle),
                     ocr=lade_ocr_einstellungen(modelle), seitenuebergreifend=lade_seitenuebergreifend(modelle))


def einlesen(w) -> dict:
    start = time.monotonic()
    dateien = w.erfassen()
    w.auslesen(lambda n, gesamt, name: print(f'{n + 1}/{gesamt} Dateien', flush=True) if n % 10 == 0 else None)
    rev = (w.provider_suche or w.provider).embedding_revision()
    return {'dateien': len(dateien), 'fundstellen': sum(len(w.index.fundstellen(d.hash)) for d in w.index.dateien()),
            'durchsuchbar': len(w.index.durchsuchbare_fundstellen(modell_revision=rev,
                                                                    vorverarbeitung=w._vorverarbeitung())),
            'minuten': round((time.monotonic() - start) / 60, 1)}


def einbetten(w) -> dict:
    start = time.monotonic()
    w._bette_nach_ein()
    rev = (w.provider_suche or w.provider).embedding_revision()
    return {'durchsuchbar': len(w.index.durchsuchbare_fundstellen(modell_revision=rev,
                                                                    vorverarbeitung=w._vorverarbeitung())),
            'minuten': round((time.monotonic() - start) / 60, 1)}


def einordnen(w) -> dict:
    """Einordnen mit dem Profil im Arbeitsordner (`.dokumentenassistent/profil.yaml`), dann Status je Datei zählen.
    Wiederaufnehmbar: Dateien mit Vorschlag bleiben, wie sie sind (Werkstatt.einordnen)."""
    start = time.monotonic()
    w.einordnen(lambda n, gesamt, name: print(f'{n + 1}/{gesamt} Dateien', flush=True) if n % 10 == 0 else None)
    dateien = list(w.index.dateien())
    status: dict[str, int] = {}
    for d in dateien:  # Datei trägt keinen Status; der steht im Index (Fehler im Lauf 08.10.)
        s = w.index.status(d.hash) or 'ohne'
        status[s] = status.get(s, 0) + 1
    return {'dateien': len(dateien), 'status': status, 'minuten': round((time.monotonic() - start) / 60, 1)}


def promptlaenge(w, fragen: list[dict]) -> dict:
    """Größter Antwortprompt je Frage (Nachgriff Top-n + Stufe-2-Zusatz), von Ollama gezählt (num_ctx 65536)."""
    import dataclasses
    from dokumentenassistent.retrieval_reranker import rerank
    from dokumentenassistent.suche import _STUFE2_STRENG, _prompt, dense_rang
    provider, e = (w.provider_suche or w.provider), w.sucheinstellungen
    paare = w.index.durchsuchbare_fundstellen(modell_revision=provider.embedding_revision(),
                                              vorverarbeitung=w._vorverarbeitung())
    nach_id, praefixe = {f.id: f for f, _ in paare}, w._praefixe()
    fuer_reranker = {i: dataclasses.replace(f, text=praefixe.get(f.datei_hash, '') + f.text) for i, f in nach_id.items()}
    laengen = []
    for f, v in zip(fragen, provider.embed([f['frage'] for f in fragen])):
        rang = rerank(dense_rang(v, paare), fuer_reranker, f['frage'], e.reranker, e.rerank_k)
        top = tuple(nach_id[i] for i, _ in rang[:e.top_n])
        prompt = _prompt(top, f['frage']).replace('\n\nAbsätze:', _STUFE2_STRENG + '\n\nAbsätze:', 1)
        antwort = provider._post('/api/generate', {'model': provider.llm_modell, 'prompt': prompt, 'stream': False,
                                                  'think': provider.think,
                                                  'options': {'num_ctx': 65536, 'num_predict': 1, 'temperature': 0}})
        laengen.append(antwort.get('prompt_eval_count', 0))
    reserve = provider.max_antwort_tokens or 0
    return {'fragen': len(laengen), 'tokens_max': max(laengen), 'tokens_median': sorted(laengen)[len(laengen) // 2],
            **{f'ueber_{k}': sum(1 for n in laengen if n + reserve > k) for k in (8192, 16384, 32768)},
            'reserve_antwort': reserve}


def pruefen(w, fragen: list[dict], sichtung: Path, ausgabe: Path) -> dict:
    from dokumentenassistent import gold_mehrfach as gm
    beginn = datetime.now()
    mf = gm.Mehrfach(fragen, w.index, gm.lies_entscheidungen(sichtung))
    fertig = {json.loads(z)['nr'] for z in ausgabe.read_text().splitlines()} if ausgabe.exists() else set()
    for f in fragen:
        if f['nr'] in fertig:
            continue
        start = time.monotonic()
        antwort = w.frage(f['frage'])
        gefunden = f['status'] == 'gefunden'
        zeile = {'nr': f['nr'], 'status': f['status'], 'antwortstatus': antwort.status,
                 'mehrfach': gefunden and any(mf.akzeptiert(f['nr'], k.fundstelle) for k in antwort.karten),
                 'streng': gefunden and any(k.fundstelle.id in mf.gold[f['nr']] for k in antwort.karten),
                 'abgewiesen': not antwort.karten, 'sekunden': round(time.monotonic() - start, 1),
                 'karten': [k.fundstelle.id for k in antwort.karten],  # für spätere Neubewertung
                 'antwort': antwort.text}  # privat
        with ausgabe.open('a', encoding='utf-8') as out:
            out.write(json.dumps(zeile, ensure_ascii=False) + '\n')
    zeilen = [json.loads(z) for z in ausgabe.read_text().splitlines()]
    pos = [z for z in zeilen if z['status'] == 'gefunden']
    neg = [z for z in zeilen if z['status'] != 'gefunden']
    return {'fragen': len(zeilen), 'mehrfach': sum(z['mehrfach'] for z in pos), 'streng': sum(z['streng'] for z in pos),
            'positiv_abgewiesen': sum(z['abgewiesen'] for z in pos),
            'negativ_abgewiesen': sum(z['abgewiesen'] for z in neg),
            'sekunden_median': sorted(z['sekunden'] for z in zeilen)[len(zeilen) // 2] if zeilen else None,
            'modell_ladevorgaenge': ladevorgaenge(beginn)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('schritt', choices=('einlesen', 'einbetten', 'einordnen', 'pruefen', 'promptlaenge'))
    p.add_argument('--ausgabe', default='pruefung.jsonl', help='pruefen: Dateiname im Arbeitsordner')
    p.add_argument('--quelle', type=Path, required=True)
    p.add_argument('--arbeitsordner', type=Path, required=True)
    p.add_argument('--modelle', type=Path, required=True)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--sichtung', type=Path, default=LAEUFE / 'gold-mehrfach/sichtung.md')
    a = p.parse_args()
    if a.arbeitsordner.resolve() == a.quelle.resolve():
        p.error('--arbeitsordner darf nicht die Quelle sein (der bestehende Index bliebe nicht unangetastet)')
    a.arbeitsordner.mkdir(parents=True, exist_ok=True)
    w = werkstatt(a.quelle, a.arbeitsordner / 'zielablage', a.modelle, a.arbeitsordner)
    if a.schritt == 'einlesen':
        print(json.dumps(einlesen(w)))
        return
    if a.schritt == 'einbetten':
        print(json.dumps(einbetten(w)))
        return
    if a.schritt == 'einordnen':
        bericht = einordnen(w)
        (a.arbeitsordner / 'bericht-einordnen.json').write_text(json.dumps(bericht, indent=1))
        print(json.dumps(bericht))
        return
    fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
    if a.schritt == 'promptlaenge':
        bericht = promptlaenge(w, [f for f in fragen if f['status'] == 'gefunden'] + [f for f in fragen if f['status'] != 'gefunden'])
    else:
        bericht = pruefen(w, fragen, a.sichtung, a.arbeitsordner / a.ausgabe)
    (a.arbeitsordner / f'bericht-{a.schritt}-{Path(a.ausgabe).stem}.json').write_text(json.dumps(bericht, indent=1))
    print(json.dumps(bericht, indent=1))


if __name__ == '__main__':
    main()

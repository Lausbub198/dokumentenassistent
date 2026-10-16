"""AnythingLLM gegen denselben Goldstandard messen. CLI gibt nur IDs und Kennzahlen aus.

Alles läuft gegen die lokale AnythingLLM-Desktop-API (127.0.0.1:3001) und das lokale
Ollama. Private Texte landen ausschließlich im --private-Ordner (außerhalb von Git).

    konfigurieren  bisherige Einstellungen sichern, LLM/Embedder auf Ollama setzen, Telemetrie aus
    pruefen        Konfiguration prüfen (LLM/Embedder = Ollama, Modelle wie im Dokumentenassistenten)
    einlesen       Workspaces anlegen, registrierte Dateien hochladen und einbetten (wiederaufnehmbar)
    retrieval      nur vector-search Top 20 je Frage, ohne LLM (Minuten statt Stunden)
    messen         je Frage: vector-search Top 20 (ohne LLM) und Chat im query-Modus je Arm
    auswerten      aggregierte Kennzahlen je Arm als JSON (keine Texte), auch nach bericht.json
    zuruecksetzen  gesicherte Einstellungen wiederherstellen
    alles          konfigurieren → pruefen → einlesen → messen → auswerten (→ zuruecksetzen mit Flag)

API-Schlüssel: ANYTHINGLLM_API_KEY, sonst der neueste Schlüssel aus AnythingLLMs lokaler Datenbank
(read-only). Der Wert wird nie ausgegeben oder gespeichert. Ein Embedder-Wechsel macht bestehende
Workspaces von AnythingLLM ungültig; sie müssen danach in der App neu eingebettet werden.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import time

import httpx

from dokumentenassistent.antwort_eval import normalisiere_whitespace as ws
from dokumentenassistent.seitenvergleich import _ausserhalb_git, _dateischluessel, _registrierte_dateien
from dokumentenassistent.pfade_privat import BESTAND, FRAGEN, LAEUFE

BASIS = 'http://127.0.0.1:3001/api'
ABGEWIESEN = 'NICHT_GEFUNDEN'
SOLL = {'LLMProvider': 'ollama', 'OllamaLLMModelPref': 'gemma4:12b-it-q4_K_M',
        'EmbeddingEngine': 'ollama', 'EmbeddingModelPref': 'qwen3-embedding:0.6b'}
EINSTELLUNGEN = {**SOLL, 'OllamaLLMBasePath': 'http://127.0.0.1:11434', 'OllamaLLMTokenLimit': '32768',
                 'EmbeddingBasePath': 'http://127.0.0.1:11434', 'DisableTelemetry': 'true'}
DB = Path.home() / 'Library/Application Support/anythingllm-desktop/storage/anythingllm.db'
# Arm "standard": Produkt wie ausgeliefert (topN 4, Schwelle 0,25, kein Reranking).
# Arm "angeglichen": gleiche Kontextgröße wie der Dokumentenassistent (20) plus AnythingLLM-Reranking.
# Beide: Temperatur 0 und fester Ablehnungstext, damit Abweisungen zählbar sind.
ARME = {
    'standard': {'topN': 4, 'similarityThreshold': 0.25, 'vectorSearchMode': 'default'},
    'angeglichen': {'topN': 20, 'similarityThreshold': 0.25, 'vectorSearchMode': 'rerank'},
}
_META = re.compile(r'<document_metadata>.*?</document_metadata>\s*', re.S)


class Api:
    def __init__(self, schluessel: str, basis: str = BASIS, client: httpx.Client | None = None):
        self.client = client or httpx.Client(base_url=basis, timeout=900,
                                             headers={'Authorization': f'Bearer {schluessel}'})

    def get(self, pfad: str) -> dict:
        r = self.client.get(pfad)
        r.raise_for_status()
        return r.json()

    def post(self, pfad: str, **kw) -> dict:
        r = self.client.post(pfad, **kw)
        r.raise_for_status()
        return r.json()


def api_schluessel(db: Path = DB) -> str | None:
    if os.environ.get('ANYTHINGLLM_API_KEY'):
        return os.environ['ANYTHINGLLM_API_KEY']
    if not db.is_file():
        return None
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as v:
        zeile = v.execute('SELECT secret FROM api_keys ORDER BY createdAt DESC LIMIT 1').fetchone()
    return zeile[0] if zeile else None


def konfigurieren(api: Api, privat: Path) -> list[str]:
    """Sichert die bisherigen Werte (nur beim ersten Mal) und setzt die Messkonfiguration."""
    sicherung = privat / 'einstellungen-vorher.json'
    if not sicherung.exists():
        jetzt = api.get('/v1/system')['settings']
        sicherung.write_text(json.dumps({k: jetzt.get(k) for k in EINSTELLUNGEN}, indent=1), encoding='utf-8')
    antwort = api.post('/v1/system/update-env', json=EINSTELLUNGEN)
    if antwort.get('error'):
        raise RuntimeError(f'update-env: {antwort["error"]}')
    return sorted(EINSTELLUNGEN)


def zuruecksetzen(api: Api, privat: Path) -> list[str]:
    vorher = json.loads((privat / 'einstellungen-vorher.json').read_text(encoding='utf-8'))
    werte = {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in vorher.items() if v is not None}
    antwort = api.post('/v1/system/update-env', json=werte)
    if antwort.get('error'):
        raise RuntimeError(f'update-env: {antwort["error"]}')
    return sorted(werte)


def slug(arm: str) -> str:
    return f'lab-bestand-{arm}'


def pruefe_konfiguration(settings: dict) -> list[str]:
    return [f'{k}: {settings.get(k)!r} statt {v!r}' for k, v in SOLL.items() if settings.get(k) != v]


def chunk_text(text: str) -> str:
    return _META.sub('', text or '')


def passt_datei(titel: str, gold_datei: str) -> bool:
    name = Path(gold_datei or '').name
    return bool(name) and (titel == name or _dateischluessel(titel) == _dateischluessel(name))


def bewerte_treffer(frage: dict, treffer: list[dict]) -> dict:
    """treffer: [{'titel', 'text'}] in Rangfolge. Drei Maße, von locker nach streng."""
    wert = ws(frage.get('wortlaut_enthaelt') or '')
    absatz = ws(frage.get('zielabsatz') or '')
    def rang(pruef):
        return next((r for r, t in enumerate(treffer, 1) if pruef(t)), None)
    in_datei = lambda t: passt_datei(t['titel'], frage.get('datei'))
    return {
        'rang_datei': rang(in_datei),
        'rang_wortlaut': rang(lambda t: in_datei(t) and bool(wert) and wert in ws(chunk_text(t['text']))),
        'rang_zielabsatz': rang(lambda t: in_datei(t) and bool(absatz) and absatz in ws(chunk_text(t['text']))),
    }


def bewerte_antwort(frage: dict, antwort: str, quellen: list[dict]) -> dict:
    wert = ws(frage.get('wortlaut_enthaelt') or '')
    abgewiesen = not quellen or antwort.strip() == ABGEWIESEN
    return {'abgewiesen': abgewiesen,
            'antwort_enthaelt_wert': bool(wert) and not abgewiesen and wert in ws(antwort),
            **{f'kontext_{k}': v for k, v in bewerte_treffer(frage, quellen).items()}}


def _jsonl(pfad: Path) -> dict[tuple, dict]:
    if not pfad.exists():
        return {}
    zeilen = [json.loads(z) for z in pfad.read_text(encoding='utf-8').splitlines() if z.strip()]
    return {(z['arm'], z['nr']): z for z in zeilen}


def einlesen(api: Api, quelle: Path, privat: Path) -> dict:
    vorhanden = {w['slug'] for w in api.get('/v1/workspaces')['workspaces']}
    for arm, einst in ARME.items():
        if slug(arm) not in vorhanden:
            api.post('/v1/workspace/new', json={'name': slug(arm), 'chatMode': 'query'})
        api.post(f'/v1/workspace/{slug(arm)}/update',
                 json={**einst, 'openAiTemp': 0, 'queryRefusalResponse': ABGEWIESEN})
    zustand_pfad = privat / 'hochgeladen.json'
    zustand = json.loads(zustand_pfad.read_text()) if zustand_pfad.exists() else {}
    ziele = ','.join(slug(a) for a in ARME)
    fehler = []
    for datei in _registrierte_dateien(quelle):
        if datei.hash in zustand:
            continue
        try:
            with open(datei.pfad, 'rb') as f:
                antwort = api.post('/v1/document/upload', data={'addToWorkspaces': ziele},
                                   files={'file': (datei.name, f)})
        except httpx.HTTPStatusError as exc:  # eine nicht verarbeitbare Datei darf den Lauf nicht beenden
            print(f'Upload {datei.hash[:12]}: HTTP {exc.response.status_code}', flush=True)
            fehler.append(datei.hash)
            continue
        if not antwort.get('success'):
            fehler.append(datei.hash)
            continue
        zustand[datei.hash] = [d['location'] for d in antwort['documents']]
        zustand_pfad.write_text(json.dumps(zustand, indent=1), encoding='utf-8')
    return {'hochgeladen': len(zustand), 'fehler_hashes': fehler}


def retrieval(api: Api, fragen: list[dict], privat: Path) -> dict:
    """Nur vector-search (Top 20, ohne Schwelle, ohne LLM); schnell, direkt vergleichbar mit unserem Gate."""
    zeilen = []
    for frage in fragen:
        suche = api.post(f'/v1/workspace/{slug("standard")}/vector-search',
                         json={'query': frage['frage'], 'topN': 20, 'scoreThreshold': 0})
        zeilen.append({'nr': frage['nr'], 'status': frage['status'],
                       **bewerte_treffer(frage, _quellen(suche.get('results', [])))})
    (privat / 'retrieval.json').write_text(json.dumps(zeilen), encoding='utf-8')
    pos = [z for z in zeilen if z['status'] == 'gefunden']
    return {m: {f'top{k}': sum(1 for z in pos if z[m] and z[m] <= k) for k in (1, 4, 20)}
            for m in ('rang_datei', 'rang_wortlaut', 'rang_zielabsatz')}


def _quellen(liste: list[dict]) -> list[dict]:
    return [{'titel': q.get('title') or (q.get('metadata') or {}).get('title') or '',
             'text': q.get('text') or q.get('chunk') or ''} for q in liste]


def messen(api: Api, fragen: list[dict], privat: Path) -> int:
    ausgabe = privat / 'ergebnisse.jsonl'
    fertig = _jsonl(ausgabe)
    neu = 0
    for frage in fragen:
        for arm in ARME:
            if (arm, frage['nr']) in fertig:
                continue
            zeile = {'arm': arm, 'nr': frage['nr'], 'status': frage['status']}
            start = time.monotonic()
            if arm == 'standard':  # Retrieval ohne LLM nur einmal; hängt nicht vom Arm ab
                suche = api.post(f'/v1/workspace/{slug(arm)}/vector-search',
                                 json={'query': frage['frage'], 'topN': 20, 'scoreThreshold': 0})
                treffer = _quellen(suche.get('results', []))
                zeile['retrieval'] = bewerte_treffer(frage, treffer)
                zeile['max_score'] = max((r.get('score', 0) for r in suche.get('results', [])), default=None)
            chat = api.post(f'/v1/workspace/{slug(arm)}/chat',
                            json={'message': frage['frage'], 'mode': 'query',
                                  'sessionId': f'lab-{arm}-{frage["nr"]}', 'reset': True})
            if chat.get('error') not in (None, 'null'):
                zeile['fehler'] = str(chat['error'])
            quellen = _quellen(chat.get('sources') or [])
            zeile.update(bewerte_antwort(frage, chat.get('textResponse') or '', quellen))
            zeile['antwort'] = chat.get('textResponse')  # privat, bleibt im --private-Ordner
            zeile['sekunden'] = round(time.monotonic() - start, 1)
            with ausgabe.open('a', encoding='utf-8') as f:
                f.write(json.dumps(zeile, ensure_ascii=False) + '\n')
            neu += 1
    return neu


def auswerten(zeilen: list[dict]) -> dict:
    bericht = {}
    for arm in ARME:
        eigene = [z for z in zeilen if z['arm'] == arm]
        pos = [z for z in eigene if z['status'] == 'gefunden']
        neg = [z for z in eigene if z['status'] != 'gefunden']
        zaehle = lambda rows, key, k=None: sum(1 for z in rows if z.get(key) and (k is None or z[key] <= k))
        bericht[arm] = {
            'fragen': len(eigene), 'positiv': len(pos), 'negativ': len(neg),
            'technische_fehler': sum(1 for z in eigene if 'fehler' in z),
            'kontext_wortlaut': zaehle(pos, 'kontext_rang_wortlaut'),
            'kontext_zielabsatz': zaehle(pos, 'kontext_rang_zielabsatz'),
            'antwort_enthaelt_wert': sum(1 for z in pos if z['antwort_enthaelt_wert']),
            'positiv_abgewiesen': sum(1 for z in pos if z['abgewiesen']),
            'negativ_korrekt_abgewiesen': sum(1 for z in neg if z['abgewiesen']),
            'median_sekunden': sorted(z['sekunden'] for z in eigene)[len(eigene) // 2] if eigene else None,
        }
    ret = [z['retrieval'] for z in zeilen if z['arm'] == 'standard' and z['status'] == 'gefunden']
    bericht['retrieval_ohne_llm_top20'] = {
        m: {f'top{k}': sum(1 for r in ret if r[m] and r[m] <= k) for k in (1, 4, 20)}
        for m in ('rang_datei', 'rang_wortlaut', 'rang_zielabsatz')}
    return bericht


def _schreibe_bericht(privat: Path) -> dict:
    bericht = auswerten(list(_jsonl(privat / 'ergebnisse.jsonl').values()))
    (privat / 'bericht.json').write_text(json.dumps(bericht, indent=1), encoding='utf-8')
    return bericht


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('schritt', choices=('konfigurieren', 'pruefen', 'einlesen', 'retrieval', 'messen',
                                       'auswerten', 'zuruecksetzen', 'alles'))
    p.add_argument('--quelle', type=Path, default=BESTAND)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--private', type=Path, default=LAEUFE / 'anythingllm')
    p.add_argument('--zuruecksetzen', action='store_true', help='bei "alles": danach Einstellungen wiederherstellen')
    a = p.parse_args()
    _ausserhalb_git(a.private.resolve())
    a.private.mkdir(parents=True, exist_ok=True)
    if a.schritt == 'auswerten':
        print(json.dumps(_schreibe_bericht(a.private), ensure_ascii=False, indent=1))
        return
    schluessel = api_schluessel()
    if not schluessel:
        p.error('Kein API-Schlüssel (ANYTHINGLLM_API_KEY oder AnythingLLM → Einstellungen → Developer API)')
    api = Api(schluessel)
    if not api.get('/v1/auth').get('authenticated'):
        p.error('API-Schlüssel ungültig')
    schritte = (['konfigurieren', 'pruefen', 'einlesen', 'messen', 'auswerten']
                + (['zuruecksetzen'] if a.zuruecksetzen else [])) if a.schritt == 'alles' else [a.schritt]
    for schritt in schritte:
        print(f'== {schritt}', flush=True)
        if schritt == 'konfigurieren':
            print(json.dumps({'gesetzt': konfigurieren(api, a.private)}))
        elif schritt == 'zuruecksetzen':
            print(json.dumps({'wiederhergestellt': zuruecksetzen(api, a.private)}))
        elif schritt == 'auswerten':
            print(json.dumps(_schreibe_bericht(a.private), ensure_ascii=False, indent=1))
        else:
            abweichungen = pruefe_konfiguration(api.get('/v1/system')['settings'])
            if abweichungen:
                p.error('Konfiguration weicht ab:\n  ' + '\n  '.join(abweichungen))
            if schritt == 'pruefen':
                print('Konfiguration ok')
            elif schritt == 'einlesen':
                print(json.dumps(einlesen(api, a.quelle, a.private)))
            elif schritt == 'retrieval':
                fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
                print(json.dumps(retrieval(api, fragen, a.private), indent=1), flush=True)
            else:
                fragen = json.loads(a.gold.read_text(encoding='utf-8'))['fragen']
                print(json.dumps({'neu_gemessen': messen(api, fragen, a.private)}), flush=True)


if __name__ == '__main__':
    main()

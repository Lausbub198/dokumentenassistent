"""Lokaler A/B-Vergleich: erst Struktur, dann optional Retrieval ohne Antwort-LLM."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

import numpy as np

from dokumentenassistent.auslesen import NichtLesbar, OcrEinstellungen, OcrNichtVerfuegbar, lies_seiten
from dokumentenassistent.fundstellen import zerlege
from dokumentenassistent.index import Index
from dokumentenassistent.typen import Datei
from dokumentenassistent.index import validiere_vektoren


def _sha256(pfad: Path) -> str:
    digest = hashlib.sha256()
    with pfad.open('rb') as datei:
        for block in iter(lambda: datei.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _atomar_json(pfad: Path, daten: dict) -> None:
    tmp = pfad.with_suffix(pfad.suffix + '.tmp')
    tmp.write_text(json.dumps(daten, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')
    tmp.replace(pfad)


def _ausserhalb_git(pfad: Path) -> None:
    for elternteil in (pfad, *pfad.parents):
        if (elternteil / '.git').exists():
            raise ValueError('Private Vergleichsdaten dürfen nicht in einem Git-Baum liegen')


def _registrierte_dateien(quelle: Path) -> tuple[Datei, ...]:
    index_pfad = quelle / '.dokumentenassistent' / 'index.sqlite'
    if not index_pfad.is_file():
        raise FileNotFoundError('Quellindex fehlt')
    with sqlite3.connect(f'file:{index_pfad}?mode=ro', uri=True) as db:
        rows = db.execute('SELECT hash,pfad,name,groesse FROM dateien ORDER BY hash').fetchall()
    dateien = tuple(Datei(row[0], Path(row[1]), row[2], row[3]) for row in rows)
    for datei in dateien:
        if not datei.pfad.resolve().is_relative_to(quelle.resolve()) or not datei.pfad.is_file():
            raise ValueError('Registrierte Quelldatei fehlt oder liegt außerhalb der Quelle')
    return dateien


def _manifest(quelle: Path, gold: Path, dateien: tuple[Datei, ...],
              ocr: OcrEinstellungen) -> dict:
    modulpfad = Path(__file__).parent
    return {
        'quelle_index_sha256': _sha256(quelle / '.dokumentenassistent' / 'index.sqlite'),
        'gold_sha256': _sha256(gold),
        'code_sha256': {name: _sha256(modulpfad / name)
                        for name in ('fundstellen.py', 'auslesen.py', 'index.py', 'typen.py',
                                     'seitenvergleich.py')},
        'extraktion': dataclasses.asdict(ocr),
        'chunking': {'min_woerter': 120, 'max_woerter': 380, 'ueberlapp': 30},
        # Nur in der privaten Manifestdatei, nie im Bericht oder Git.
        'dateien': {datei.hash: {'pfad': str(datei.pfad), 'sha256': _sha256(datei.pfad)}
                    for datei in dateien},
    }


def _normalisiere_leerraum(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def _ergebnis_fingerprint(index: Index, datei_hash: str) -> str:
    fundstellen = index.fundstellen(datei_hash)
    daten = [(f.id, f.text, [(s.seite, s.start, s.ende) for s in f.spannen])
             for f in fundstellen]
    return hashlib.sha256(json.dumps(daten, ensure_ascii=False).encode()).hexdigest()


def _dateischluessel(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).casefold())


def _frage_treffer(frage: dict, index: Index, namens_index: dict[str, list[Datei]]) -> tuple[bool, bool] | None:
    name = Path(frage.get('datei') or '').name
    dateien = namens_index.get(name, [])
    if not dateien:
        dateien = [datei for gruppe in namens_index.values() for datei in gruppe
                   if _dateischluessel(datei.name) == _dateischluessel(name)]
    if len(dateien) != 1:
        return None
    wortlaut = frage.get('wortlaut_enthaelt')
    if not isinstance(wortlaut, str) or not wortlaut.strip():
        return None
    texte = [f.text for f in index.fundstellen(dateien[0].hash)]
    return (any(wortlaut in text for text in texte),
            any(_normalisiere_leerraum(wortlaut) in _normalisiere_leerraum(text)
                for text in texte))


def _bericht(gold: Path, dateien: tuple[Datei, ...], baseline: Index,
             neu: Index, fehlgeschlagen: list[str], manifest: dict) -> dict:
    fragen = json.loads(gold.read_text(encoding='utf-8'))['fragen']
    namens_index: dict[str, list[Datei]] = {}
    for datei in dateien:
        namens_index.setdefault(datei.name, []).append(datei)
    paare = {'baseline': baseline, 'seitenuebergreifend': neu}
    exakt = {arm: 0 for arm in paare}
    leerraum = {arm: 0 for arm in paare}
    veraendert: list[int] = []
    unbekannt: list[int] = []
    positiv = [f for f in fragen if f['status'] == 'gefunden']
    negativ = [f for f in fragen if f['status'] == 'nicht_gefunden']
    for frage in positiv:
        treffer = {arm: _frage_treffer(frage, index, namens_index)
                   for arm, index in paare.items()}
        if any(wert is None for wert in treffer.values()):
            unbekannt.append(frage['nr'])
            continue
        for arm, wert in treffer.items():
            exakt[arm] += int(wert[0])
            leerraum[arm] += int(wert[1])
        if treffer['baseline'] != treffer['seitenuebergreifend']:
            veraendert.append(frage['nr'])
    return {
        'art': 'strukturvergleich_ohne_embeddings',
        'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        'dokumente': {'gesamt': len(dateien), 'verarbeitet': len(dateien) - len(fehlgeschlagen),
                      'nicht_lesbar': len(fehlgeschlagen)},
        'chunks': {arm: sum(len(index.fundstellen(d.hash)) for d in dateien)
                   for arm, index in paare.items()},
        'mehrseiten_chunks': sum(len(f.seiten) > 1 for d in dateien
                                 for f in neu.fundstellen(d.hash)),
        'fragen': {'gesamt': len(fragen), 'positiv': len(positiv), 'negativ': len(negativ),
                   'nicht_zuordenbar': unbekannt},
        'wortlaut_exakt': exakt,
        'wortlaut_leerraum_normalisiert': leerraum,
        'veraenderte_fragen': veraendert,
        'vektoren': {'baseline': 0, 'seitenuebergreifend': 0},
        'retrieval_oder_antwortqualitaet_gemessen': False,
    }


def strukturvergleich(quelle: Path, gold: Path, privat: Path, *,
                      resume: bool = False,
                      ocr: OcrEinstellungen | None = None) -> dict:
    quelle, gold, privat = Path(quelle).resolve(), Path(gold).resolve(), Path(privat).resolve()
    _ausserhalb_git(privat)
    if privat.exists() and not resume:
        raise FileExistsError('Vergleichsverzeichnis existiert bereits')
    if resume and not privat.is_dir():
        raise FileNotFoundError('Kein Vergleichslauf zum Fortsetzen')
    dateien = _registrierte_dateien(quelle)
    einstellungen = ocr or OcrEinstellungen(pdf_extraktion='pdftotext_layout')
    manifest = _manifest(quelle, gold, dateien, einstellungen)
    if resume:
        vorhanden = json.loads((privat / 'manifest.json').read_text(encoding='utf-8'))
        if vorhanden != manifest:
            raise ValueError('Manifest stimmt nicht mehr mit Quelle, Gold, Code oder Konfiguration überein')
    else:
        privat.mkdir(parents=True)
        _atomar_json(privat / 'manifest.json', manifest)
    zustandspfad = privat / 'fortschritt.json'
    zustand = json.loads(zustandspfad.read_text()) if resume and zustandspfad.exists() else {
        'verarbeitet': [], 'nicht_lesbar': [], 'resultate': {}}
    if resume and any(not (privat / arm / '.dokumentenassistent' / 'index.sqlite').is_file()
                      for arm in ('baseline', 'seitenuebergreifend')):
        raise ValueError('Ergebnis-Index fehlt; Fortsetzung verweigert')
    baseline = Index(privat / 'baseline')
    neu = Index(privat / 'seitenuebergreifend')
    if resume:
        for datei_hash in zustand['verarbeitet']:
            erwartete = zustand.get('resultate', {}).get(datei_hash)
            if not erwartete:
                raise ValueError('Ergebnis-Checkpoint fehlt; Fortsetzung verweigert')
            for arm, index in (('baseline', baseline), ('seitenuebergreifend', neu)):
                if (index.datei(datei_hash) is None
                        or _ergebnis_fingerprint(index, datei_hash) != erwartete.get(arm)):
                    raise ValueError('Ergebnis-Index weicht vom Checkpoint ab')
    abgeschlossen = set(zustand['verarbeitet']) | set(zustand['nicht_lesbar'])
    for datei in dateien:
        if datei.hash in abgeschlossen:
            continue
        try:
            seiten = lies_seiten(datei.pfad, einstellungen)
        except (NichtLesbar, OcrNichtVerfuegbar):
            zustand['nicht_lesbar'].append(datei.hash)
            _atomar_json(zustandspfad, zustand)
            continue
        for index, modus in ((baseline, False), (neu, True)):
            index.registriere(datei, 'unklar')
            index.ersetze_fundstellen(datei.hash, zerlege(datei, seiten,
                                                         seitenuebergreifend=modus))
        zustand['resultate'][datei.hash] = {
            'baseline': _ergebnis_fingerprint(baseline, datei.hash),
            'seitenuebergreifend': _ergebnis_fingerprint(neu, datei.hash),
        }
        zustand['verarbeitet'].append(datei.hash)
        _atomar_json(zustandspfad, zustand)
    bericht = _bericht(gold, dateien, baseline, neu, zustand['nicht_lesbar'], manifest)
    _atomar_json(privat / 'bericht.json', bericht)
    return bericht


_ARME = ('baseline', 'seitenuebergreifend')
_SCHWELLE = 0.49


def _pruefe_struktur(struktur: Path, gold: Path) -> dict:
    manifest = json.loads((struktur / 'manifest.json').read_text(encoding='utf-8'))
    fortschritt = json.loads((struktur / 'fortschritt.json').read_text(encoding='utf-8'))
    # Ein bereinigtes Gold (gold_bereinigung.py) ist zulässig, wenn es aus dem gepinnten Gold abgeleitet ist.
    basis = json.loads(gold.read_text(encoding='utf-8')).get('bereinigung', {}).get('basis_sha256')
    if manifest['gold_sha256'] not in (_sha256(gold), basis):
        raise ValueError('Struktur-Manifest: Gold-Hash weicht ab')
    modulpfad = Path(__file__).parent
    for name, digest in manifest['code_sha256'].items():
        # Der Messrunner selbst wird für Phase 2 erweitert; Extraktion/Chunking/Index bleiben gepinnt.
        if name != 'seitenvergleich.py' and _sha256(modulpfad / name) != digest:
            raise ValueError('Struktur-Code-Hash weicht ab')
    for arm in _ARME:
        db = struktur / arm / '.dokumentenassistent' / 'index.sqlite'
        if not db.is_file():
            raise ValueError('Struktur-Ergebnisindex fehlt')
        index = Index(struktur / arm)
        for datei_hash in fortschritt['verarbeitet']:
            if (_ergebnis_fingerprint(index, datei_hash)
                    != fortschritt['resultate'][datei_hash][arm]):
                raise ValueError('Struktur-Hash des Ergebnisindex weicht ab')
        if index.durchsuchbare_fundstellen():
            raise ValueError('Strukturkopie enthält bereits Embeddings')
    if len(fortschritt['verarbeitet']) + len(fortschritt['nicht_lesbar']) != len(manifest['dateien']):
        raise ValueError('Strukturvergleich ist nicht vollständig')
    return manifest


def _pruefe_retrieval_kopien(privat: Path, struktur: Path) -> None:
    fortschritt = json.loads((struktur / 'fortschritt.json').read_text(encoding='utf-8'))
    for arm in _ARME:
        db = privat / arm / '.dokumentenassistent' / 'index.sqlite'
        if not db.is_file():
            raise ValueError('Retrieval-Ergebnisindex fehlt')
        index = Index(privat / arm)
        for datei_hash in fortschritt['verarbeitet']:
            if (_ergebnis_fingerprint(index, datei_hash)
                    != fortschritt['resultate'][datei_hash][arm]):
                raise ValueError('Retrieval-Struktur-Hash weicht ab')


def _ziel_ids(frage: dict, index: Index) -> set[str]:
    passend = _ziel_dateien(frage, index)
    zielabsatz = frage.get('zielabsatz') or ''
    if not zielabsatz.strip():
        return set()
    norm = _normalisiere_leerraum(zielabsatz)
    return {f.id for d in passend for f in index.fundstellen(d.hash)
            if norm in _normalisiere_leerraum(f.text)}


def _ziel_dateien(frage: dict, index: Index) -> list[Datei]:
    name = Path(frage.get('datei') or '').name
    dateien = list(index.dateien())
    passend = [d for d in dateien if d.name == name]
    if not passend:
        passend = [d for d in dateien if _dateischluessel(d.name) == _dateischluessel(name)]
    return passend


def _matrix(index: Index, revision: str) -> tuple[list, np.ndarray]:
    paare = index.durchsuchbare_fundstellen(modell_revision=revision)
    fundstellen = [f for f, _ in paare]
    if len({f.id for f in fundstellen}) != len(fundstellen):
        raise ValueError('Doppelte Fundstellen-ID')
    vektoren = [v for _, v in paare]
    validiere_vektoren(vektoren, len(vektoren))
    matrix = np.asarray(vektoren, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError('Embedding-Matrix ist leer oder inkonsistent')
    normen = np.linalg.norm(matrix, axis=1)
    if np.any(normen == 0):
        raise ValueError('Nullvektor im Index')
    return fundstellen, matrix / normen[:, None]


def _messe_frage(frage: dict, vektor: list[float], index: Index, fundstellen: list,
                 matrix: np.ndarray, reranker) -> dict:
    start = time.monotonic()
    query = np.asarray(vektor, dtype=np.float32)
    if query.shape != (matrix.shape[1],) or not np.isfinite(query).all() or np.linalg.norm(query) == 0:
        raise ValueError('Fragevektor passt nicht zur Index-Dimension')
    scores = matrix @ (query / np.linalg.norm(query))
    order = sorted(range(len(fundstellen)), key=lambda i: (-float(scores[i]), fundstellen[i].id))
    ziel = _ziel_ids(frage, index) if frage['status'] == 'gefunden' else set()
    rang = next((r for r, i in enumerate(order, 1) if fundstellen[i].id in ziel), None)
    # Produktpfad: Die Schwelle entscheidet nur über die ganze Frage anhand Rang 1.
    # Danach gehen die vollständigen Top 20 in den Reranker, auch unter 0,49.
    schwelle_blockiert = scores[order[0]] < _SCHWELLE
    kandidaten = [] if schwelle_blockiert else order[:20]
    if kandidaten:
        neu_scores = reranker.bewerte(frage['frage'], [fundstellen[i].text for i in kandidaten])
        if len(neu_scores) != len(kandidaten) or not np.isfinite(neu_scores).all():
            raise ValueError('Reranker-Scores ungültig')
        kandidaten = [i for _, i in sorted(zip(neu_scores, kandidaten), key=lambda p: -p[0])]
    return {
        'nr': frage['nr'], 'zielchunk_rang_dense': rang,
        'zielabsatz_im_index': bool(ziel),
        'schwelle_blockiert': bool(schwelle_blockiert),
        'zielchunk_rang_reranked': next((r for r, i in enumerate(kandidaten, 1)
                                        if fundstellen[i].id in ziel), None),
        'kontexttreffer': any(fundstellen[i].id in ziel for i in kandidaten),
        'kontext_chunks': len(kandidaten),
        'kontext_zeichen': sum(len(fundstellen[i].text) for i in kandidaten),
        'max_score': float(scores[order[0]]),
        'latenz_ms': round((time.monotonic() - start) * 1000),
    }


def retrievalvergleich(struktur: Path, gold: Path, privat: Path, provider, reranker, *,
                       erwartet: tuple[int, int] = (85, 15), resume: bool = False,
                       recompute: bool = False) -> dict:
    """Gepaarter, lokaler Retrieval-Gate-Test; erzeugt keine Antwort mit einem LLM."""
    struktur, gold, privat = Path(struktur).resolve(), Path(gold).resolve(), Path(privat).resolve()
    _ausserhalb_git(privat)
    struktur_manifest = _pruefe_struktur(struktur, gold)
    fragen = json.loads(gold.read_text(encoding='utf-8'))['fragen']
    positiv = sum(f['status'] == 'gefunden' for f in fragen)
    negativ = sum(f['status'] == 'nicht_gefunden' for f in fragen)
    if (positiv, negativ) != erwartet or len({f['nr'] for f in fragen}) != len(fragen):
        raise ValueError('Gold-Fragenanzahl oder IDs weichen ab')
    revision = provider.embedding_revision()
    reranker_revision = getattr(reranker, 'revision', None)
    if not revision or not getattr(reranker, 'modell_name', None) or not reranker_revision:
        raise ValueError('Modellrevision oder Reranker-Modell fehlt')
    manifest = {
        'struktur_manifest_sha256': _sha256(struktur / 'manifest.json'),
        'struktur_indices_sha256': {arm: _sha256(struktur / arm / '.dokumentenassistent' / 'index.sqlite')
                                   for arm in _ARME},
        'gold_sha256': _sha256(gold), 'embedding_revision': revision,
        'reranker': reranker.modell_name, 'reranker_revision': reranker_revision,
        'auswertung_code_sha256': _sha256(Path(__file__)), 'schwelle': _SCHWELLE,
        'rerank_k': 20, 'top_n': 20, 'erwartet': list(erwartet),
        'chunking': struktur_manifest['chunking'],
    }
    if resume:
        if not privat.is_dir():
            raise ValueError('Retrieval-Manifest fehlt')
        vorhanden = json.loads((privat / 'manifest.json').read_text())
        if vorhanden != manifest:
            neu_bewerten = {'auswertung_code_sha256', 'reranker_revision'}
            unveraendert = {k: v for k, v in vorhanden.items() if k not in neu_bewerten}
            soll = {k: v for k, v in manifest.items() if k not in neu_bewerten}
            if not recompute or unveraendert != soll:
                raise ValueError('Retrieval-Manifest oder Modellrevision weicht ab')
        if recompute:
            for name in ('ergebnisse.json', 'bericht.json'):
                pfad = privat / name
                if pfad.exists():
                    suffix = _sha256(pfad)[:12]
                    archiv = privat / f'{pfad.stem}.alt-{suffix}.json'
                    if archiv.exists():
                        raise FileExistsError('Auswertungsarchiv existiert bereits')
                    pfad.rename(archiv)
            _atomar_json(privat / 'manifest.json', manifest)
    else:
        if privat.exists():
            raise FileExistsError('Retrieval-Verzeichnis existiert bereits')
        privat.mkdir(parents=True)
        _atomar_json(privat / 'manifest.json', manifest)
        for arm in _ARME:
            quelle = struktur / arm / '.dokumentenassistent' / 'index.sqlite'
            ziel = privat / arm / '.dokumentenassistent' / 'index.sqlite'
            ziel.parent.mkdir(parents=True)
            with sqlite3.connect(f'file:{quelle}?mode=ro', uri=True) as von, sqlite3.connect(ziel) as nach:
                von.backup(nach)
    _pruefe_retrieval_kopien(privat, struktur)
    # Der identische Fragenvektor wird einmal je Frage erzeugt und in beiden Armen benutzt.
    vektorpfad = privat / 'fragenvektoren.json'
    if vektorpfad.exists():
        vektoren = json.loads(vektorpfad.read_text())['vektoren']
    else:
        vektoren = provider.embed([f['frage'] for f in fragen])
        validiere_vektoren(vektoren, len(fragen))
        if provider.embedding_revision() != revision:
            raise ValueError('Embedding-Revision wechselte während der Fragen')
        _atomar_json(vektorpfad, {'vektoren': vektoren})
    validiere_vektoren(vektoren, len(fragen))
    indices = {arm: Index(privat / arm) for arm in _ARME}
    for arm, index in indices.items():
        fehlend = index.fundstellen_ohne_embedding(modell_revision=revision)
        gruppen: dict[str, list] = {}
        for f in fehlend:
            gruppen.setdefault(f.datei_hash, []).append(f)
        for nummer, gruppe in enumerate(gruppen.values(), 1):
            for anfang in range(0, len(gruppe), 16):
                batch = gruppe[anfang:anfang + 16]
                vector_batch = provider.embed([f.text for f in batch])
                if provider.embedding_revision() != revision:
                    raise ValueError('Embedding-Revision wechselte während der Chunks')
                index.speichere_embeddings(tuple((f.id, v) for f, v in zip(batch, vector_batch)),
                                          modell_revision=revision,
                                          erwartete_texte={f.id: f.text for f in batch})
            print(f'{arm}: {nummer}/{len(gruppen)} Dokumente eingebettet', flush=True)
    matrizen = {arm: _matrix(index, revision) for arm, index in indices.items()}
    struktur_bericht = json.loads((struktur / 'bericht.json').read_text(encoding='utf-8'))
    for arm, (fundstellen, _) in matrizen.items():
        if len(fundstellen) != struktur_bericht['chunks'][arm]:
            raise ValueError(f'{arm}: Fundstellenzahl weicht ab')
    ergebnispfad = privat / 'ergebnisse.json'
    resultate = json.loads(ergebnispfad.read_text())['resultate'] if ergebnispfad.exists() else {}
    for n, (frage, vektor) in enumerate(zip(fragen, vektoren)):
        key = str(frage['nr'])
        if key in resultate:
            continue
        reihenfolge = _ARME if n % 2 == 0 else tuple(reversed(_ARME))
        messung = {}
        for arm in reihenfolge:
            fundstellen, matrix = matrizen[arm]
            messung[arm] = _messe_frage(frage, vektor, indices[arm], fundstellen, matrix, reranker)
        resultate[key] = messung
        _atomar_json(ergebnispfad, {'resultate': resultate})
        if (n + 1) % 10 == 0:
            print(f'Fragen: {n + 1}/{len(fragen)}', flush=True)
    if len(resultate) != len(fragen):
        raise ValueError('Nicht alle Fragen wurden gemessen')
    positive_ids = {str(f['nr']) for f in fragen if f['status'] == 'gefunden'}
    negative_ids = {str(f['nr']) for f in fragen if f['status'] == 'nicht_gefunden'}
    mehrdeutig = {str(f['nr']) for f in fragen if f['status'] == 'gefunden'
                  and len(_ziel_dateien(f, indices['baseline'])) != 1}
    eindeutig = positive_ids - mehrdeutig
    treffer = {arm: sum(resultate[k][arm]['kontexttreffer'] for k in positive_ids) for arm in _ARME}
    blockiert = {arm: sum(resultate[k][arm]['kontext_chunks'] == 0 for k in negative_ids) for arm in _ARME}
    bericht = {
        'art': 'retrievalvergleich_ohne_antwort_llm', 'fragen': {'positiv': positiv, 'negativ': negativ},
        'chunks': {arm: len(matrizen[arm][0]) for arm in _ARME},
        'kontexttreffer': treffer, 'negative_blockiert': blockiert,
        'zielabsatz_auswertbar': {arm: sum(resultate[k][arm]['zielabsatz_im_index']
                                          for k in positive_ids) for arm in _ARME},
        'zielabsatz_nicht_im_index': {arm: sorted(int(k) for k in positive_ids
                                            if not resultate[k][arm]['zielabsatz_im_index'])
                                     for arm in _ARME},
        'schwelle_blockiert': {arm: sorted(int(k) for k in positive_ids
                                      if resultate[k][arm]['zielabsatz_im_index']
                                      and resultate[k][arm]['schwelle_blockiert'])
                               for arm in _ARME},
        'ranking_verluste': {arm: sorted(int(k) for k in positive_ids
                                     if resultate[k][arm]['zielabsatz_im_index']
                                     and not resultate[k][arm]['schwelle_blockiert']
                                     and not resultate[k][arm]['kontexttreffer'])
                              for arm in _ARME},
        'mehrdeutige_zieldatei': sorted(int(k) for k in mehrdeutig),
        'kontexttreffer_eindeutig': {arm: sum(resultate[k][arm]['kontexttreffer']
                                             for k in eindeutig) for arm in _ARME},
        'dense_zielrang_1': {arm: sum(resultate[k][arm]['zielchunk_rang_dense'] == 1
                                       for k in positive_ids) for arm in _ARME},
        'dense_zielrang_20': {arm: sum(resultate[k][arm]['zielchunk_rang_dense'] is not None
                                        and resultate[k][arm]['zielchunk_rang_dense'] <= 20
                                        for k in positive_ids) for arm in _ARME},
        'reranked_zielrang_1': {arm: sum(resultate[k][arm]['zielchunk_rang_reranked'] == 1
                                          for k in positive_ids) for arm in _ARME},
        'gewinne': sorted(int(k) for k in positive_ids if not resultate[k]['baseline']['kontexttreffer']
                          and resultate[k]['seitenuebergreifend']['kontexttreffer']),
        'verluste': sorted(int(k) for k in positive_ids if resultate[k]['baseline']['kontexttreffer']
                           and not resultate[k]['seitenuebergreifend']['kontexttreffer']),
        'kontext_zeichen_mittel': {arm: round(sum(resultate[k][arm]['kontext_zeichen'] for k in resultate)
                                          / len(resultate)) for arm in _ARME},
        'latenz_ms_mittel': {arm: round(sum(resultate[k][arm]['latenz_ms'] for k in resultate)
                                    / len(resultate)) for arm in _ARME},
        'antwortqualitaet_gemessen': False,
    }
    _atomar_json(privat / 'bericht.json', bericht)
    return bericht


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modus', nargs='?', choices=('retrieval',))
    parser.add_argument('--quelle', type=Path)
    parser.add_argument('--struktur', type=Path)
    parser.add_argument('--gold', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--recompute', action='store_true',
                        help='Nur Auswertung erneut ausführen; vorhandene Vektoren behalten')
    args = parser.parse_args()
    if args.modus == 'retrieval':
        if args.struktur is None:
            parser.error('--struktur ist für retrieval erforderlich')
        import os
        from dokumentenassistent.provider import OllamaProvider
        from dokumentenassistent.retrieval_reranker import CrossEncoderReranker
        from huggingface_hub import try_to_load_from_cache

        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        provider = OllamaProvider('http://localhost:11434', 'qwen3-embedding:0.6b', '')
        modell_name = 'BAAI/bge-reranker-v2-m3'
        konfig = try_to_load_from_cache(modell_name, 'config.json')
        if not isinstance(konfig, str) or not Path(konfig).is_file():
            parser.error('Reranker-Snapshot fehlt im lokalen Cache')
        snapshot = Path(konfig).parent
        reranker = CrossEncoderReranker(str(snapshot))
        reranker.modell_name = modell_name
        reranker.revision = snapshot.name
        bericht = retrievalvergleich(args.struktur, args.gold, args.private, provider,
                                      reranker, resume=args.resume,
                                      recompute=args.recompute)
    else:
        if args.quelle is None:
            parser.error('--quelle ist für den Strukturvergleich erforderlich')
        bericht = strukturvergleich(args.quelle, args.gold, args.private, resume=args.resume)
    print(json.dumps(bericht, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()

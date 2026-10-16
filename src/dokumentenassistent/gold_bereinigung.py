"""Gold-Zielabsätze gegen den tatsächlich ausgelesenen Text abgleichen. CLI gibt nur IDs/Kennzahlen aus.

Hintergrund: Der Goldstandard wurde aus den Dokumenten erzeugt, nicht aus unserem Index. Wo der
Zielabsatz nicht wortgetreu (nach Whitespace-Normalisierung) in einem Chunk der Zieldatei steht,
kann die Retrieval-Messung ihn nie finden – egal wie gut die Suche ist.

Je betroffener Frage wird die ähnlichste Textspanne im ausgelesenen Dokument gesucht:

    gold_schreibweise  nur Case/Anführungszeichen/Striche weichen ab – der Goldtext war ungenau
    auslesefehler      unser Index weicht inhaltlich ab (OCR, Layout, fehlende Wörter) – Gold war
                       richtig; der Ersatz macht nur das Ranking messbar, der Fehler bleibt Befund
    gold_ok            Goldtext steht wortgetreu im Dokument
    unklar             keine Spanne mit Sollwert – manuell prüfen, nicht ersetzt

Zusätzlich: `ueber_chunks` – die Spanne liegt über zwei Chunks. Dann wird der Ersatz auf das Stück
im Chunk mit dem Sollwert gekürzt (nur so ist „Zielchunk im Kontext“ überhaupt definiert).

Schreibt golden-v2.json (Original bleibt unverändert) und eine private Sichtungsliste in --private.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from dokumentenassistent.antwort_eval import normalisiere_whitespace as ws
from dokumentenassistent.index import Index
from dokumentenassistent.seitenvergleich import _ausserhalb_git, _ziel_dateien
from dokumentenassistent.pfade_privat import FRAGEN, LAEUFE

_ZEICHEN = str.maketrans({'„': '"', '“': '"', '”': '"', '‚': "'", '‘': "'", '’': "'", '–': '-', '—': '-',
                          '­': '', ' ': ' '})
MIN_ABDECKUNG = 0.6
ERSETZBAR = ('gold_schreibweise', 'auslesefehler')


def locker(text: str) -> str:
    """Nur für die Klassifikation: Case, typografische Zeichen, Silbentrennung am Zeilenende."""
    t = unicodedata.normalize('NFKC', text).translate(_ZEICHEN).casefold()
    return ws(re.sub(r'(\w)-\s+(\w)', r'\1\2', t))


@dataclass(frozen=True)
class Befund:
    nr: int
    klasse: str
    abdeckung: float  # Anteil der Zielabsatz-Zeichen, die in der Spanne übereinstimmen
    ueber_chunks: bool
    ersatz: str | None  # privat; messbarer Zieltext (liegt in genau einem Chunk)


def beste_spanne(ziel: str, dokument: str) -> tuple[float, str]:
    """Ähnlichste Spanne von `dokument` zu `ziel` (case-insensitiv), ohne überstehende Ränder."""
    z, d = ziel.casefold(), dokument.casefold()
    bloecke = [b for b in difflib.SequenceMatcher(None, z, d, autojunk=False).get_matching_blocks()
               if b.size >= 4]
    if not bloecke:
        return 0.0, ''
    fenster = int(len(z) * 1.5) + 20
    bestes = (0, 0, 0)
    for i, start in enumerate(bloecke):
        treffer = [b for b in bloecke[i:] if b.b + b.size - start.b <= fenster]
        summe = sum(b.size for b in treffer)
        if summe > bestes[0]:
            bestes = (summe, start.b, treffer[-1].b + treffer[-1].size)
    summe, von, bis = bestes
    while von > 0 and not dokument[von - 1].isspace():  # kurze Randblöcke (< 4 Zeichen) zurückholen
        von -= 1
    while bis < len(dokument) and not dokument[bis].isspace():
        bis += 1
    spanne = _raender_kappen(ziel, dokument[von:bis])
    return summe / len(z), spanne


def _raender_kappen(ziel: str, spanne: str) -> str:
    """Überstehenden Text vorn/hinten entfernen, der im Ziel keine Entsprechung hat."""
    ops = difflib.SequenceMatcher(None, ziel.casefold(), spanne.casefold(), autojunk=False).get_opcodes()
    von = ops[0][4] if ops and ops[0][0] == 'insert' else 0
    bis = ops[-1][3] if ops and ops[-1][0] == 'insert' else len(spanne)
    return spanne[von:bis].strip().rstrip(' ([{„"')  # öffnende Zeichen gehören zum nächsten Absatz


def _auf_einen_chunk(spanne: str, texte: list[str], wert: str) -> str | None:
    """Längstes Stück der Spanne, das vollständig in einem Chunk mit dem Sollwert liegt."""
    stuecke = []
    for t in texte:
        if wert not in t:
            continue
        m = difflib.SequenceMatcher(None, spanne, t, autojunk=False).find_longest_match(0, len(spanne), 0, len(t))
        stueck = spanne[m.a:m.a + m.size].strip()
        if wert in stueck:
            stuecke.append(stueck)
    return max(stuecke, key=len, default=None)


def klassifiziere(frage: dict, chunks: list[str]) -> Befund:
    ziel = ws(frage.get('zielabsatz') or '')
    wert = ws(frage.get('wortlaut_enthaelt') or '')
    texte = [ws(c) for c in chunks]
    dokument = ' '.join(texte)
    if ziel in dokument:
        abdeckung, spanne, klasse = 1.0, ziel, 'gold_ok'
    else:
        abdeckung, spanne = beste_spanne(ziel, dokument)
        abdeckung = round(abdeckung, 3)
        if abdeckung < MIN_ABDECKUNG or not wert or wert not in spanne:
            return Befund(frage['nr'], 'unklar', abdeckung, False, None)
        klasse = 'gold_schreibweise' if locker(ziel) == locker(spanne) else 'auslesefehler'
    if any(spanne in t for t in texte):
        return Befund(frage['nr'], klasse, abdeckung, False, spanne)
    ersatz = _auf_einen_chunk(spanne, texte, wert)
    return Befund(frage['nr'], klasse if ersatz else 'unklar', abdeckung, True, ersatz)


def betroffene(fragen: list[dict], index: Index) -> list[tuple[dict, list[list[str]]]]:
    """Positive Fragen, deren Zielabsatz in keinem Chunk einer namenspassenden Zieldatei steht."""
    raus = []
    for f in fragen:
        if f['status'] != 'gefunden' or not (f.get('zielabsatz') or '').strip():
            continue
        je_datei = [[fs.text for fs in sorted(index.fundstellen(d.hash), key=lambda x: (x.seite, x.absatz))]
                    for d in _ziel_dateien(f, index)]
        if je_datei and not any(ws(f['zielabsatz']) in ws(c) for chunks in je_datei for c in chunks):
            raus.append((f, je_datei))
    return raus


def befund(frage: dict, je_datei: list[list[str]]) -> Befund:
    """Bei gleichnamigen Dateien genügt eine; die Messung akzeptiert jede namenspassende Datei."""
    alle = [klassifiziere(frage, chunks) for chunks in je_datei]
    return next((b for b in alle if b.ersatz), alle[0])


def neues_gold(gold: dict, befunde: list[Befund], quelle_sha: str) -> dict:
    ersatz = {b.nr: b for b in befunde if b.ersatz and (b.klasse in ERSETZBAR or b.ueber_chunks)}
    fragen = []
    for f in gold['fragen']:
        b = ersatz.get(f['nr'])
        fragen.append({**f, 'zielabsatz': b.ersatz, 'zielabsatz_alt': f['zielabsatz'],
                       'zielabsatz_bereinigt': b.klasse, 'zielabsatz_ueber_chunks': b.ueber_chunks}
                      if b else dict(f))
    klasse = lambda k: sorted(b.nr for b in befunde if b.klasse == k)
    return {**gold, 'fragen': fragen, 'bereinigung': {
        'datum': '2026-09-29', 'basis_sha256': quelle_sha,
        'regel': 'Zielabsatz durch die ähnlichste ausgelesene Spanne ersetzt, nur wenn sie den Sollwert '
                 'enthält; bei Chunkgrenzen auf das Stück im Chunk mit dem Sollwert gekürzt. Sollwert, '
                 'Datei und Status unverändert. auslesefehler = Fehler unseres Index, nicht des Golds.',
        'ersetzt': sorted(ersatz), 'gold_schreibweise': klasse('gold_schreibweise'),
        'auslesefehler': klasse('auslesefehler'),
        'ueber_chunks': sorted(b.nr for b in befunde if b.ueber_chunks), 'unklar': klasse('unklar')}}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--gold', type=Path, default=FRAGEN / 'golden.json')
    p.add_argument('--index', type=Path, required=True, help='Arbeitsordner des ausgelesenen Index')
    p.add_argument('--ausgabe', type=Path, default=FRAGEN / 'golden-v2.json')
    p.add_argument('--private', type=Path, default=LAEUFE / 'gold-bereinigung')
    a = p.parse_args()
    for pfad in (a.private.resolve(), a.ausgabe.resolve().parent):
        _ausserhalb_git(pfad)
    if a.ausgabe.exists():
        p.error(f'{a.ausgabe} existiert bereits – nicht überschrieben')
    roh = a.gold.read_bytes()
    gold = json.loads(roh)
    befunde = [befund(f, je) for f, je in betroffene(gold['fragen'], Index(a.index))]
    a.private.mkdir(parents=True, exist_ok=True)
    nach_nr = {f['nr']: f for f in gold['fragen']}
    sichtung = [{'nr': b.nr, 'klasse': b.klasse, 'ueber_chunks': b.ueber_chunks, 'abdeckung': b.abdeckung,
                 'sollwert': nach_nr[b.nr].get('wortlaut_enthaelt'), 'alt': nach_nr[b.nr]['zielabsatz'],
                 'neu': b.ersatz} for b in befunde]
    (a.private / 'sichtung.json').write_text(json.dumps(sichtung, ensure_ascii=False, indent=1), encoding='utf-8')
    a.ausgabe.write_text(json.dumps(neues_gold(gold, befunde, hashlib.sha256(roh).hexdigest()),
                                    ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps([{'nr': b.nr, 'klasse': b.klasse, 'ueber_chunks': b.ueber_chunks,
                       'abdeckung': b.abdeckung} for b in befunde]))


if __name__ == '__main__':
    main()

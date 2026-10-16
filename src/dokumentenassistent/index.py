"""SQLite-Index: registrierte Dateien, Fundstellen, Vorschläge, Konflikte,
Embeddings und ein append-only Protokoll.
"""
from __future__ import annotations

import json
import hashlib
import math
import sqlite3
import threading
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from dokumentenassistent.typen import (
    Beleg,
    Datei,
    Feld,
    Fundstelle,
    SeitenSpanne,
    Konflikt,
    Status,
    Vorschlag,
)
from dokumentenassistent.fundstellen import fundstellen_id

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dateien (
    hash TEXT PRIMARY KEY,
    pfad TEXT NOT NULL,
    name TEXT NOT NULL,
    groesse INTEGER NOT NULL,
    status TEXT NOT NULL,
    bestaetigt INTEGER NOT NULL DEFAULT 0,
    zielpfad TEXT
);
CREATE TABLE IF NOT EXISTS fundstellen (
    id TEXT PRIMARY KEY,
    datei_hash TEXT NOT NULL REFERENCES dateien(hash),
    datei_name TEXT NOT NULL,
    seite INTEGER NOT NULL,
    absatz INTEGER NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vorschlaege (
    datei_hash TEXT PRIMARY KEY REFERENCES dateien(hash),
    datei_name TEXT NOT NULL,
    kategorie TEXT,
    typ TEXT,
    felder TEXT NOT NULL,
    zielname TEXT,
    status TEXT NOT NULL,
    begruendung TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS konflikte (
    id TEXT PRIMARY KEY,
    feld TEXT NOT NULL,
    hash_a TEXT NOT NULL,
    hash_b TEXT NOT NULL,
    wert_a TEXT NOT NULL,
    wert_b TEXT NOT NULL,
    beleg_a TEXT NOT NULL,
    beleg_b TEXT NOT NULL,
    vorschlag TEXT NOT NULL,
    entscheidung TEXT,
    eigener_wert TEXT
);
CREATE TABLE IF NOT EXISTS embeddings (
    fundstelle_id TEXT PRIMARY KEY REFERENCES fundstellen(id),
    vektor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS duplikate (
    pfad TEXT PRIMARY KEY,
    hash TEXT NOT NULL REFERENCES dateien(hash),
    name TEXT NOT NULL,
    groesse INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fundstellen_alias (
    alias TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY(alias, target_id)
);
CREATE TABLE IF NOT EXISTS mehrdeutige_alias (
    alias TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS auslesungen (
    datei_hash TEXT PRIMARY KEY REFERENCES dateien(hash),
    seiten TEXT NOT NULL
);
"""


_GUELTIGES_EMBEDDING = (
    "e.text_sha256=text_sha256(f.text) AND e.modell_revision IS NOT NULL "
    "AND e.modell_revision<>'' AND e.vorverarbeitung=? "
    "AND (? IS NULL OR e.modell_revision=?)"
)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validiere_vektoren(vektoren, anzahl: int) -> None:
    """Validate the complete batch before any vector can be persisted."""
    if not isinstance(vektoren, (list, tuple)) or len(vektoren) != anzahl:
        raise ValueError('Embedding-Anzahl stimmt nicht')
    dimension = None
    for vector in vektoren:
        if not isinstance(vector, (list, tuple)) or not vector:
            raise ValueError('Embedding-Dimension ist leer')
        dimension = len(vector) if dimension is None else dimension
        if len(vector) != dimension:
            raise ValueError('Embedding-Dimensionen stimmen nicht überein')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
            raise ValueError('Embedding enthält ungültige Werte')
        if not any(vector):
            raise ValueError('Embedding ist ein Nullvektor')


def _zeile_zu_datei(row: tuple) -> Datei:
    return Datei(hash=row[0], pfad=Path(row[1]), name=row[2], groesse=row[3])


def _validiere_spannen(fundstelle: Fundstelle) -> None:
    if not fundstelle.spannen:
        return
    if fundstelle.spannen[0].seite != fundstelle.seite:
        raise ValueError('Seiten-Spannen beginnen nicht auf der Fundstellenseite')
    voriges_ende = 0
    vorige_seite = 0
    for spanne in fundstelle.spannen:
        if (not isinstance(spanne, SeitenSpanne)
                or type(spanne.seite) is not int or type(spanne.start) is not int
                or type(spanne.ende) is not int or spanne.seite < 1
                or spanne.start < voriges_ende or spanne.ende <= spanne.start
                or spanne.ende > len(fundstelle.text) or spanne.seite < vorige_seite):
            raise ValueError('Seiten-Spannen sind ungültig')
        voriges_ende = spanne.ende
        vorige_seite = spanne.seite


def _zeile_zu_fundstelle(row: tuple) -> Fundstelle:
    spannen = tuple(SeitenSpanne(*werte) for werte in json.loads(row[6])) if row[6] else ()
    return Fundstelle(id=row[0], datei_hash=row[1], datei_name=row[2], seite=row[3],
                      absatz=row[4], text=row[5], spannen=spannen)


def _feld_zu_dict(f: Feld) -> dict:
    beleg = None if f.beleg is None else {"fundstelle_id": f.beleg.fundstelle_id, "wortlaut": f.beleg.wortlaut}
    return {"name": f.name, "wert": f.wert, "beleg": beleg, "status": f.status}


def _dict_zu_feld(d: dict) -> Feld:
    beleg = None if d["beleg"] is None else Beleg(**d["beleg"])
    return Feld(name=d["name"], wert=d["wert"], beleg=beleg, status=d["status"])


def _beleg_zu_json(b: Beleg) -> str:
    return json.dumps({"fundstelle_id": b.fundstelle_id, "wortlaut": b.wortlaut})


def _beleg_von_json(s: str) -> Beleg:
    return Beleg(**json.loads(s))


class Index:
    """SQLite-gestützter Index für einen Arbeitsordner."""

    def __init__(self, arbeitsordner: Path) -> None:
        ordner = Path(arbeitsordner) / ".dokumentenassistent"
        ordner.mkdir(parents=True, exist_ok=True)
        self._db_pfad = ordner / "index.sqlite"
        self._protokoll_pfad = ordner / "protokoll.jsonl"
        # check_same_thread=False: die Web-Oberfläche bedient Anfragen in Worker-Threads,
        # und das Einordnen schreibt aus einem eigenen Thread, während die Seite liest.
        # sqlite3 serialisiert das NICHT von sich aus: zwei Threads teilen sich auf einer
        # Verbindung den Statement-Cache, greifen auf dasselbe vorbereitete Statement zu und
        # bekommen sqlite3.InterfaceError (bad parameter or other API misuse) oder, schlimmer,
        # Zeilen aus der fremden Abfrage. Deshalb geht jeder Zugriff durch _schloss, und zwar
        # bis die Zeilen geholt sind: ein offener Cursor hält dasselbe Statement, das der
        # andere Thread gerade zurücksetzt.
        self._schloss = threading.RLock()
        self._conn = sqlite3.connect(self._db_pfad, check_same_thread=False, timeout=30)
        with self._schloss:
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            # Old rows deliberately retain NULL provenance: never infer a model
            # or text fingerprint for a vector whose origin was not recorded.
            columns = {r[1] for r in self._conn.execute('PRAGMA table_info(embeddings)')}
            for name in ('text_sha256', 'modell_revision', 'vorverarbeitung'):
                if name not in columns:
                    self._conn.execute(f'ALTER TABLE embeddings ADD COLUMN {name} TEXT')
            fundstellen_columns = {r[1] for r in self._conn.execute('PRAGMA table_info(fundstellen)')}
            if 'spannen' not in fundstellen_columns:
                self._conn.execute('ALTER TABLE fundstellen ADD COLUMN spannen TEXT')
            self._conn.create_function('text_sha256', 1, _text_hash, deterministic=True)
            self._conn.commit()

    def _alle(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._schloss:
            return self._conn.execute(sql, params).fetchall()

    def _eine(self, sql: str, params: tuple = ()) -> tuple | None:
        with self._schloss:
            return self._conn.execute(sql, params).fetchone()

    def _schreibe(self, sql: str, params: tuple = ()) -> None:
        with self._schloss:
            self._conn.execute(sql, params)
            self._conn.commit()

    def _schreibe_viele(self, sql: str, zeilen: list[tuple]) -> None:
        with self._schloss:
            self._conn.executemany(sql, zeilen)
            self._conn.commit()

    def registriere(self, datei: Datei, status: Status) -> None:
        self._schreibe(
            "INSERT OR IGNORE INTO dateien (hash, pfad, name, groesse, status) VALUES (?, ?, ?, ?, ?)",
            (datei.hash, str(datei.pfad), datei.name, datei.groesse, status),
        )

    def datei(self, hash: str) -> Datei | None:
        row = self._eine(
            "SELECT hash, pfad, name, groesse FROM dateien WHERE hash = ?", (hash,)
        )
        return None if row is None else _zeile_zu_datei(row)

    def dateien(self) -> tuple[Datei, ...]:
        """Alle registrierten Dateien (erster Fundort je Hash), sortiert nach Pfad."""
        rows = self._alle("SELECT hash, pfad, name, groesse FROM dateien ORDER BY pfad")
        return tuple(_zeile_zu_datei(r) for r in rows)

    def setze_status(self, hash: str, status: Status) -> None:
        if self.datei(hash) is None:
            raise ValueError(f"Datei nicht registriert: {hash!r}")
        self._schreibe("UPDATE dateien SET status = ? WHERE hash = ?", (status, hash))

    def status(self, hash: str) -> Status | None:
        row = self._eine("SELECT status FROM dateien WHERE hash = ?", (hash,))
        return None if row is None else row[0]

    def zielpfad(self, hash: str) -> Path | None:
        row = self._eine("SELECT zielpfad FROM dateien WHERE hash = ?", (hash,))
        return None if row is None or row[0] is None else Path(row[0])

    def registriere_duplikat(self, datei: Datei) -> None:
        """Weiterer Fundort eines bereits registrierten Hashes. Die Datei bleibt, wo sie ist."""
        if self.datei(datei.hash) is None:
            raise ValueError(f"Datei nicht registriert: {datei.hash!r}")
        self._schreibe(
            "INSERT OR IGNORE INTO duplikate (pfad, hash, name, groesse) VALUES (?, ?, ?, ?)",
            (str(datei.pfad), datei.hash, datei.name, datei.groesse),
        )

    def duplikate(self) -> tuple[Datei, ...]:
        rows = self._alle("SELECT hash, pfad, name, groesse FROM duplikate ORDER BY pfad")
        return tuple(_zeile_zu_datei(r) for r in rows)

    def speichere_fundstellen(self, fundstellen: tuple[Fundstelle, ...]) -> None:
        with self._schloss, self._conn:
            self._speichere_fundstellen(fundstellen)

    def migriere_legacy_fundstellen(self) -> dict:
        """Explicit copy-only migration; caller must provide a disposable index copy.

        This method never reads originals or invents chunks lost to old name collisions.
        Report empty registered documents for a later re-extraction from originals.
        """
        counts = {'migrated_chunks': 0, 'documents_without_chunks': []}
        for doc in self.dateien():
            old = self.fundstellen(doc.hash)
            if not old:
                counts['documents_without_chunks'].append(doc.hash)
                continue
            new = tuple(replace(f, id=fundstellen_id(f.datei_hash, f.seite, f.absatz, f.text))
                        for f in old)
            changed = sum(a.id != b.id for a, b in zip(old, new))
            if changed:
                self.ersetze_fundstellen(doc.hash, new)
                counts['migrated_chunks'] += changed
        # The old global key collapsed same-name sources. A sole surviving alias
        # is still ambiguous when multiple registered documents share the name.
        with self._schloss, self._conn:
            groups = self._conn.execute(
                'SELECT name FROM dateien GROUP BY name HAVING COUNT(*)>1').fetchall()
            for (name,) in groups:
                for f in self._alle('SELECT seite,absatz FROM fundstellen WHERE datei_name=?', (name,)):
                    self._conn.execute('INSERT OR IGNORE INTO mehrdeutige_alias(alias) VALUES (?)',
                                       (f'{name}#S{f[0]}#A{f[1]}',))
        return counts

    def ersetze_fundstellen(self, datei_hash: str, fundstellen: tuple[Fundstelle, ...], *,
                           extraktion: tuple[tuple[int, str | None, str | None], ...] = ()) -> None:
        """Replace one successfully read document in one SQLite transaction.

        An empty tuple is an explicit successful empty extraction. Callers must not
        invoke this method when extraction raised an error.
        """
        if self.datei(datei_hash) is None:
            raise ValueError('Datei nicht registriert')
        if any(f.datei_hash != datei_hash for f in fundstellen):
            raise ValueError('Fundstelle gehört zu einem anderen Dokument')
        if len({f.id for f in fundstellen}) != len(fundstellen):
            raise ValueError('Doppelte Fundstellen-Identität')
        with self._schloss, self._conn:
            previous = {f.id: f for f in self.fundstellen(datei_hash)}
            current = {f.id: f for f in fundstellen}
            obsolete = set(previous) - set(current)
            changed = {fid for fid in previous.keys() & current.keys()
                       if previous[fid].text != current[fid].text}
            new_by_text: dict[str, list[Fundstelle]] = {}
            for f in fundstellen:
                new_by_text.setdefault(f.text, []).append(f)
            transferred = {
                old_id: matches[0].id for old_id in obsolete
                if len(matches := new_by_text.get(previous[old_id].text, [])) == 1
                and previous[old_id].datei_hash == matches[0].datei_hash
            }
            for fid in obsolete:
                self._conn.execute('DELETE FROM embeddings WHERE fundstelle_id=?', (fid,))
                self._conn.execute('DELETE FROM fundstellen WHERE id=? AND datei_hash=?', (fid, datei_hash))
                self._conn.execute('DELETE FROM fundstellen_alias WHERE target_id=?', (fid,))
            self._speichere_fundstellen(fundstellen)
            self._uebertrage_belege(datei_hash, transferred)
            # Transferred references now carry new IDs. Any old reference left
            # behind belongs to an unverified owner or lacks matching text.
            self._entwerte_belege(obsolete | changed)
            self._conn.execute('INSERT INTO auslesungen(datei_hash,seiten) VALUES (?,?) '
                               'ON CONFLICT(datei_hash) DO UPDATE SET seiten=excluded.seiten',
                               (datei_hash, json.dumps(extraktion)))

    def ausleseprotokoll(self, datei_hash: str) -> tuple[tuple[int, str | None, str | None], ...] | None:
        row = self._eine('SELECT seiten FROM auslesungen WHERE datei_hash=?', (datei_hash,))
        return None if row is None else tuple(tuple(item) for item in json.loads(row[0]))

    def _uebertrage_belege(self, datei_hash: str, transfers: dict[str, str]) -> None:
        from dokumentenassistent.zitatpruefung import normalisiere
        if not transfers:
            return
        for owner, raw in self._conn.execute('SELECT datei_hash, felder FROM vorschlaege').fetchall():
            if owner != datei_hash:
                continue
            fields = json.loads(raw)
            dirty = False
            for field in fields:
                beleg = field.get('beleg')
                if beleg and beleg.get('fundstelle_id') in transfers:
                    target = self.fundstelle(transfers[beleg['fundstelle_id']])
                    quote = normalisiere(beleg.get('wortlaut') or '')
                    if target and quote and quote in normalisiere(target.text):
                        beleg['fundstelle_id'] = target.id
                        dirty = True
            if dirty:
                self._conn.execute('UPDATE vorschlaege SET felder=? WHERE datei_hash=?',
                                   (json.dumps(fields), owner))
        for cid, hash_a, hash_b, raw_a, raw_b in self._conn.execute(
            'SELECT id,hash_a,hash_b,beleg_a,beleg_b FROM konflikte').fetchall():
            data = [json.loads(raw_a), json.loads(raw_b)]
            dirty = False
            for owner, beleg in zip((hash_a, hash_b), data):
                if owner == datei_hash and beleg['fundstelle_id'] in transfers:
                    target = self.fundstelle(transfers[beleg['fundstelle_id']])
                    quote = normalisiere(beleg.get('wortlaut') or '')
                    if target and quote and quote in normalisiere(target.text):
                        beleg['fundstelle_id'] = target.id
                        dirty = True
            if dirty:
                self._conn.execute('UPDATE konflikte SET beleg_a=?,beleg_b=? WHERE id=?',
                                   (json.dumps(data[0]), json.dumps(data[1]), cid))

    def _entwerte_belege(self, ids: set[str]) -> None:
        """Persisted field claims cannot remain proven by removed or changed text."""
        if not ids:
            return
        for doc_hash, raw in self._conn.execute('SELECT datei_hash, felder FROM vorschlaege').fetchall():
            fields = json.loads(raw)
            dirty = False
            for field in fields:
                if field.get('beleg') and field['beleg'].get('fundstelle_id') in ids:
                    field.update(wert=None, beleg=None, status='unklar')
                    dirty = True
            if dirty:
                self._conn.execute('UPDATE vorschlaege SET felder=?, status=? WHERE datei_hash=?',
                                   (json.dumps(fields), 'unklar', doc_hash))
                self._conn.execute('UPDATE dateien SET status=? WHERE hash=?', ('unklar', doc_hash))

    def pruefe_persistierte_belege(self) -> dict[str, int]:
        """Repair stale field claims on a migration copy; retain human approvals."""
        from dokumentenassistent.zitatpruefung import normalisiere
        downgraded = 0
        unresolved_conflicts = 0
        with self._schloss, self._conn:
            for owner, raw in self._conn.execute('SELECT datei_hash,felder FROM vorschlaege').fetchall():
                fields = json.loads(raw)
                dirty = False
                for field in fields:
                    beleg = field.get('beleg')
                    if not beleg or field.get('status') != 'belegt':
                        continue
                    source = self._fundstelle_direkt(beleg['fundstelle_id'])
                    quote = normalisiere(beleg.get('wortlaut') or '')
                    if source is None or source.datei_hash != owner or not quote or quote not in normalisiere(source.text):
                        field.update(wert=None, beleg=None, status='unklar')
                        downgraded += 1
                        dirty = True
                if dirty:
                    self._conn.execute('UPDATE vorschlaege SET felder=?,status=? WHERE datei_hash=?',
                                       (json.dumps(fields), 'unklar', owner))
                    self._conn.execute('UPDATE dateien SET status=? WHERE hash=?', ('unklar', owner))
            for hash_a, hash_b, raw_a, raw_b in self._conn.execute(
                'SELECT hash_a,hash_b,beleg_a,beleg_b FROM konflikte').fetchall():
                for owner, raw in ((hash_a, raw_a), (hash_b, raw_b)):
                    beleg = json.loads(raw)
                    source = self._fundstelle_direkt(beleg['fundstelle_id'])
                    quote = normalisiere(beleg.get('wortlaut') or '')
                    if source is None or source.datei_hash != owner or not quote or quote not in normalisiere(source.text):
                        unresolved_conflicts += 1
        return {'downgraded_fields': downgraded, 'unresolved_conflict_belege': unresolved_conflicts}

    def _speichere_fundstellen(self, fundstellen: tuple[Fundstelle, ...]) -> None:
        """Caller owns transaction and lock; no intermediate commit."""
        for f in fundstellen:
            _validiere_spannen(f)
            if self.datei(f.datei_hash) is None:
                raise ValueError('Datei nicht registriert')
            old = self._fundstelle_direkt(f.id)
            if old and (old.datei_hash, old.seite, old.absatz) != (f.datei_hash, f.seite, f.absatz):
                raise ValueError('Fundstellen-Identität kollidiert')
            if old and old.text != f.text:
                self._conn.execute('DELETE FROM embeddings WHERE fundstelle_id=?', (f.id,))
            self._conn.execute(
                'INSERT INTO fundstellen(id,datei_hash,datei_name,seite,absatz,text,spannen) VALUES(?,?,?,?,?,?,?) '
                'ON CONFLICT(id) DO UPDATE SET datei_name=excluded.datei_name, text=excluded.text, '
                'spannen=excluded.spannen',
                (f.id, f.datei_hash, f.datei_name, f.seite, f.absatz, f.text,
                 json.dumps([(s.seite, s.start, s.ende) for s in f.spannen]) if f.spannen else None))
            alias = f'{f.datei_name}#S{f.seite}#A{f.absatz}'
            if alias != f.id:
                self._conn.execute('INSERT OR IGNORE INTO fundstellen_alias(alias,target_id) VALUES (?,?)',
                                   (alias, f.id))
                targets = self._conn.execute('SELECT target_id FROM fundstellen_alias WHERE alias=? LIMIT 2',
                                             (alias,)).fetchall()
                if len(targets) > 1:
                    self._conn.execute('INSERT OR IGNORE INTO mehrdeutige_alias(alias) VALUES (?)', (alias,))

    def fundstellen(self, datei_hash: str) -> tuple[Fundstelle, ...]:
        rows = self._alle(
            "SELECT id, datei_hash, datei_name, seite, absatz, text, spannen FROM fundstellen "
            "WHERE datei_hash = ? ORDER BY seite, absatz",
            (datei_hash,),
        )
        return tuple(_zeile_zu_fundstelle(r) for r in rows)

    def fundstelle(self, id: str) -> Fundstelle | None:
        direct = self._fundstelle_direkt(id)
        if direct is not None:
            if id != fundstellen_id(direct.datei_hash, direct.seite, direct.absatz, direct.text):
                count = self._eine('SELECT COUNT(*) FROM dateien WHERE name=?', (direct.datei_name,))[0]
                if count != 1 or self._eine('SELECT 1 FROM mehrdeutige_alias WHERE alias=?', (id,)):
                    return None
            return direct
        if self._eine('SELECT 1 FROM mehrdeutige_alias WHERE alias=?', (id,)):
            return None
        target = self._alle('SELECT target_id FROM fundstellen_alias WHERE alias=? LIMIT 2', (id,))
        if len(target) != 1:
            return None
        resolved = self.fundstelle(target[0][0])
        if resolved is None:
            return None
        count = self._eine('SELECT COUNT(*) FROM dateien WHERE name=?', (resolved.datei_name,))[0]
        return resolved if count == 1 else None

    def _fundstelle_direkt(self, id: str) -> Fundstelle | None:
        row = self._eine(
            "SELECT id, datei_hash, datei_name, seite, absatz, text, spannen FROM fundstellen WHERE id = ?",
            (id,),
        )
        if row is None:
            return None
        return _zeile_zu_fundstelle(row)

    def speichere_vorschlag(self, v: Vorschlag) -> None:
        felder_json = json.dumps([_feld_zu_dict(f) for f in v.felder])
        self._schreibe(
            "INSERT OR REPLACE INTO vorschlaege "
            "(datei_hash, datei_name, kategorie, typ, felder, zielname, status, begruendung) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (v.datei_hash, v.datei_name, v.kategorie, v.typ, felder_json, v.zielname, v.status, v.begruendung),
        )

    def vorschlaege(self) -> tuple[Vorschlag, ...]:
        rows = self._alle(
            "SELECT datei_hash, datei_name, kategorie, typ, felder, zielname, status, begruendung "
            "FROM vorschlaege ORDER BY datei_hash"
        )
        out = []
        for r in rows:
            felder = tuple(_dict_zu_feld(d) for d in json.loads(r[4]))
            out.append(
                Vorschlag(
                    datei_hash=r[0], datei_name=r[1], kategorie=r[2], typ=r[3],
                    felder=felder, zielname=r[5], status=r[6], begruendung=r[7],
                )
            )
        return tuple(out)

    def speichere_konflikt(self, k: Konflikt) -> None:
        self._schreibe(
            "INSERT OR REPLACE INTO konflikte "
            "(id, feld, hash_a, hash_b, wert_a, wert_b, beleg_a, beleg_b, vorschlag, entscheidung, eigener_wert) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                k.id, k.feld, k.hash_a, k.hash_b, k.wert_a, k.wert_b,
                _beleg_zu_json(k.beleg_a), _beleg_zu_json(k.beleg_b),
                k.vorschlag, k.entscheidung, k.eigener_wert,
            ),
        )

    def konflikte(self, offen: bool | None = None) -> tuple[Konflikt, ...]:
        sql = (
            "SELECT id, feld, hash_a, hash_b, wert_a, wert_b, beleg_a, beleg_b, "
            "vorschlag, entscheidung, eigener_wert FROM konflikte"
        )
        params: tuple = ()
        if offen is True:
            sql += " WHERE entscheidung IS NULL"
        elif offen is False:
            sql += " WHERE entscheidung IS NOT NULL"
        sql += " ORDER BY id"
        rows = self._alle(sql, params)
        return tuple(
            Konflikt(
                id=r[0], feld=r[1], hash_a=r[2], hash_b=r[3], wert_a=r[4], wert_b=r[5],
                beleg_a=_beleg_von_json(r[6]), beleg_b=_beleg_von_json(r[7]),
                vorschlag=r[8], entscheidung=r[9], eigener_wert=r[10],
            )
            for r in rows
        )

    def markiere_bestaetigt(self, datei_hash: str, zielpfad: Path) -> None:
        self._schreibe(
            "UPDATE dateien SET bestaetigt = 1, zielpfad = ? WHERE hash = ?",
            (str(zielpfad), datei_hash),
        )

    def speichere_embeddings(self, paare: tuple[tuple[str, list[float]], ...], *,
                            modell_revision: str, erwartete_texte: dict[str, str],
                            vorverarbeitung: str = 'raw-v1') -> None:
        if not modell_revision or not vorverarbeitung:
            raise ValueError('Embedding-Provenienz fehlt')
        ids = [fid for fid, _ in paare]
        if len(set(ids)) != len(ids) or set(ids) != set(erwartete_texte):
            raise ValueError('Embedding-Anzahl/IDs stimmen nicht mit dem Textbestand überein')
        validiere_vektoren([v for _, v in paare], len(erwartete_texte))
        with self._schloss, self._conn:
            rows = []
            for fid, vector in paare:
                f = self.fundstelle(fid)
                if f is None or f.text != erwartete_texte[fid]:
                    raise ValueError('Embedding-Text wurde während der Berechnung verändert')
                rows.append((fid, json.dumps(vector), _text_hash(f.text), modell_revision, vorverarbeitung))
            existing = self._conn.execute(
                'SELECT vektor FROM embeddings WHERE modell_revision=? AND vorverarbeitung=? LIMIT 1',
                (modell_revision, vorverarbeitung)).fetchone()
            if existing and paare and len(json.loads(existing[0])) != len(paare[0][1]):
                raise ValueError('Embedding-Dimension passt nicht zum Modell')
            self._conn.executemany(
                'INSERT OR REPLACE INTO embeddings '
                '(fundstelle_id,vektor,text_sha256,modell_revision,vorverarbeitung) VALUES(?,?,?,?,?)', rows)

    def fundstellen_ohne_embedding(self, *, modell_revision: str | None = None,
                                  vorverarbeitung: str = 'raw-v1') -> tuple[Fundstelle, ...]:
        """Für das Nachziehen beim Auslesen — ein zweiter Lauf bettet nichts doppelt ein."""
        rows = self._alle(
            "SELECT f.id, f.datei_hash, f.datei_name, f.seite, f.absatz, f.text, f.spannen "
            "FROM fundstellen f LEFT JOIN embeddings e ON e.fundstelle_id = f.id AND "
            + _GUELTIGES_EMBEDDING + " WHERE e.fundstelle_id IS NULL ORDER BY f.id",
            (vorverarbeitung, modell_revision, modell_revision),
        )
        return tuple(_zeile_zu_fundstelle(r) for r in rows)

    def durchsuchbare_fundstellen(self, *, modell_revision: str | None = None,
                                 vorverarbeitung: str = 'raw-v1') -> tuple[tuple[Fundstelle, list[float]], ...]:
        """Alles, was ein Embedding hat — unabhängig davon, ob die Datei abgelegt ist.

        Bis 24.09.2026 stand hier zusätzlich `WHERE d.bestaetigt = 1`, und Embeddings
        entstanden erst beim Ablegen. Ein Dokument ohne Kategorie war damit für jede
        Suche unsichtbar. Gemessen am echten Bestand: 31 von 85 Fragen waren dadurch
        unbeantwortbar, bevor die Suche überhaupt lief — 36 % des Ergebnisses hingen
        an einer Einordnungsentscheidung, die mit Auffindbarkeit nichts zu tun hat.
        Die Einordnung entscheidet über die Ablage, nicht über den Index.
        """
        rows = self._alle(
            "SELECT f.id, f.datei_hash, f.datei_name, f.seite, f.absatz, f.text, f.spannen, e.vektor "
            "FROM fundstellen f "
            "JOIN embeddings e ON e.fundstelle_id = f.id WHERE "
            + _GUELTIGES_EMBEDDING + " ORDER BY f.id",
            (vorverarbeitung, modell_revision, modell_revision),
        )
        return tuple(
            (
                _zeile_zu_fundstelle(r),
                json.loads(r[7]),
            )
            for r in rows
        )

    def protokolliere(self, art: str, **daten) -> None:
        eintrag = {"zeit": datetime.now(timezone.utc).isoformat(), "art": art, **daten}
        with self._protokoll_pfad.open("a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")

    def protokoll(self) -> tuple[dict, ...]:
        """Alle Protokollzeilen in Schreibreihenfolge; nur lesen, nie ändern."""
        if not self._protokoll_pfad.exists():
            return ()
        zeilen = self._protokoll_pfad.read_text(encoding="utf-8").splitlines()
        return tuple(json.loads(z) for z in zeilen if z.strip())

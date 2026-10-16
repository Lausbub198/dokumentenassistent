"""Copy-only migration of a legacy index; never opens the source for writing."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from dokumentenassistent.index import Index


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migriere_index_kopie(quelle: Path, ziel: Path) -> dict:
    quelle, ziel = Path(quelle).resolve(), Path(ziel).resolve()
    if ziel == quelle or ziel.is_relative_to(quelle):
        raise ValueError('Ziel muss außerhalb des Quellbestands liegen')
    source = quelle/'.dokumentenassistent/index.sqlite'
    if not source.is_file():
        raise FileNotFoundError('Quellindex nicht gefunden')
    if ziel.exists():
        raise FileExistsError('Ziel existiert bereits')
    before = _sha(source)
    private_dir = ziel/'.dokumentenassistent'
    private_dir.mkdir(mode=0o700, parents=True)
    dest = private_dir/'index.sqlite'
    with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as read_db:
        with sqlite3.connect(dest) as write_db:
            read_db.backup(write_db)
    log = quelle/'.dokumentenassistent/protokoll.jsonl'
    if log.is_file():
        shutil.copy2(log, private_dir/'protokoll.jsonl')
    index = Index(ziel)
    result = index.migriere_legacy_fundstellen()
    result.update(index.pruefe_persistierte_belege())
    after = _sha(source)
    if after != before:
        raise RuntimeError('Quellindex hat sich während der Migration geändert')
    manifest = {'source_sha256':before, 'target_sha256':_sha(dest), **result}
    (private_dir/'migration.json').write_text(json.dumps(manifest, indent=2))
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Legacy-Index in neue Kopie migrieren')
    parser.add_argument('--quelle', type=Path, required=True)
    parser.add_argument('--ziel', type=Path, required=True)
    args = parser.parse_args(argv)
    result = migriere_index_kopie(args.quelle, args.ziel)
    print(json.dumps({'migrated_chunks':result['migrated_chunks'],
                      'documents_without_chunks':len(result['documents_without_chunks'])}))


if __name__ == '__main__':
    main()

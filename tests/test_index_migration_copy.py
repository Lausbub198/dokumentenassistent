"""Migration works on a separate copy and keeps the original database intact."""
import hashlib
from pathlib import Path

from dokumentenassistent.index import Index
from dokumentenassistent.index_migration import migriere_index_kopie
from tests.test_M5_index import D, F


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_copy_migration_preserves_original_and_is_idempotent(tmp_path):
    source = tmp_path/'source'
    target = tmp_path/'target'
    ix = Index(source)
    ix.registriere(D, 'sicher')
    ix.speichere_fundstellen((F,))
    ix.markiere_bestaetigt(D.hash, Path('/approved/copy.pdf'))
    before = sha(source/'.dokumentenassistent/index.sqlite')
    result = migriere_index_kopie(source, target)
    assert result['migrated_chunks'] == 1
    assert sha(source/'.dokumentenassistent/index.sqlite') == before
    migrated = Index(target)
    assert migrated.fundstellen(D.hash)[0].id != F.id
    assert migrated.zielpfad(D.hash) == Path('/approved/copy.pdf')
    assert migrated.migriere_legacy_fundstellen()['migrated_chunks'] == 0

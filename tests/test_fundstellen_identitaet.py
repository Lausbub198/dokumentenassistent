"""Source identity is independent of a display filename."""
from pathlib import Path

from dokumentenassistent.fundstellen import zerlege
from dokumentenassistent.index import Index
from dokumentenassistent.typen import Datei, Seite


def doc(hash_, path, name='gleich.pdf'):
    return Datei(hash_, Path(path), name, 1)


def chunk(document, text):
    return zerlege(document, (Seite(1, text, False, None),))[0]


def test_equal_filenames_do_not_overwrite_different_documents(tmp_path):
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('b'*64, '/b/gleich.pdf')
    fa, fb = chunk(a, 'Betrag 10 EUR'), chunk(b, 'Betrag 20 EUR')
    assert fa.id != fb.id
    ix = Index(tmp_path)
    ix.registriere(a, 'unklar')
    ix.registriere(b, 'unklar')
    ix.ersetze_fundstellen(a.hash, (fa,))
    ix.ersetze_fundstellen(b.hash, (fb,))
    assert ix.fundstellen(a.hash) == (fa,)
    assert ix.fundstellen(b.hash) == (fb,)
    assert ix.fundstelle('gleich.pdf#S1#A1') is None  # ambiguous legacy alias


def test_same_bytes_at_two_paths_have_one_document_identity():
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('a'*64, '/b/anderer-name.pdf', 'anderer-name.pdf')
    assert chunk(a, 'Betrag 10 EUR').id == chunk(b, 'Betrag 10 EUR').id


def test_text_change_changes_identity_but_filename_unicode_does_not():
    a = doc('a'*64, '/a/Müller.pdf', 'Müller.pdf')
    b = doc('a'*64, '/a/Mu\u0308ller.pdf', 'Mu\u0308ller.pdf')
    assert chunk(a, 'Betrag 10 EUR').id == chunk(b, 'Betrag 10 EUR').id
    assert chunk(a, 'Betrag 10 EUR').id != chunk(a, 'Betrag 20 EUR').id


def test_unique_legacy_alias_resolves_only_to_matching_source(tmp_path):
    a = doc('a'*64, '/a/gleich.pdf')
    fa = chunk(a, 'Betrag 10 EUR')
    ix = Index(tmp_path)
    ix.registriere(a, 'unklar')
    ix.ersetze_fundstellen(a.hash, (fa,))
    assert ix.fundstelle('gleich.pdf#S1#A1') == fa
    assert ix.fundstelle('fremd.pdf#S1#A1') is None


def test_legacy_alias_rejects_second_registered_document_without_chunks(tmp_path):
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('b'*64, '/b/gleich.pdf')
    fa = chunk(a, 'Betrag 10 EUR')
    ix = Index(tmp_path)
    ix.registriere(a, 'unklar')
    ix.ersetze_fundstellen(a.hash, (fa,))
    ix.registriere(b, 'unklar')
    assert ix.fundstelle('gleich.pdf#S1#A1') is None
    assert ix.fundstelle(fa.id) == fa


def test_colliding_legacy_row_is_not_assigned_to_either_same_named_document(tmp_path):
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('b'*64, '/b/gleich.pdf')
    ix = Index(tmp_path)
    ix.registriere(a, 'unklar')
    ix.registriere(b, 'unklar')
    old = chunk(a, 'Betrag 10 EUR')
    from dataclasses import replace
    old = replace(old, id='gleich.pdf#S1#A1')
    ix.speichere_fundstellen((old,))
    assert ix.fundstelle(old.id) is None
    assert ix.fundstellen(a.hash) == (old,)


def test_explicit_legacy_migration_keeps_approval_and_flags_missing_collision(tmp_path):
    from dataclasses import replace
    from dokumentenassistent.typen import Beleg, Feld, Vorschlag
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('b'*64, '/b/gleich.pdf')
    ix = Index(tmp_path)
    ix.registriere(a, 'sicher')
    ix.registriere(b, 'unklar')
    old = replace(chunk(a, 'Betrag 10 EUR'), id='gleich.pdf#S1#A1')
    ix.speichere_fundstellen((old,))
    ix.speichere_vorschlag(Vorschlag(a.hash, a.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg(old.id, '10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    ix.markiere_bestaetigt(a.hash, tmp_path/'approved.pdf')
    first = ix.migriere_legacy_fundstellen()
    second = ix.migriere_legacy_fundstellen()
    assert first['migrated_chunks'] == 1
    assert second['migrated_chunks'] == 0
    assert b.hash in first['documents_without_chunks']
    current = ix.fundstellen(a.hash)[0]
    assert current.id != old.id
    assert ix.vorschlaege()[0].felder[0].beleg.fundstelle_id == current.id
    assert ix.zielpfad(a.hash) == tmp_path/'approved.pdf'
    assert ix.fundstelle(old.id) is None


def test_legacy_citation_rejected_when_globally_ambiguous_even_if_one_in_prompt():
    from dokumentenassistent.suche import _karten
    a, b = doc('a'*64, '/a/gleich.pdf'), doc('b'*64, '/b/gleich.pdf')
    fa, fb = chunk(a, 'Betrag 10 EUR'), chunk(b, 'Betrag 20 EUR')
    assert _karten('[gleich.pdf#S1#A1]', (fa,), alle_fundstellen=(fa, fb)) == ()
    assert _karten(f'[{fa.id}]', (fa,), alle_fundstellen=(fa, fb))[0].fundstelle.id == fa.id

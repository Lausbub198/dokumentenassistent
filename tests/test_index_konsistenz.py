"""Real SQLite regressions; all documents are synthetic."""
from dataclasses import replace
import sqlite3

import pytest

from dokumentenassistent.index import Index
from tests.test_M5_index import D, F
from dokumentenassistent.fundstellen import fundstellen_id
from dokumentenassistent.typen import Beleg, Feld, Vorschlag, Konflikt
from dokumentenassistent import typen


def prepared(tmp_path):
    ix = Index(tmp_path)
    ix.registriere(D, 'unklar')
    ix.speichere_fundstellen((F,))
    return ix


def save(ix, f=F, vector=None, revision='model@1'):
    ix.speichere_embeddings(((f.id, vector or [0.1, 0.2]),),
        modell_revision=revision, erwartete_texte={f.id: f.text})


def test_changed_text_invalidates_vector_atomically(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    changed = replace(F, text='Betrag 20 EUR')
    ix.speichere_fundstellen((changed,))
    assert ix.durchsuchbare_fundstellen() == ()
    assert ix.fundstellen_ohne_embedding() == (changed,)


def test_unchanged_text_reuses_vector_and_model_change_requires_embedding(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    ix.speichere_fundstellen((F,))
    assert ix.durchsuchbare_fundstellen(modell_revision='model@1') == ((F, [0.1, 0.2]),)
    assert ix.durchsuchbare_fundstellen(modell_revision='model@2') == ()
    assert ix.fundstellen_ohne_embedding(modell_revision='model@2') == (F,)
    assert ix.durchsuchbare_fundstellen(vorverarbeitung='prefix-v2') == ()


def test_stale_inflight_embedding_cannot_attach_to_changed_text(tmp_path):
    ix = prepared(tmp_path)
    ix.speichere_fundstellen((replace(F, text='Neu'),))
    with pytest.raises(ValueError, match='Text'):
        save(ix)
    assert not ix.durchsuchbare_fundstellen()


@pytest.mark.parametrize('bad', [[float('nan'), 0.1], [float('inf'), 1], [], [1], ['1', 2], [0, 0]])
def test_bad_batch_leaves_no_partial_vectors(tmp_path, bad):
    ix = prepared(tmp_path)
    other = replace(F, id='second', absatz=2)
    ix.speichere_fundstellen((other,))
    with pytest.raises(ValueError):
        ix.speichere_embeddings(((F.id, [0.1, 0.2]), (other.id, bad)),
            modell_revision='model@1', erwartete_texte={F.id:F.text, other.id:other.text})
    assert not ix.durchsuchbare_fundstellen()


def test_unknown_legacy_provenance_is_not_searchable(tmp_path):
    ix = prepared(tmp_path)
    ix._conn.execute('INSERT INTO embeddings(fundstelle_id,vektor) VALUES (?, ?)', (F.id, '[0.1, 0.2]'))
    ix._conn.commit()
    assert not ix.durchsuchbare_fundstellen()
    assert ix.fundstellen_ohne_embedding() == (F,)


def test_cross_document_id_collision_is_rejected_without_overwrite(tmp_path):
    ix = prepared(tmp_path)
    other = replace(D, hash='h2')
    ix.registriere(other, 'unklar')
    with pytest.raises(ValueError, match='Identität'):
        ix.speichere_fundstellen((replace(F, datei_hash='h2'),))
    assert ix.fundstellen(D.hash) == (F,)
    assert ix.fundstelle(F.id) is None  # duplicate display name is ambiguous


def test_complete_replacement_removes_old_chunks_and_vectors(tmp_path):
    ix = prepared(tmp_path)
    second = replace(F, id='a.pdf#S1#A2', absatz=2, text='Old second chunk')
    ix.speichere_fundstellen((second,))
    save(ix)
    save(ix, second)
    ix.ersetze_fundstellen(D.hash, (F,))
    assert ix.fundstellen(D.hash) == (F,)
    assert ix.fundstelle(second.id) is None
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)
    ix.ersetze_fundstellen(D.hash, (F,))
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)


def test_successfully_empty_document_removes_all_chunks(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    ix.ersetze_fundstellen(D.hash, ())
    assert ix.fundstellen(D.hash) == ()
    assert ix.durchsuchbare_fundstellen() == ()


def test_replacement_failure_rolls_back_deletion_and_embeddings(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    other = replace(F, id='a.pdf#S2#A1', seite=2)
    ix._conn.execute("CREATE TRIGGER deny_insert BEFORE INSERT ON fundstellen "
                     "WHEN NEW.id='a.pdf#S2#A1' BEGIN SELECT RAISE(ABORT,'blocked'); END")
    ix._conn.commit()
    with pytest.raises(sqlite3.DatabaseError):
        ix.ersetze_fundstellen(D.hash, (other,))
    assert ix.fundstellen(D.hash) == (F,)
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)


def test_replacement_rejects_another_document_before_deletion(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    with pytest.raises(ValueError):
        ix.ersetze_fundstellen(D.hash, (replace(F, datei_hash='other'),))
    assert ix.fundstellen(D.hash) == (F,)


def test_unchanged_legacy_evidence_moves_to_new_id_and_keeps_approval(tmp_path):
    ix = prepared(tmp_path)
    ix.speichere_vorschlag(Vorschlag(D.hash, D.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg(F.id, '10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    ix.markiere_bestaetigt(D.hash, tmp_path/'approved.pdf')
    new = replace(F, id=fundstellen_id(F.datei_hash, F.seite, F.absatz, F.text))
    ix.ersetze_fundstellen(D.hash, (new,))
    assert ix.vorschlaege()[0].felder[0].beleg.fundstelle_id == new.id
    assert ix.vorschlaege()[0].status == 'sicher'
    assert ix.zielpfad(D.hash) == tmp_path/'approved.pdf'


def test_legacy_evidence_transfer_uses_quote_normalization(tmp_path):
    ix = prepared(tmp_path)
    old = replace(F, text='„Miete“\n  10 EUR')
    ix.speichere_fundstellen((old,))
    ix.speichere_vorschlag(Vorschlag(D.hash, D.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg(old.id, '"Miete" 10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    ix.markiere_bestaetigt(D.hash, tmp_path/'approved.pdf')
    new = replace(old, id=fundstellen_id(old.datei_hash, old.seite, old.absatz, old.text))
    ix.ersetze_fundstellen(D.hash, (new,))
    field = ix.vorschlaege()[0].felder[0]
    assert field.status == 'belegt'
    assert field.beleg.fundstelle_id == new.id
    assert ix.zielpfad(D.hash) == tmp_path/'approved.pdf'


def test_changed_legacy_evidence_is_unclear_but_approval_kept(tmp_path):
    ix = prepared(tmp_path)
    ix.speichere_vorschlag(Vorschlag(D.hash, D.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg(F.id, '10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    ix.markiere_bestaetigt(D.hash, tmp_path/'approved.pdf')
    new = replace(F, id=fundstellen_id(F.datei_hash, 1, 1, '20 EUR'), text='20 EUR')
    ix.ersetze_fundstellen(D.hash, (new,))
    assert ix.vorschlaege()[0].felder[0].status == 'unklar'
    assert ix.vorschlaege()[0].status == 'unklar'
    assert ix.zielpfad(D.hash) == tmp_path/'approved.pdf'


def test_conflict_evidence_transfer_requires_owner_and_text_match(tmp_path):
    ix = prepared(tmp_path)
    ix.speichere_konflikt(Konflikt('k', 'betrag', D.hash, 'other', '10', '20',
        Beleg(F.id, '10 EUR'), Beleg(F.id, '10 EUR'), 'nicht_entscheidbar'))
    new = replace(F, id=fundstellen_id(F.datei_hash, 1, 1, F.text))
    ix.ersetze_fundstellen(D.hash, (new,))
    conflict = ix.konflikte()[0]
    assert conflict.beleg_a.fundstelle_id == new.id
    assert conflict.beleg_b.fundstelle_id == F.id  # different owner, not reassigned


def test_extraction_version_saved_with_replaced_document(tmp_path):
    ix = prepared(tmp_path)
    ix.ersetze_fundstellen(D.hash, (F,), extraktion=((1, 'pdftotext', '26.04.0'),))
    assert ix.ausleseprotokoll(D.hash) == ((1, 'pdftotext', '26.04.0'),)
    ix.ersetze_fundstellen(D.hash, (), extraktion=())
    assert ix.ausleseprotokoll(D.hash) == ()


def test_legacy_id_from_collided_name_does_not_keep_other_document_proven(tmp_path):
    ix = prepared(tmp_path)
    other = replace(D, hash='h2', pfad=D.pfad.parent/'copy/a.pdf')
    ix.registriere(other, 'sicher')
    ix.speichere_vorschlag(Vorschlag(other.hash, other.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg(F.id, '10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    new = replace(F, id=fundstellen_id(F.datei_hash, 1, 1, F.text))
    ix.ersetze_fundstellen(D.hash, (new,))
    proposal=ix.vorschlaege()[0]
    assert proposal.datei_hash == other.hash
    assert proposal.felder[0].status == 'unklar'
    assert proposal.status == 'unklar'


def test_evidence_audit_downgrades_orphan_but_keeps_approved_copy(tmp_path):
    ix = prepared(tmp_path)
    ix.markiere_bestaetigt(D.hash, tmp_path/'approved.pdf')
    ix.speichere_vorschlag(Vorschlag(D.hash, D.name, 'K', 'T',
        (Feld('betrag', '10 EUR', Beleg('missing', '10 EUR'), 'belegt'),), 'z.pdf', 'sicher'))
    result=ix.pruefe_persistierte_belege()
    assert result['downgraded_fields'] == 1
    assert ix.vorschlaege()[0].felder[0].status == 'unklar'
    assert ix.zielpfad(D.hash) == tmp_path/'approved.pdf'


def test_cross_page_spans_roundtrip_through_every_index_read_path(tmp_path):
    assert hasattr(typen, 'SeitenSpanne')
    text = 'Betrag 10 EUR'
    first = typen.SeitenSpanne(1, 0, 7)
    second = typen.SeitenSpanne(2, 7, len(text))
    source = replace(F, spannen=(first, second))
    ix = Index(tmp_path)
    ix.registriere(D, 'unklar')
    ix.ersetze_fundstellen(D.hash, (source,))
    assert ix.fundstellen(D.hash) == (source,)
    assert ix.fundstelle(F.id) == source
    assert ix.fundstellen_ohne_embedding() == (source,)
    save(ix)
    assert ix.durchsuchbare_fundstellen() == ((source, [0.1, 0.2]),)
    assert source.seiten == (1, 2)


def test_invalid_page_spans_roll_back_replacement_and_vector(tmp_path):
    assert hasattr(typen, 'SeitenSpanne')
    ix = prepared(tmp_path)
    save(ix)
    invalid = replace(F, spannen=(typen.SeitenSpanne(1, 0, len(F.text)+1),))
    with pytest.raises(ValueError, match='Seiten'):
        ix.ersetze_fundstellen(D.hash, (invalid,))
    assert ix.fundstellen(D.hash) == (F,)
    assert ix.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)


def test_corrected_page_spans_do_not_invalidate_unchanged_text_vector(tmp_path):
    assert hasattr(typen, 'SeitenSpanne')
    ix = prepared(tmp_path)
    save(ix)
    corrected = replace(F, spannen=(typen.SeitenSpanne(1, 0, 7),
                                    typen.SeitenSpanne(2, 7, len(F.text))))
    ix.ersetze_fundstellen(D.hash, (corrected,))
    assert ix.durchsuchbare_fundstellen() == ((corrected, [0.1, 0.2]),)


def test_legacy_index_without_page_span_column_keeps_citation_and_vector(tmp_path):
    ix = prepared(tmp_path)
    save(ix)
    ix._conn.close()
    with sqlite3.connect(tmp_path/'.dokumentenassistent/index.sqlite') as db:
        columns = {row[1] for row in db.execute('PRAGMA table_info(fundstellen)')}
        assert 'spannen' in columns
        db.execute('ALTER TABLE fundstellen DROP COLUMN spannen')
    migrated = Index(tmp_path)
    assert migrated.fundstelle(F.id) == F
    assert migrated.fundstelle(F.id).seiten == (1,)
    assert migrated.durchsuchbare_fundstellen() == ((F, [0.1, 0.2]),)

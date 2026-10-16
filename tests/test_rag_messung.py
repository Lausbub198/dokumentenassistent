"""Measurement gates and resume protection must not silently accept partial data."""
import pytest


def test_duplicate_question_ids_are_rejected():
    from dokumentenassistent.rag_folgeschritte import validiere_fragen
    with pytest.raises(ValueError):
        validiere_fragen([{'nr':1}, {'nr':1}], 2)


def test_missing_question_is_rejected():
    from dokumentenassistent.rag_folgeschritte import validiere_fragen
    with pytest.raises(ValueError):
        validiere_fragen([{'nr':1}], 2)


@pytest.mark.parametrize('wins,losses,want', [(6,1,True),(5,1,False),(9,3,False),(0,0,False)])
def test_gate_checks_net_effect_and_regressions(wins, losses, want):
    from dokumentenassistent.rag_folgeschritte import pruefe_gate
    assert pruefe_gate(wins, losses) is want


def test_resume_rejects_different_manifest(tmp_path):
    from dokumentenassistent.rag_folgeschritte import lade_checkpoint
    p=tmp_path/'rows.jsonl'
    p.write_text('{"key":"12:A","manifest":"old"}\n')
    with pytest.raises(ValueError):
        lade_checkpoint(p, 'new')


def test_resume_rejects_duplicate_results(tmp_path):
    from dokumentenassistent.rag_folgeschritte import lade_checkpoint
    p=tmp_path/'rows.jsonl'
    p.write_text('{"key":"12:A","manifest":"a"}\n'*2)
    with pytest.raises(ValueError):
        lade_checkpoint(p, 'a')


def test_resume_accepts_valid_results(tmp_path):
    from dokumentenassistent.rag_folgeschritte import lade_checkpoint
    p=tmp_path/'rows.jsonl'
    p.write_text('{"key":"12:A","manifest":"a","count":2}\n')
    assert lade_checkpoint(p, 'a')['12:A']['count']==2


def test_cache_provenance_rejects_reordered_ids():
    from dokumentenassistent.rag_folgeschritte import validiere_cache_provenienz
    with pytest.raises(ValueError):
        validiere_cache_provenienz({'cache_sha256':'a','gold_sha256':'g','query_ids':[2,1],
                                   'embedding_model':'m'}, 'a','g',[1,2],'m')


def test_cache_provenance_rejects_changed_vectors():
    from dokumentenassistent.rag_folgeschritte import validiere_cache_provenienz
    with pytest.raises(ValueError):
        validiere_cache_provenienz({'cache_sha256':'a','gold_sha256':'g','query_ids':[1],
                                   'embedding_model':'m'}, 'changed','g',[1],'m')


def test_context_integrity_rejects_other_chunk():
    from dokumentenassistent.rag_folgeschritte import validiere_kontext, digest
    from tests.conftest import fs
    chunks=[fs('A#S1#A1','a'),fs('B#S1#A1','b')]
    with pytest.raises(ValueError):
        validiere_kontext([1],chunks,{'context_count':1,'context_hash':digest(['A#S1#A1'])})


@pytest.mark.parametrize('response', [ {'response':'null'}, {'response':'[]'}, {'response':'bad'},
                                      {'response':'{"antwortstuetzung":"supported"}'} ])
def test_invalid_judge_result_stays_unverified(response):
    from dokumentenassistent.rag_folgeschritte import prueferurteil
    result=prueferurteil(response)
    assert result['antwortstuetzung']=='ungeprueft'
    assert result['pruefstatus']=='fehler'


@pytest.mark.parametrize('text', ['null','[]','{"provenance":{"x":2},"response":{}}'])
def test_corrupt_judge_envelope_rejected(tmp_path,text):
    from dokumentenassistent.rag_folgeschritte import lade_pruefercache
    p=tmp_path/'judge.json';p.write_text(text)
    with pytest.raises(ValueError):
        lade_pruefercache(p,{'x':1})


def test_valid_cache_context_and_judge_are_accepted(tmp_path):
    from dokumentenassistent.rag_folgeschritte import validiere_cache_provenienz,validiere_kontext,prueferurteil,digest
    from tests.conftest import fs
    validiere_cache_provenienz({'cache_sha256':'a','gold_sha256':'g','query_ids':[1],'embedding_model':'m'},'a','g',[1],'m')
    validiere_kontext([0],[fs('A#S1#A1','a')],{'context_count':1,'context_hash':digest(['A#S1#A1'])})
    assert prueferurteil({'response':'{"quellen_ausreichend":"ja","antwort_beantwortet_frage":"ja","antwortstuetzung":"unterstuetzt"}'})['pruefstatus']=='modellurteil'

"""Document scoped candidate pool, independent of answer context size."""
from dokumentenassistent.retrieval_dokumente import kandidaten_aus_dokumenten
from tests.conftest import fs


def test_document_scope_recovers_late_chunk_without_displacing_original_top20():
    sources = [fs(f'A#S1#A{i}', f'A {i}', datei='A') for i in range(1, 4)]
    sources += [fs(f'B#S1#A{i}', f'B {i}', datei='B') for i in range(1, 72)]
    ranked = tuple((f.id, 1.0-i/100) for i,f in enumerate(sources))
    # A is discovered at rank 1; its last chunk is deliberately moved far back.
    ranked = ranked[:2] + ranked[3:] + ranked[2:3]
    by_id = {f.id:f for f in sources}
    pool = kandidaten_aus_dokumenten(ranked, by_id, initial=20, docs=1, cap=50)
    assert [fid for fid,_ in ranked[:20]] == [fid for fid,_ in pool[:20]]
    assert sources[2].id in {fid for fid,_ in pool}
    assert len(pool) <= 50


def test_scope_keeps_unique_candidates_and_never_adds_unknown_sources():
    a=fs('a','A',datei='A')
    b=fs('b','B',datei='B')
    ranked=(('a',.9),('b',.8),('a',.7),('ghost',.6))
    pool=kandidaten_aus_dokumenten(ranked,{'a':a,'b':b},initial=2,docs=2,cap=3)
    assert [id_ for id_,_ in pool] == ['a','b']


def test_optional_search_recovers_same_document_late_chunk_with_20_context_slots():
    import math
    from dokumentenassistent.suche import suche
    from tests.conftest import FakeProvider
    early=fs('early','generic',datei='A')
    others=[fs(f'other{i}','generic',datei=f'B{i}') for i in range(1,49)]
    target=fs('target','Target fact',datei='A',absatz=2)
    sources=[early,*others,target]
    values=[.99-i*.01 for i in range(len(sources))]
    pairs=tuple((f,[v,math.sqrt(1-v*v)]) for f,v in zip(sources,values))
    class TargetReranker:
        def bewerte(self, question, texts):
            return [100.0 if text=='Target fact' else 0.0 for text in texts]
    provider=FakeProvider(text_antworten=['Fact [target]'])
    provider.embed=lambda texts:[[1.0,0.0]]
    result=suche('Fact?',pairs,provider,reranker=TargetReranker(),rerank_k=20,
                 top_n=20,dokument_scope=True)
    assert result.status=='gefunden'
    assert result.karten[0].fundstelle.id=='target'
    prompt=next(value for kind,value in provider.aufrufe if kind=='text')
    assert prompt.count(']\n')==20

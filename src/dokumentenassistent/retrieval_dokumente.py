"""Optional document-scoped second pass using the already computed query ranking."""
from __future__ import annotations

from dokumentenassistent.typen import Fundstelle


def kandidaten_aus_dokumenten(
    rangliste: tuple[tuple[str, float], ...],
    fundstellen: dict[str, Fundstelle],
    *, initial: int = 20, docs: int = 5, cap: int = 50,
) -> tuple[tuple[str, float], ...]:
    """Keep dense top-20, then add chunks from its first five distinct documents.

    The global dense list already scores every chunk for the same question. Restrict
    its tail to those documents and hand at most 50 candidates to the reranker.
    """
    if initial < 1 or docs < 1 or cap < initial:
        raise ValueError('Ungültige Kandidatenlimits')
    first = []
    seen = set()
    document_hashes = []
    for fid, score in rangliste:
        if fid not in fundstellen or fid in seen:
            continue
        if len(first) < initial:
            first.append((fid, score))
            seen.add(fid)
            document_hash = fundstellen[fid].datei_hash
            if document_hash not in document_hashes and len(document_hashes) < docs:
                document_hashes.append(document_hash)
        else:
            break
    selected = set(document_hashes)
    for fid, score in rangliste:
        if len(first) >= cap:
            break
        if fid in seen or fid not in fundstellen:
            continue
        if fundstellen[fid].datei_hash in selected:
            first.append((fid, score))
            seen.add(fid)
    return tuple(first)

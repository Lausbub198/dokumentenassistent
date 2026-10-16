"""Synthetic regressions: grouped sources are not semantic verification."""
import pytest

from dokumentenassistent.suche import _karten
from dokumentenassistent.typen import Antwort
from tests.conftest import fs

A = fs('A, Rechnung.pdf#S1#A1', 'Betrag 12,50 EUR', datei='A, Rechnung.pdf')
B = fs('B.pdf#S2#A1', 'Keine Zahlung vereinbart.', datei='B.pdf')


@pytest.mark.parametrize('text, expected', [
    (f'[{A.id}, {B.id}]', [A.id, B.id]),
    (f'[{A.id}] [{B.id}]', [A.id, B.id]),
    (f'[{A.id}, {A.id}]', [A.id]),
    (f'[{A.id}, unbekannt.pdf#S1#A1]', []),
    (f'[{A.id} Zusatz]', []),
    (f'[[{A.id}]]', []),
    (A.id, []),
])
def test_grouped_citations_are_exact_and_fail_closed(text, expected):
    assert [k.fundstelle.id for k in _karten(text, (A, B))] == expected


def test_outside_context_source_rejected():
    assert not _karten(f'[{A.id}, {B.id}]', (A,))


def test_ambiguous_filename_or_group_is_rejected():
    combined = fs(f'{A.id}, {B.id}', 'Ambiguous filename')
    assert not _karten(f'[{A.id}, {B.id}]', (A, B, combined))


def test_formally_valid_wrong_evidence_stays_unverified():
    from dokumentenassistent.antwort_eval import bewerte_antwort
    answer = Antwort('gefunden', f'99 EUR [{A.id}, {B.id}]', _karten(f'[{A.id}, {B.id}]', (A, B)))
    result = bewerte_antwort(answer, 'C.pdf', '99 EUR')
    assert result['quellen_id_gueltig'] is True
    assert result['zieldatei_getroffen'] is False
    assert result['beleg_exakt'] is False
    assert result['antwortstuetzung'] == 'ungeprueft'
    assert result['pruefverfahren'] == 'keine_semantische_pruefung'


def test_whitespace_eval_does_not_change_historical_metric():
    from dokumentenassistent.antwort_eval import bewerte_antwort
    source = fs('A.pdf#S1#A1', 'Summe 12,50\nEUR', datei='A.pdf')
    answer = Antwort('gefunden', f'12,50 EUR [{source.id}]', _karten(f'[{source.id}]', (source,)))
    result = bewerte_antwort(answer, 'A.pdf', '12,50 EUR')
    assert result['beleg_exakt'] is False
    assert result['beleg_whitespace'] is True
    assert result['antwortstuetzung'] == 'ungeprueft'


@pytest.mark.parametrize('actual, expected', [
    ('12,50 EUR', '1250 EUR'), ('-12,50 EUR', '12,50 EUR'),
    ('12.05.2026', '12.06.2026'), ('nicht bezahlt', 'bezahlt'),
])
def test_normalization_does_not_erase_meaning(actual, expected):
    from dokumentenassistent.antwort_eval import normalisiere_whitespace
    assert normalisiere_whitespace(actual) != normalisiere_whitespace(expected)


def test_ui_links_grouped_sources_and_escapes_text():
    from dokumentenassistent.web import antwort_html
    text = f'<script>alert(1)</script> [{A.id}, {B.id}]'
    html = str(antwort_html(text, _karten(text, (A, B))))
    assert 'href="#beleg-1"' in html and 'href="#beleg-2"' in html
    assert '<script>' not in html


def test_answer_serialization_keeps_support_separate():
    from dataclasses import asdict
    answer = Antwort('gefunden', f'99 EUR [{A.id}]', _karten(f'[{A.id}]', (A,)))
    data = asdict(answer)
    assert data['status'] == 'gefunden'
    assert data['stuetzung']['status'] == 'ungeprueft'


def test_support_claim_requires_documented_method():
    from dokumentenassistent.typen import Stuetzungspruefung
    with pytest.raises(ValueError):
        Stuetzungspruefung(status='unterstuetzt')
    assert Stuetzungspruefung(status='widersprochen', verfahren='manuelle_pruefung').status == 'widersprochen'


def test_target_indices_distinguishes_answer_value_from_supporting_paragraph():
    from dokumentenassistent.rag_folgeschritte import target_indices
    wrong = fs('wrong', '21 Stellplätze', datei='Teilung.pdf')
    right = fs('right', 'Im Haus B werden 21 Eigentumswohnungen entstehen.', datei='Teilung.pdf')
    gold = {'datei': 'Teilung.pdf', 'wortlaut_enthaelt': '21',
            'zielabsatz': 'Im Haus B werden 21 Eigentumswohnungen entstehen.'}
    assert target_indices(gold, [wrong, right], 'whitespace') == [0, 1]
    assert target_indices(gold, [wrong, right], 'paragraph') == [1]

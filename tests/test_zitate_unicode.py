"""Canonical spelling may change; source identity and offsets may not."""
import pytest

from dokumentenassistent.suche import _karten
from dokumentenassistent.zitate import zitatgruppen
from tests.conftest import fs


@pytest.mark.parametrize('stored,cited', [
    ('Mu\u0308ller.pdf#S1#A1', 'Müller.pdf#S1#A1'),
    ('Müller.pdf#S1#A1', 'Mu\u0308ller.pdf#S1#A1'),
])
def test_unicode_spelling_resolves_original_source_and_preserves_offsets(stored, cited):
    source = fs(stored, '12,50 EUR')
    text = f'Betrag [{cited}]. Danach.'
    cards = _karten(text, (source,))
    assert len(cards) == 1
    assert cards[0].fundstelle is source
    start, end, ids = next(zitatgruppen(text, [stored]))
    assert text[start:end] == f'[{cited}]'
    assert ids == (stored,)


def test_canonical_collision_rejects_even_exact_spelling():
    assert not list(zitatgruppen('[Müller.pdf#S1#A1]', [
        'Müller.pdf#S1#A1', 'Mu\u0308ller.pdf#S1#A1',
    ]))


def test_unicode_group_with_comma_filename_preserves_identity():
    stored = 'Mu\u0308ller, Rechnung.pdf#S1#A1'
    assert list(zitatgruppen('[Müller, Rechnung.pdf#S1#A1, B]', [stored, 'B']))[0][2] == (stored, 'B')


def test_unicode_does_not_admit_outside_context_or_unknown_group_member():
    assert not list(zitatgruppen('[Müller.pdf#S1#A1]', ['B']))
    assert not list(zitatgruppen('[Müller.pdf#S1#A1, unbekannt]', ['Mu\u0308ller.pdf#S1#A1']))

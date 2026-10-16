import dataclasses
from pathlib import Path

import pytest

from dokumentenassistent.typen import Datei


def test_M0_G1_datei_ist_unveraenderlich():
    d = Datei(hash="a", pfad=Path("x.pdf"), name="x.pdf", groesse=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.name = "y.pdf"


def test_M0_G2_fake_provider_embed_ist_deterministisch(fake_provider):
    p = fake_provider()
    assert p.embed(["Heizung Nord"]) == p.embed(["Heizung Nord"])

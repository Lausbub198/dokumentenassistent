"""Test-Infrastruktur für alle Stufen. Eingefroren — Änderungen nur durch den Orchestrator."""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.pdfgen import canvas

from dokumentenassistent.typen import Fundstelle


class FakeProvider:
    """Deterministischer Ersatz für Ollama.

    embed = Bag-of-Words-Hash-Vektor (normalisiert), generate_json/generate_text
    liefern vorher eingereihte Antworten. Eine eingereihte Exception wird geworfen.
    """

    def __init__(self, json_antworten=None, text_antworten=None, dim: int = 64):
        self.json_antworten = list(json_antworten or [])
        self.text_antworten = list(text_antworten or [])
        self.dim = dim
        self.aufrufe: list[tuple[str, str]] = []

    def embed(self, texte: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texte:
            v = [0.0] * self.dim
            for w in re.findall(r"\w+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

    def embedding_revision(self) -> str:
        return f'synthetic-bow-md5-v1-dim{self.dim}'

    def generate_json(self, prompt: str, schema: dict) -> dict:
        self.aufrufe.append(("json", prompt))
        if not self.json_antworten:
            raise AssertionError("FakeProvider: keine JSON-Antwort eingereiht")
        antwort = self.json_antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort

    def generate_text(self, prompt: str) -> str:
        self.aufrufe.append(("text", prompt))
        if not self.text_antworten:
            raise AssertionError("FakeProvider: keine Text-Antwort eingereiht")
        antwort = self.text_antworten.pop(0)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort


@pytest.fixture
def fake_provider():
    return FakeProvider


def schreibe_text_pdf(pfad: Path, seiten: list[str]) -> Path:
    c = canvas.Canvas(str(pfad))
    for text in seiten:
        y = 800
        for zeile in text.split("\n"):
            c.drawString(50, y, zeile)
            y -= 16
        c.showPage()
    c.save()
    return pfad


def schreibe_bild(pfad: Path, text: str, unscharf: bool = False) -> Path:
    img = Image.new("RGB", (1200, 400), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 150), text, fill="black", font=ImageFont.load_default(size=40))
    if unscharf:
        img = img.rotate(12, fillcolor="white").filter(ImageFilter.GaussianBlur(4))
    img.save(pfad)
    return pfad


def schreibe_bild_pdf(pfad: Path, text: str, unscharf: bool = False) -> Path:
    png = pfad.with_suffix(".png")
    schreibe_bild(png, text, unscharf)
    Image.open(png).convert("RGB").save(pfad, "PDF")
    png.unlink()
    return pfad


@pytest.fixture
def text_pdf(tmp_path):
    return schreibe_text_pdf(
        tmp_path / "Rechnung (2).pdf",
        [
            "Rechnung Nr. 2025-0815\nHeizung Sanitär Krause GmbH\nRechnungsbetrag 1.240,00 EUR\n"
            "Leistung: Reparatur Heizung, Musterstraße 3, Wohnung Nord",
            "Seite 2\nZahlbar bis 30.06.2025",
        ],
    )


@pytest.fixture
def bild_pdf(tmp_path):
    return schreibe_bild_pdf(tmp_path / "Scan_0043.pdf", "Rechnung Nr. 2025-0815 Betrag 1.240,00 EUR")


@pytest.fixture
def unscharfes_bild(tmp_path):
    return schreibe_bild(tmp_path / "IMG_8831.jpg", "Quittung 17,90 EUR", unscharf=True)


def fs(id_: str, text: str, datei: str = "Rechnung (2).pdf", seite: int = 1, absatz: int = 1) -> Fundstelle:
    return Fundstelle(id=id_, datei_hash="h_" + datei, datei_name=datei, seite=seite, absatz=absatz, text=text)


@pytest.fixture
def fundstellen_rechnung():
    return {
        "Rechnung (2).pdf#S1#A1": fs("Rechnung (2).pdf#S1#A1", "Rechnung Nr. 2025-0815"),
        "Rechnung (2).pdf#S1#A3": fs("Rechnung (2).pdf#S1#A3", "Rechnungsbetrag 1.240,00 EUR", absatz=3),
        "Rechnung (2).pdf#S2#A1": fs("Rechnung (2).pdf#S2#A1", "Zahlbar bis 30.06.2025", seite=2),
    }

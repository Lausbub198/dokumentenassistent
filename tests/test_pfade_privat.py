"""Private Messdaten haben keinen festen Ort im Repo — nur Umgebungsvariablen."""
import importlib
import subprocess
from pathlib import Path

from dokumentenassistent import pfade_privat


def test_standard_liegt_unter_dem_home_ordner(monkeypatch):
    for name in ("DOKASS_BESTAND", "DOKASS_ARBEIT", "DOKASS_FRAGEN", "DOKASS_LAEUFE", "DOKASS_GERMANQUAD"):
        monkeypatch.delenv(name, raising=False)
    neu = importlib.reload(pfade_privat)
    assert neu.FRAGEN == Path.home() / "dokass-privat" / "fragen"


def test_umgebungsvariable_gewinnt(monkeypatch, tmp_path):
    monkeypatch.setenv("DOKASS_LAEUFE", str(tmp_path))
    assert importlib.reload(pfade_privat).LAEUFE == tmp_path


def test_im_repo_steht_kein_fester_privater_pfad():
    wurzel = Path(__file__).resolve().parent.parent
    treffer = subprocess.run(
        ["git", "grep", "-l", "-i", "-E", "Mietwohnungen|/Users/[a-z0-9]+/", "--", "src", "scripts", "docs", "modelle.yaml", "beweise", ":!scripts/veroeffentlichen.sh"],
        cwd=wurzel, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert treffer == []


def test_in_den_messdaten_stehen_keine_echten_dateinamen():
    """Die OCR-Protokolle nannten einmal reale Dateien eines privaten Bestands; jetzt nur noch datei-NNN."""
    wurzel = Path(__file__).resolve().parent.parent
    treffer = subprocess.run(
        ["git", "grep", "-l", "-i", "-E", "N(ü|ue)renberg|SEPA_Mandat|Selbstauskunft|Zeichnungsschein",
         "--", "beweise", "docs", ":!*.arrow"],
        cwd=wurzel, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert treffer == []

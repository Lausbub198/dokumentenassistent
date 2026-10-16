"""Stufe 3 · Gesamttest — E1–E12 gegen echten Ollama und den echten Beispielkorpus.

Läuft nur mit Marker::

    uv run pytest -m e2e -v -s

Ein Session-Fixture (`lauf`) fährt den vollen Nutzerfluss EINMAL:
erfassen → auslesen → Profil vorschlagen/bestätigen → einordnen →
Konflikt entscheiden ("ersetzt") → freigeben → fragen. Alle Tests lesen nur
dieses Ergebnis, damit die Aufnahme später denselben Pfad zeigt.

Der Korpus wird nach `tmp_path_factory` kopiert; `beispiele/steuerfall/Quelle`
im Repo wird nie angefasst (E7 prüft das über SHA-256 vor/nach dem Lauf).

Nichts wird übersprungen: fehlt Ollama oder ein Modell, schlägt E1 fehl.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from dokumentenassistent.provider import (lade_modelle, lade_ocr_einstellungen, lade_provider_suche,
                                          lade_seitenuebergreifend, lade_sucheinstellungen)
from dokumentenassistent.typen import Antwort, Datei, Konflikt, Profil, Vorschlag
from dokumentenassistent.werkstatt import Werkstatt
from dokumentenassistent.zitatpruefung import pruefe_beleg

REPO = Path(__file__).resolve().parent.parent
MODELLE_YAML = REPO / "modelle.yaml"
KORPUS = REPO / "beispiele" / "steuerfall" / "Quelle"
GOLDEN: dict = json.loads((REPO / "tests" / "golden.json").read_text(encoding="utf-8"))
KONFIG: dict = yaml.safe_load(MODELLE_YAML.read_text())
HOST: str = KONFIG["host"]

# think: false steht seit 19.09. in modelle.yaml (Befund: Ollama 0.34 + qwen3.5:9b legt bei
# think:low die Antwort ins Feld `thinking`); provider.py meldet den Fall inzwischen klar.


class Protokollierender:
    """Zählt Modellaufrufe und Modellzeit. Delegiert an den echten Provider."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.zaehler: dict[str, int] = {"embed": 0, "generate_json": 0, "generate_text": 0}
        self.sekunden: dict[str, float] = {"embed": 0.0, "generate_json": 0.0, "generate_text": 0.0}

    def _messe(self, art: str, fn, *args):
        start = time.perf_counter()
        try:
            return fn(*args)
        finally:
            self.zaehler[art] += 1
            self.sekunden[art] += time.perf_counter() - start

    def embed(self, texte: list[str]) -> list[list[float]]:
        return self._messe("embed", self.inner.embed, texte)

    def generate_json(self, prompt: str, schema: dict) -> dict:
        return self._messe("generate_json", self.inner.generate_json, prompt, schema)

    def generate_text(self, prompt: str) -> str:
        return self._messe("generate_text", self.inner.generate_text, prompt)

    def __getattr__(self, name: str):
        """Alles Übrige (embedding_revision, llm_modell, …) unverändert vom echten Provider —
        sonst bricht der Lauf an jeder Provider-Erweiterung (06.10.: embedding_revision)."""
        return getattr(self.inner, name)


@dataclasses.dataclass
class Lauf:
    """Alles, was der eine echte Lauf hergegeben hat."""

    werkstatt: Werkstatt
    provider: Protokollierender
    quelle: Path
    zielablage: Path
    dateien: tuple[Datei, ...]
    duplikate: tuple[str, ...]
    profil: Profil
    vorschlaege: dict[str, Vorschlag]
    konflikte: tuple[Konflikt, ...]
    entscheidung: Konflikt | None
    freigegeben: tuple[Path, ...]
    antworten: dict[str, Antwort]
    quelle_vorher: dict[str, str]
    quelle_nachher: dict[str, str]
    korpus_vorher: dict[str, str]
    korpus_nachher: dict[str, str]
    phasen: dict[str, float]
    zweiter_lauf: dict[str, list]
    beweise: Path

    def status(self, name: str) -> str | None:
        """Ist-Status wie nach `einordnen()` — Duplikate haben keinen Vorschlag."""
        if name in self.duplikate:
            return "duplikat"
        vorschlag = self.vorschlaege.get(name)
        return None if vorschlag is None else vorschlag.status

    def antwort(self, nr: int) -> Antwort:
        return self.antworten[GOLDEN["fragen"][nr]["frage"]]


# ------------------------------------------------------------------ Hilfsmittel


def _hashes(ordner: Path) -> dict[str, str]:
    return {
        str(p.relative_to(ordner)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(ordner.rglob("*"))
        if p.is_file() and not any(t.startswith(".") for t in p.relative_to(ordner).parts)
    }


def _tags() -> list[str]:
    """Modellnamen aus /api/tags. Nicht erreichbar → Test fällt, kein Skip."""
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=15) as antwort:
            return [m["name"] for m in json.loads(antwort.read()).get("models", [])]
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError) as fehler:
        pytest.fail(f"Ollama nicht erreichbar unter {HOST} — Ollama starten. ({fehler})")


def _geladen(modell: str, tags: list[str]) -> bool:
    """Ollama führt `bge-m3` als `bge-m3:latest`; beide Schreibweisen gelten."""
    return modell in tags or f"{modell}:latest" in tags or modell.removesuffix(":latest") in tags


def _provider() -> Protokollierender:
    inner = lade_modelle(MODELLE_YAML)
    inner.timeout = 600
    return Protokollierender(inner)


@contextmanager
def _phase(phasen: dict[str, float], name: str):
    start = time.perf_counter()
    yield
    phasen[name] = time.perf_counter() - start
    print(f"  [Phase] {name}: {phasen[name]:.1f}s")


def _als_dict(objekt) -> dict:
    return json.loads(json.dumps(dataclasses.asdict(objekt), default=str, ensure_ascii=False))


# --------------------------------------------------------------------- Der Lauf


def _baue_werkstatt(basis: Path, marke: str, provider) -> Werkstatt:
    """Wie web.py und mcp_server.py: alle Such-, OCR- und Chunk-Einstellungen aus modelle.yaml.
    Ohne sie lief der Gesamttest bis 06.10.2026 mit den Werkstatt-Standards (kein Reranker, keine
    Kaskade, Schwelle 0,49) — also nicht mit dem Produkt; E8 scheiterte am 4B-Embedding an der
    0,6B-Schwelle (bester Kosinus 0,461 auf der richtigen Rechnung)."""
    quelle = basis / f"quelle_{marke}"
    if not quelle.exists():
        shutil.copytree(KORPUS, quelle)
    return Werkstatt(
        quelle=quelle,
        zielablage=basis / f"ablage_{marke}",
        provider=provider,
        provider_suche=lade_provider_suche(MODELLE_YAML),
        sucheinstellungen=lade_sucheinstellungen(MODELLE_YAML),
        ocr=lade_ocr_einstellungen(MODELLE_YAML),
        seitenuebergreifend=lade_seitenuebergreifend(MODELLE_YAML),
        arbeitsordner=basis / f"arbeit_{marke}",
    )


def _erster_lauf(w: Werkstatt, phasen: dict[str, float]) -> dict:
    """erfassen → auslesen → Profil → einordnen → Konflikt → freigeben → fragen."""
    with _phase(phasen, "erfassen"):
        dateien = w.erfassen()
    with _phase(phasen, "auslesen"):
        w.auslesen()
    with _phase(phasen, "profil_vorschlagen"):
        profil = w.profil_vorschlagen(GOLDEN["zweck"])
    w.profil_bestaetigen(profil)
    with _phase(phasen, "einordnen"):
        vorschlaege = w.einordnen()
    konflikte = w.index.konflikte(offen=True)
    with _phase(phasen, "konflikt_entscheiden"):
        # Der Mensch entscheidet jeden gefundenen Konflikt mit "ersetzt"; bliebe einer
        # offen, wären beide Seiten gesperrt und E8 könnte nichts finden.
        entschieden = tuple(w.entscheide_konflikt(k.id, "ersetzt") for k in konflikte)
        entscheidung = entschieden[0] if entschieden else None
    with _phase(phasen, "freigeben"):
        # index.dateien() = ein Eintrag je Hash; `dateien` aus erfassen() enthält das
        # Duplikat ein zweites Mal, und freigeben() kopiert je übergebenem Hash einmal.
        freigegeben = w.freigeben(tuple(d.hash for d in w.index.dateien()))
    with _phase(phasen, "fragen"):
        antworten = {f["frage"]: w.frage(f["frage"]) for f in GOLDEN["fragen"]}
    return {
        "dateien": dateien,
        "duplikate": tuple(d.name for d in w.index.duplikate()),
        "profil": profil,
        "vorschlaege": {v.datei_name: v for v in vorschlaege},
        "konflikte": konflikte,
        "entscheidung": entscheidung,
        "freigegeben": freigegeben,
        "antworten": antworten,
    }


def _zweiter_lauf(basis: Path, provider, phasen: dict[str, float]) -> dict[str, list]:
    """E12: Profil + Einordnung erneut, frischer Arbeitsordner, gleiche Quelle."""
    w = _baue_werkstatt(basis, "zwei", provider)
    with _phase(phasen, "zweiter_lauf"):
        w.erfassen()
        w.auslesen()
        w.profil_bestaetigen(w.profil_vorschlagen(GOLDEN["zweck"]))
        vorschlaege = w.einordnen()
    return {v.datei_name: [v.kategorie, v.zielname] for v in vorschlaege}


def _umgebung(tags: list[str]) -> str:
    try:
        version = subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, timeout=30
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as fehler:
        version = f"nicht ermittelbar ({fehler})"
    return "\n".join(
        [
            "# Umgebung des e2e-Laufs",
            "",
            f"- Zeit (lokal): {datetime.now().isoformat(timespec='seconds')}",
            f"- ollama --version: {version}",
            f"- macOS: {platform.mac_ver()[0]} ({platform.platform()})",
            f"- Python: {platform.python_version()}",
            f"- Host: {HOST}",
            f"- modelle.yaml: embedding={KONFIG['embedding']} llm={KONFIG['llm']} "
            f"think={KONFIG.get('think')!r}",
            f"- Modelle in /api/tags: {', '.join(sorted(tags))}",
            "- Netzteil angeschlossen: unbekannt",
            "- Powermode: unbekannt",
            "",
            "Alle Zeiten in `zeiten.json`. Sollwerte: tests/golden.json.",
        ]
    )


def _schreibe_beweise(lauf: Lauf, tags: list[str]) -> None:
    ordner = lauf.beweise
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "umgebung.md").write_text(_umgebung(tags), encoding="utf-8")
    shutil.copyfile(lauf.werkstatt.profil_pfad, ordner / "profil.yaml")
    protokoll = lauf.werkstatt.arbeitsordner / ".dokumentenassistent" / "protokoll.jsonl"
    if protokoll.exists():
        shutil.copyfile(protokoll, ordner / "protokoll.jsonl")
    _schreibe_json(ordner / "vorschlaege.json", [_als_dict(v) for v in lauf.vorschlaege.values()])
    _schreibe_json(ordner / "konflikte.json", [_als_dict(k) for k in lauf.konflikte])
    _schreibe_json(
        ordner / "antworten.json",
        [
            {"frage": frage, "status": a.status, "text": a.text,
             "karten": [{"id": k.fundstelle.id, "datei": k.fundstelle.datei_name,
                         "wortlaut": k.wortlaut} for k in a.karten]}
            for frage, a in lauf.antworten.items()
        ],
    )
    _schreibe_json(ordner / "zweiter_lauf.json", lauf.zweiter_lauf)
    _schreibe_json(
        ordner / "zeiten.json",
        {
            "phasen_sekunden": lauf.phasen,
            "gesamt_sekunden": sum(lauf.phasen.values()),
            "modellaufrufe": lauf.provider.zaehler,
            "modellzeit_sekunden": lauf.provider.sekunden,
        },
    )
    _schreibe_json(
        ordner / "status.json",
        {
            "ist": {name: lauf.status(name) for name in sorted(GOLDEN["dateien"])},
            "soll": {name: GOLDEN["dateien"][name].get("status") for name in sorted(GOLDEN["dateien"])},
            "weitere_ist": {
                name: lauf.status(name) for name in sorted(GOLDEN.get("weitere_dateien", {}))
            },
            "duplikate": list(lauf.duplikate),
            "freigegeben": [str(p.relative_to(lauf.zielablage)) for p in lauf.freigegeben],
        },
    )


def _schreibe_json(pfad: Path, daten) -> None:
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(scope="session")
def lauf(tmp_path_factory) -> Lauf:
    tags = _tags()
    basis = tmp_path_factory.mktemp("e2e")
    provider = _provider()
    phasen: dict[str, float] = {}
    korpus_vorher = _hashes(KORPUS)
    w = _baue_werkstatt(basis, "eins", provider)
    quelle_vorher = _hashes(w.quelle)
    ergebnis = _erster_lauf(w, phasen)
    zweiter = _zweiter_lauf(basis, provider, phasen)
    ergebnis = Lauf(
        werkstatt=w,
        provider=provider,
        quelle=w.quelle,
        zielablage=w.zielablage,
        quelle_vorher=quelle_vorher,
        quelle_nachher=_hashes(w.quelle),
        korpus_vorher=korpus_vorher,
        korpus_nachher=_hashes(KORPUS),
        phasen=phasen,
        zweiter_lauf=zweiter,
        beweise=REPO / "beweise" / "e2e" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        **ergebnis,
    )
    _schreibe_beweise(ergebnis, tags)
    print(f"\n  [Beweise] {ergebnis.beweise}")
    return ergebnis


# ------------------------------------------------------------------- E1 bis E12


@pytest.mark.e2e
def test_E1_ollama_erreichbar_und_modelle_geladen():
    """Vorbedingung: Ollama antwortet und beide Modelle aus modelle.yaml sind da."""
    tags = _tags()
    fehlt = [m for m in (KONFIG["embedding"], KONFIG["llm"]) if not _geladen(m, tags)]
    assert fehlt == [], (
        f"Modelle fehlen in {HOST}/api/tags: {fehlt}. Vorhanden: {sorted(tags)}. "
        "Andreas muss sie selbst ziehen (ollama pull)."
    )


@pytest.mark.e2e
def test_E2_profil_enthaelt_sollkategorien_und_felder(lauf: Lauf):
    soll = GOLDEN["profil_muss_enthalten"]
    fehlt = {
        "kategorien": [k for k in soll["kategorien"] if k not in lauf.profil.kategorien],
        "felder": [f for f in soll["felder"] if f not in lauf.profil.felder],
    }
    assert fehlt == {"kategorien": [], "felder": []}, (
        f"Profil: kategorien={lauf.profil.kategorien} felder={lauf.profil.felder} "
        f"namensschema={lauf.profil.namensschema!r}"
    )


@pytest.mark.e2e
@pytest.mark.parametrize("name", sorted(GOLDEN["dateien"]))
def test_E3_jede_datei_hat_sollstatus(lauf: Lauf, name: str):
    vorschlag = lauf.vorschlaege.get(name)
    unklare = [] if vorschlag is None else [f.name for f in vorschlag.felder if f.status == "unklar"]
    assert lauf.status(name) == GOLDEN["dateien"][name]["status"], (
        f"{name}: unklare Felder={unklare} kategorie={getattr(vorschlag, 'kategorie', None)!r} "
        f"typ={getattr(vorschlag, 'typ', None)!r} zielname={getattr(vorschlag, 'zielname', None)!r}"
    )


@pytest.mark.e2e
def test_E4_jede_datei_hat_sollkategorie_wenn_sicher(lauf: Lauf):
    soll = {n: e["kategorie"] for n, e in GOLDEN["dateien"].items() if "kategorie" in e}
    ist = {n: getattr(lauf.vorschlaege.get(n), "kategorie", None) for n in soll}
    assert ist == soll, f"Profilkategorien waren: {lauf.profil.kategorien}"


@pytest.mark.e2e
def test_E5_alle_belege_bestehen_die_zitatpruefung(lauf: Lauf):
    """Unantastbar: kein Feld 'belegt' ohne wörtlichen Treffer in genau seiner Fundstelle."""
    faul = []
    for vorschlag in lauf.vorschlaege.values():
        fundstellen = {f.id: f for f in lauf.werkstatt.index.fundstellen(vorschlag.datei_hash)}
        for feld in vorschlag.felder:
            if feld.status != "belegt":
                continue
            if feld.beleg is None or not pruefe_beleg(feld.beleg, fundstellen):
                faul.append((vorschlag.datei_name, feld.name, feld.wert, feld.beleg))
    assert faul == [], f"Belege ohne wörtlichen Treffer: {faul}"


def _konflikt_signatur(feld: str, dateien, werte, vorschlag: str) -> tuple:
    return (feld, tuple(sorted(dateien)), tuple(sorted(werte)), vorschlag)


@pytest.mark.e2e
def test_E6_genau_die_sollkonflikte(lauf: Lauf):
    """Genau die Konfliktpaare aus golden — nicht mehr, nicht weniger. Der Scan ist
    dieselbe Rechnung wie Rechnung (2).pdf, deshalb trifft die Korrektur beide."""
    name = {v.datei_hash: v.datei_name for v in lauf.vorschlaege.values()}
    ist = sorted(
        _konflikt_signatur(k.feld, (name[k.hash_a], name[k.hash_b]), (k.wert_a, k.wert_b), k.vorschlag)
        for k in lauf.konflikte
    )
    soll = sorted(
        _konflikt_signatur(s["feld"], s["dateien"], s["werte"], s["vorschlag"])
        for s in GOLDEN["konflikte"]
    )
    assert ist == soll


@pytest.mark.e2e
def test_E7_freigabe_legt_kopien_an_und_originale_sind_hashgleich(lauf: Lauf):
    assert (
        len(lauf.freigegeben) > 0,
        all(p.exists() for p in lauf.freigegeben),
        lauf.quelle_nachher == lauf.quelle_vorher,
        lauf.korpus_nachher == lauf.korpus_vorher,
    ) == (True, True, True, True), (
        f"Kopien: {[p.name for p in lauf.freigegeben]}"
    )


@pytest.mark.e2e
def test_E8_frage_heizung_liefert_korrigierten_betrag_mit_beleg(lauf: Lauf):
    soll = GOLDEN["fragen"][0]
    antwort = lauf.antwort(0)
    passend = [
        k for k in antwort.karten
        if k.fundstelle.datei_name == soll["datei"] and soll["wortlaut_enthaelt"] in k.wortlaut
    ]
    assert (antwort.status, bool(passend)) == (soll["status"], True), (
        f"Antwort={antwort.text!r} Karten="
        f"{[(k.fundstelle.id, k.wortlaut[:60]) for k in antwort.karten]}"
    )


@pytest.mark.e2e
def test_E9_frage_kaltmiete_liefert_mietvertrag(lauf: Lauf):
    soll = GOLDEN["fragen"][1]
    antwort = lauf.antwort(1)
    dateien = [k.fundstelle.datei_name for k in antwort.karten]
    assert (antwort.status, soll["datei"] in dateien) == (soll["status"], True), (
        f"Antwort={antwort.text!r} Karten={[(k.fundstelle.id) for k in antwort.karten]}"
    )


@pytest.mark.e2e
def test_E10_frage_auto_ist_nicht_gefunden(lauf: Lauf):
    """Unantastbar: für ein Dokument, das es nicht gibt, darf keine Fundstelle entstehen."""
    antwort = lauf.antwort(2)
    assert (antwort.status, antwort.karten) == ("nicht_gefunden", ()), (
        f"Antwort={antwort.text!r} Karten={[k.fundstelle.id for k in antwort.karten]}"
    )


@pytest.mark.e2e
def test_E11_protokoll_zaehlt_hoechstens_n_menschliche_korrekturen(lauf: Lauf):
    """Nacharbeit = menschliche Korrekturen im Protokoll + Dateien, deren Ist-Status
    schlechter ist als der Sollstatus (die ein Mensch also nachziehen müsste)."""
    protokoll = lauf.werkstatt.index.protokoll()
    korrekturen = [e for e in protokoll if e["art"] == "korrektur"]
    nachzuziehen = [
        name for name, eintrag in GOLDEN["dateien"].items()
        if lauf.status(name) != eintrag["status"]
    ]
    assert len(korrekturen) + len(nachzuziehen) <= GOLDEN["nacharbeit_max_korrekturen"], (
        f"Korrekturen={len(korrekturen)} nachzuziehen={nachzuziehen} "
        f"(erlaubt: {GOLDEN['nacharbeit_max_korrekturen']})"
    )


@pytest.mark.e2e
def test_E12_zweiter_lauf_ist_deterministisch(lauf: Lauf):
    erster = {name: [v.kategorie, v.zielname] for name, v in lauf.vorschlaege.items()}
    abweichungen = {
        name: {"lauf1": erster[name], "lauf2": lauf.zweiter_lauf.get(name)}
        for name in sorted(erster)
        if erster[name] != lauf.zweiter_lauf.get(name)
    }
    assert abweichungen == {}, f"temperature 0, trotzdem unterschiedlich: {abweichungen}"

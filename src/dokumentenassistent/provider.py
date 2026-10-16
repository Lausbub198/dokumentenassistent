"""ModelProvider-Protocol und Ollama-Adapter. Modelle nur aus modelle.yaml (STATE 34).

Seit 23.09.2026 liest dieses Modul zusätzlich die Sucheinstellungen (Reranker, rerank_k,
top_n) aus derselben Datei. `RerankerFehler` wird mit re-exportiert, damit Aufrufer den
Startfehler fangen können, ohne retrieval_reranker direkt zu importieren.
"""
from __future__ import annotations

import dataclasses
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

import yaml

from dokumentenassistent.auslesen import (
    OcrEinstellungen,
    OcrNichtVerfuegbar,
    fordere_ocr,
)
from dokumentenassistent.retrieval_reranker import (
    CrossEncoderReranker,
    Reranker,
    RerankerFehler,
)
from dokumentenassistent.typen import DokumentenassistentFehler

__all__ = [
    "ABNAHME_PROTOKOLL_MODI",
    "ABNAHME_PROTOKOLL_STANDARD",
    "OCR_ENGINES",
    "OCR_STANDARD",
    "ModelProvider",
    "OcrEinstellungen",  # re-exportiert: gehört zu auslesen, wird aber hier aus der YAML gebaut
    "OcrNichtVerfuegbar",  # re-exportiert: Startfehler der OCR-Engine, siehe lade_ocr_einstellungen
    "OllamaProvider",
    "ProviderFehler",
    "RerankerFehler",  # re-exportiert: Startfehler des Rerankers, siehe lade_sucheinstellungen
    "SchemaFehler",
    "Sucheinstellungen",
    "lade_abnahme_protokoll",
    "lade_modelle",
    "lade_ocr_einstellungen",
    "lade_seitenuebergreifend",
    "lade_provider_suche",
    "lade_sucheinstellungen",
]


class ProviderFehler(DokumentenassistentFehler):
    """Ollama nicht erreichbar, HTTP-Fehler oder ungültige modelle.yaml."""


class SchemaFehler(ProviderFehler):
    """Die Modell-Antwort enthält kein gültiges JSON."""


class ModelProvider(Protocol):
    def embedding_revision(self) -> str: ...
    def embed(self, texte: list[str]) -> list[list[float]]: ...
    def generate_json(self, prompt: str, schema: dict) -> dict: ...
    def generate_text(self, prompt: str) -> str: ...


class OllamaProvider:
    def __init__(
        self,
        host: str,
        embed_modell: str,
        llm_modell: str,
        timeout: int = 120,
        think: str | bool = False,
        kontext: int | None = None,
        max_antwort_tokens: int | None = None,
        sprache: str = "Deutsch",
    ):
        self.host = host
        self.embed_modell = embed_modell
        self.llm_modell = llm_modell
        self.timeout = timeout
        self.think = think
        self.kontext = kontext  # num_ctx; None = Ollama-Standard (4096). Ollama kuerzt zu lange Prompts STILL.
        # num_predict nur für Freitext-Antworten: ohne Grenze schrieb gemma4:12b am 01.10. bei einer
        # Frage endlos weiter, bis nach 900 s das Zeitlimit griff. JSON-Aufrufe bleiben unbegrenzt.
        self.max_antwort_tokens = max_antwort_tokens
        # Zentral in modelle.yaml (`sprache:`), geht als System-Anweisung in jeden Modellaufruf.
        self.sprache = sprache

    def system_anweisung(self) -> str:
        return f"Antworte ausschließlich auf {self.sprache}."

    def embed(self, texte: list[str]) -> list[list[float]]:
        if not texte:
            return []
        antwort = self._post("/api/embed", {"model": self.embed_modell, "input": texte, "truncate": False})
        return antwort["embeddings"]

    def embedding_revision(self) -> str:
        """Resolve mutable model tags freshly; never invent provenance from a tag."""
        req = urllib.request.Request(self.host + '/api/tags', method='GET')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                models = json.loads(response.read()).get('models', [])
        except (OSError, ValueError) as exc:
            raise ProviderFehler('Embedding-Modellrevision nicht verfügbar') from exc
        name = self.embed_modell
        if ':' not in name.rsplit('/', 1)[-1]:
            name += ':latest'
        matches = {m.get('digest') for m in models if m.get('name') in (name, self.embed_modell)}
        if len(matches) != 1 or not all(isinstance(d, str) and d for d in matches):
            raise ProviderFehler('Embedding-Modellrevision fehlt oder ist mehrdeutig')
        return matches.pop()

    def generate_json(self, prompt: str, schema: dict) -> dict:
        response = self._generate(prompt, format_=schema)
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise SchemaFehler(f"Keine gültige JSON-Antwort: {response!r}") from e

    def generate_text(self, prompt: str) -> str:
        return self._generate(prompt, max_tokens=self.max_antwort_tokens)

    def _generate(self, prompt: str, format_: dict | None = None, max_tokens: int | None = None) -> str:
        payload = {
            "model": self.llm_modell,
            "prompt": prompt,
            "stream": False,
            "format": format_,
            "think": self.think,
            "system": self.system_anweisung(),
            "options": {"temperature": 0, **({"num_ctx": self.kontext} if self.kontext else {}),
                        **({"num_predict": max_tokens} if max_tokens else {})},
        }
        antwort = self._post("/api/generate", payload)
        response = antwort.get("response", "")
        if not response.strip() and antwort.get("thinking"):
            raise ProviderFehler(
                "Ollama hat nur `thinking` geliefert, `response` ist leer — "
                "in modelle.yaml `think: false` setzen"
            )
        return response

    def _post(self, pfad: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.host + pfad,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderFehler(f"HTTP {e.code} von Ollama unter {self.host}") from e
        except (ConnectionRefusedError, urllib.error.URLError, OSError) as e:
            raise ProviderFehler(f"Ollama nicht erreichbar unter {self.host}") from e


class LmStudioProvider(OllamaProvider):
    """Antwortmodell über LM Studio (OpenAI-kompatibles `/v1/chat/completions`), Embedding weiter über Ollama.

    Zweck (06.10.2026): Laufzeiten vergleichen, insbesondere MLX, ohne den Index zu wechseln — Vektoren und
    `embedding_revision` bleiben exakt die des Ollama-Embeddings. Reine Protokollübersetzung: als System-Prompt nur die
    Sprachanweisung aus modelle.yaml, keine Wiederholung. Das Kontextfenster legt LM Studio beim Laden des Modells fest
    (`lms load … --context-length`), nicht je Anfrage; `kontext` und `think` haben hier keine Wirkung.
    """

    def __init__(self, host: str, embed_modell: str, llm_modell: str, llm_host: str, **kwargs):
        super().__init__(host, embed_modell, llm_modell, **kwargs)
        self.llm_host = llm_host

    def _generate(self, prompt: str, format_: dict | None = None, max_tokens: int | None = None) -> str:
        payload: dict = {"model": self.llm_modell, "messages": [{"role": "system", "content": self.system_anweisung()},
                                                                {"role": "user", "content": prompt}],
                         "temperature": 0, "stream": False}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if format_ is not None:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "antwort", "strict": True, "schema": format_}}
        req = urllib.request.Request(self.llm_host + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                antwort = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderFehler(f"HTTP {e.code} von LM Studio unter {self.llm_host}") from e
        except (ConnectionRefusedError, urllib.error.URLError, OSError) as e:
            raise ProviderFehler(f"LM Studio nicht erreichbar unter {self.llm_host}") from e
        try:
            return antwort["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderFehler(f"Unerwartete Antwort von LM Studio: {str(antwort)[:200]}") from e


LLM_LAUFZEITEN = ("ollama", "lmstudio")


def lade_modelle(pfad: Path) -> OllamaProvider:
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProviderFehler(f"modelle.yaml nicht gefunden: {pfad}") from e
    for pflicht in ("host", "embedding", "llm"):
        if pflicht not in daten:
            raise ProviderFehler(f"modelle.yaml: Pflichtschlüssel '{pflicht}' fehlt")
    laufzeit = daten.get("llm_laufzeit", "ollama")
    if laufzeit not in LLM_LAUFZEITEN:
        raise ProviderFehler(f"modelle.yaml: llm_laufzeit muss eine von {LLM_LAUFZEITEN} sein, nicht {laufzeit!r}")
    gemeinsam = dict(host=daten["host"], embed_modell=daten["embedding"], llm_modell=daten["llm"],
                     think=daten.get("think", False), kontext=daten.get("kontext"),
                     timeout=daten.get("timeout", 120), max_antwort_tokens=daten.get("max_antwort_tokens"),
                     sprache=daten.get("sprache", "Deutsch"))
    if laufzeit == "lmstudio":
        return LmStudioProvider(llm_host=daten.get("llm_host", "http://localhost:1234"), **gemeinsam)
    return OllamaProvider(**gemeinsam)


@dataclasses.dataclass(frozen=True)
class Sucheinstellungen:
    """Was `suche()` außer dem Provider braucht. Die Standardwerte sind das Verhalten
    von vor dem 23.09.2026: kein Reranker, `top_n` 8.

    Ein Dataclass, keine Klasse mit Logik: hier wird nichts entschieden, nur
    durchgereicht (Werkstatt -> suche). `reranker` ist bereits das fertige Objekt,
    damit Tests einen Fake einsetzen können, ohne sentence-transformers zu laden.
    """

    reranker: Reranker | None = None
    rerank_k: int = 20
    # top_n 8 ist der historische Standard von vor dem 23.09.2026 und bleibt der Code-Default, damit ein
    # Bestand ohne Eintrag sich nicht still anders verhaelt. Die gemessene Empfehlung ist 5 und steht so in
    # der mitgelieferten `modelle.yaml`: zwischen 5 und 8 Absaetzen aendert sich kein Ergebnis (Recall@3/5/8
    # je 93 %), fuenf sparen ein Drittel Kontext. Wer den Schluessel loescht, bekommt 8 -- nicht falsch, nur
    # ungemessen.
    top_n: int = 8
    # Phase B (01./02.10.2026): None = SCHWELLE aus suche (0,49, am 0,6B-Embedding kalibriert).
    schwelle: float | None = None
    kontextauswahl: str = 'fest'
    kaskade: bool = False
    kaskade_stufe2: str = 'keine'
    # Phase D (02.10.2026): 'pfad' = Pfad-Präfix für Embedding und Reranker (eigene Vektor-Herkunft).
    kontext_praefix: str = 'keiner'


def lade_sucheinstellungen(pfad: Path) -> Sucheinstellungen:
    """Optionale Schlüssel `reranker`, `rerank_k`, `rerank_geraet`, `top_n` aus modelle.yaml.

    Fehlen sie alle, ist das Ergebnis `Sucheinstellungen()` — heutiges Verhalten.
    Ist `reranker` gesetzt, wird der Cross-Encoder HIER gebaut, also beim Start:
    fehlt das Extra `reranker` (sentence-transformers), fliegt ein `RerankerFehler`
    mit Installationshinweis, statt dass die erste Frage still ohne Reranker läuft —
    ein stiller Verzicht wäre bei R@1 79 -> 93 eine andere Messlage als die eingestellte.
    """
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProviderFehler(f"modelle.yaml nicht gefunden: {pfad}") from e
    standard = Sucheinstellungen()
    modell = daten.get("reranker")
    reranker = CrossEncoderReranker(modell, daten.get("rerank_geraet")) if modell else None
    from dokumentenassistent.suche import KONTEXT_PRAEFIX, KONTEXTAUSWAHL, STUFE2
    praefix = daten.get("kontext_praefix", standard.kontext_praefix)
    if praefix not in KONTEXT_PRAEFIX:
        raise ProviderFehler(f"modelle.yaml: kontext_praefix {praefix!r} unbekannt")
    auswahl = daten.get("kontextauswahl", standard.kontextauswahl)
    stufe2 = daten.get("kaskade_stufe2", standard.kaskade_stufe2)
    if auswahl not in KONTEXTAUSWAHL or stufe2 not in STUFE2:
        raise ProviderFehler(f"modelle.yaml: kontextauswahl {auswahl!r} oder kaskade_stufe2 {stufe2!r} unbekannt")
    if auswahl == "dynamisch" and reranker is None:
        raise ProviderFehler("modelle.yaml: kontextauswahl dynamisch braucht einen reranker")
    schwelle = daten.get("schwelle")
    return Sucheinstellungen(
        reranker=reranker,
        rerank_k=int(daten.get("rerank_k", standard.rerank_k)),
        top_n=int(daten.get("top_n", standard.top_n)),
        schwelle=float(schwelle) if schwelle is not None else None,
        kontextauswahl=auswahl,
        kaskade=bool(daten.get("kaskade", standard.kaskade)),
        kaskade_stufe2=stufe2,
        kontext_praefix=praefix,
    )


def lade_seitenuebergreifend(pfad: Path) -> bool:
    """Chunk-Grenze aus modelle.yaml; fehlender Schlüssel behält den alten Modus."""
    try:
        daten = yaml.safe_load(Path(pfad).read_text()) or {}
    except FileNotFoundError as exc:
        raise ProviderFehler(f'modelle.yaml nicht gefunden: {pfad}') from exc
    except yaml.YAMLError as exc:
        raise ProviderFehler('modelle.yaml enthält ungültiges YAML') from exc
    if not isinstance(daten, dict):
        raise ProviderFehler('modelle.yaml muss ein Mapping enthalten')
    wert = daten.get('seitenuebergreifend', False)
    if type(wert) is not bool:
        raise ProviderFehler('seitenuebergreifend muss true oder false sein')
    return wert


# --------------------------------------------------------- Abnahme-Protokoll
#
# Eigene kleine Funktion statt eines Felds in `Sucheinstellungen`: `abnahme_protokoll`
# steuert, wie VIEL ein Urteil in `beweise/abnahme/...` preisgibt (Datenschutz), nicht WIE
# gesucht wird (Retrieval). Zwei verschiedene Zwecke in einem Dataclass zu vermischen wäre
# die unnötige Abstraktion, kein Gewinn an Lesbarkeit.

ABNAHME_PROTOKOLL_STANDARD = "knapp"
ABNAHME_PROTOKOLL_MODI = ("knapp", "voll")


def lade_abnahme_protokoll(pfad: Path) -> str:
    """`abnahme_protokoll: knapp | voll` aus modelle.yaml, Standard `knapp`.

    Anlass (23.09.2026): der Auftraggeber will die Abnahme-Ansicht (`/abnahme`) mit ECHTEN,
    teils vertraulichen Dokumenten benutzen. `beweise/abnahme/<datum>/urteile.jsonl` liegt im
    Projektordner unter Git — schreibt sie Frage, Antworttext und den Wortlaut der
    Belegkarten im Klartext hinein, landet bei einem unbedachten `git add` fremder
    Dokumentinhalt im Repository. `knapp` ist deshalb der Standard: das Protokoll belegt das
    URTEIL (Hashes/Längen), nicht den WORTLAUT. `voll` bleibt für den synthetischen Korpus
    (`beispiele/malerbetrieb`) sinnvoll, wo Inhalt unkritisch und zur Fehlersuche nützlich ist.
    """
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProviderFehler(f"modelle.yaml nicht gefunden: {pfad}") from e
    modus = daten.get("abnahme_protokoll", ABNAHME_PROTOKOLL_STANDARD)
    if modus not in ABNAHME_PROTOKOLL_MODI:
        raise ProviderFehler(
            f"modelle.yaml: abnahme_protokoll muss 'knapp' oder 'voll' sein, nicht {modus!r}"
        )
    return modus


# ------------------------------------------------------------- OCR (24.09.2026)
#
# Eigene Funktion wie `lade_abnahme_protokoll`, kein Feld in `Sucheinstellungen`: die OCR
# entscheidet, WAS ueberhaupt in den Index kommt, nicht WIE gesucht wird. Zwei Zwecke in
# einem Dataclass waeren die unnoetige Abstraktion.
#
# Warum die Standardwerte je Engine verschieden sind, und warum ueberhaupt Standardwerte im
# Code stehen, obwohl die Schwelle laut Auftrag in die YAML gehoert: der Schluessel ist
# OPTIONAL. Wer `ocr: tesseract` einstellt und `ocr_schwelle` weglaesst, bekommt 0,6 (die
# gemessene Tesseract-Schwelle) und nicht 0,80 (die PaddleOCR-Schwelle) — ein gemeinsamer
# Standard waere fuer eine der beiden Engines schlicht falsch. Die mitgelieferte
# modelle.yaml schreibt beide Werte aus, damit sie sichtbar sind.

OCR_ENGINES = ("paddleocr", "tesseract")
OCR_STANDARD_ENGINE = "paddleocr"
# Engine -> (Sprachkennung, Schwelle). Zwei Engines, zwei Vokabulare: PaddleOCR erwartet
# "german", Tesseract "deu". Der Nutzer stellt EINEN Schluessel `ocr_sprache` ein; fehlt er,
# gilt die Kennung der gewaehlten Engine. Zwei Schluessel (`ocr_sprache_paddle`,
# `ocr_sprache_tesseract`) waeren Konfiguration fuer einen Fall, den es nicht gibt: es laeuft
# immer genau eine Engine.
OCR_STANDARD = {
    # 0,80 — und dieser Wert weist auf den gemessenen Seiten FAKTISCH NICHTS ab ausser
    # leeren Ergebnissen. Das ist kein Versehen, sondern der Befund.
    #
    # Die fruehere Ableitung (0,87) stammte aus der Variante OHNE Seitenorientierung. Dort
    # lagen die drei als "unbrauchbar" beurteilten Seiten bei 0,681/0,697/0,774 gegen
    # 0,975-1,000 bei den brauchbaren, und jeder Wert dazwischen trennte sauber. Im Produkt
    # laeuft aber `ocr_drehung: true`. Auf DIESER Variante (beweise/ocr-drehung/2026-09-24/,
    # Spalte `nur_seitenorientierung`) sehen dieselben zehn Seiten so aus:
    #   "unbrauchbar" (3 Seiten): 0,9468 / 0,9656 / 0,9872
    #   "brauchbar"   (7 Seiten): 0,9752 / 0,9937 / 0,9946 / 0,9964 / 0,9969 / 1,0000
    #                             und eine reine Bildseite ohne Text (0,0)
    # Die Klassen UEBERLAPPEN: 0,9752 (brauchbar) liegt unter 0,9872 (unbrauchbar). Kein
    # Wert trennt sie noch. Der nach Youden beste waere 0,9937 (Sensitivitaet 3/3,
    # Spezifitaet 5/7) — er wuerde aber genau die drei Seiten abweisen, die die
    # Seitenorientierung gerade repariert hat (122/97/91 -> 495/564/413 Zeichen, 0 -> 5
    # Datumsangaben), plus eine brauchbare Seite mit 61 Zahlen. Das waere der Gewinn der
    # Drehung, wieder weggeworfen an der naechsten Stelle.
    #
    # Grund der Ueberlappung: die Urteile haengen an den UNGEDREHTEN Texten. Sie sind fuer
    # die Produktvariante veraltet. Eine Schwelle gegen veraltete Etiketten zu optimieren
    # waere Schoenrechnen.
    #
    # 0,80 liegt unter allen zehn gemessenen Seitenwerten der Produktvariante (Minimum
    # 0,9468) und ueber den Werten, die dieselben drei Seiten OHNE Orientierungskorrektur
    # hatten (0,681/0,697/0,774). Heisst: eine Seite, bei der die Korrektur versagt und die
    # Engine wirklich Rauschen liest, faellt weiter durch — abgewiesen wird auf dieser
    # Stichprobe aber nur die Seite ohne jeden Text ("kein Text erkannt -> 0.0").
    # Ableitung, Alternativsignal und Vorbehalt: docs/ocr-entscheidung-2026-09-24.md.
    "paddleocr": ("german", 0.80),
    # 0,6: der historische Wert, gemessen an den Test-Fixtures (sauberer Scan 0,958,
    # unscharfes Bild 0,0). Die 10 Scan-Seiten bestaetigen ihn als brauchbar, aber nicht als
    # optimal (siehe docs/ocr-entscheidung-2026-09-24.md).
    "tesseract": ("deu", 0.6),
}


def lade_ocr_einstellungen(pfad: Path) -> OcrEinstellungen:
    """`ocr`, `ocr_drehung`, `ocr_sprache`, `ocr_schwelle` aus modelle.yaml.

    Fehlen alle vier, gilt `paddleocr` mit Drehung, `german` und 0,80 — **nicht** das
    Verhalten von vor dem 24.09.2026. Das ist Absicht: der Standard des Produkts ist die
    gemessen bessere Engine (7 gegen 3 brauchbare von 10 gegengelesenen Scan-Seiten,
    0 gegen 1 Seite mit falsch gelesenen Zahlen). Der Code-Default in
    `auslesen.OcrEinstellungen()` bleibt dagegen Tesseract, damit bestehende Aufrufer
    sich nicht still anders verhalten.

    Die Engine wird HIER geprueft, also beim Start: fehlt das Extra `ocr-paddle`, fliegt
    ein `OcrNichtVerfuegbar` mit Installationsbefehl, statt dass die erste Datei still
    mit Tesseract gelesen wird. Ein stiller Rueckfall waere eine andere Messlage als die
    eingestellte — genauso wie beim Reranker.
    """
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProviderFehler(f"modelle.yaml nicht gefunden: {pfad}") from e
    engine = daten.get("ocr", OCR_STANDARD_ENGINE)
    if engine not in OCR_ENGINES:
        raise ProviderFehler(
            f"modelle.yaml: ocr muss eine von {OCR_ENGINES} sein, nicht {engine!r}"
        )
    sprache, schwelle = OCR_STANDARD[engine]
    seitenbereinigung = daten.get('seitenbereinigung', False)
    if type(seitenbereinigung) is not bool:
        raise ProviderFehler('modelle.yaml: seitenbereinigung muss true oder false sein')
    einstellungen = OcrEinstellungen(
        seitenbereinigung=seitenbereinigung,
        engine=engine,
        drehung=bool(daten.get("ocr_drehung", True)),
        sprache=str(daten.get("ocr_sprache", sprache)),
        schwelle=float(daten.get("ocr_schwelle", schwelle)),
        pdf_extraktion=str(daten.get('pdf_extraktion', 'pypdf')),
    )
    if einstellungen.pdf_extraktion not in ('pypdf', 'pdftotext', 'pdftotext_layout'):
        raise ProviderFehler('modelle.yaml: pdf_extraktion muss pypdf, pdftotext oder pdftotext_layout sein')
    fordere_ocr(einstellungen)
    return einstellungen


def lade_provider_suche(pfad: Path) -> OllamaProvider | None:
    """Modell nur für die Frage-Antwort-Suche (Werkstatt.frage).

    None, wenn `llm_suche` in modelle.yaml fehlt oder gleich `llm` ist — dann gilt
    weiterhin der Haupt-Provider aus lade_modelle(). host/embedding/think/kontext/timeout
    kommen unverändert aus modelle.yaml, damit das Embedding-Modell zum Haupt-Provider
    passt (Suchvektoren müssen mit den beim Einordnen gespeicherten kompatibel bleiben).
    """
    try:
        daten = yaml.safe_load(pfad.read_text()) or {}
    except FileNotFoundError as e:
        raise ProviderFehler(f"modelle.yaml nicht gefunden: {pfad}") from e
    llm_suche = daten.get("llm_suche")
    if not llm_suche or llm_suche == daten.get("llm"):
        return None
    return OllamaProvider(
        host=daten["host"],
        embed_modell=daten["embedding"],
        llm_modell=llm_suche,
        think=daten.get("think", False),
        kontext=daten.get("kontext"),
        timeout=daten.get("timeout", 120),
        max_antwort_tokens=daten.get("max_antwort_tokens"),
        sprache=daten.get("sprache", "Deutsch"),
    )

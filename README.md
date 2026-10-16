# Dokumentenassistent

Lokales Werkzeug: liest einen Dokumentenordner, schlägt ein Profil vor (Kategorien, Felder, Namensschema), ordnet jede Datei mit wörtlichen Fundstellen ein, legt **nach menschlicher Freigabe** sortierte Kopien an und beantwortet Fragen ausschließlich mit geprüften Belegen. Originale werden nie verändert.

Modelle laufen über Ollama (`modelle.yaml`). Kein Cloud-Zugriff.

> **Stand:** Version 0.1, von einer Person für den eigenen Gebrauch gebaut — kein fertiges Produkt.
> Entwickelt und gemessen **nur auf macOS** (MacBook Pro M4 Pro, 24 GB). Der Code ist für Linux und
> Windows angelegt, dort aber **nicht getestet**. Das Projekt entstand mit KI-Unterstützung (Claude).

## Voraussetzungen

| Was | Wozu |
|---|---|
| Python 3.13 und [`uv`](https://docs.astral.sh/uv/) | Installation und Start |
| [Ollama](https://ollama.com) | Sprachmodell und Embedding, laufen lokal |
| rund 13 GB freier Arbeitsspeicher | `gemma4:12b-it-q4_K_M` (8,1 GB) und `qwen3-embedding:4b` (4,4 GB); auf 16 GB nur mit kleineren Modellen, siehe unten |
| Internet beim **ersten** Start | der Reranker (Hugging Face) und die OCR-Modelle (PaddleOCR) laden sich einmalig nach; danach läuft alles offline |

## Schnellstart

```bash
git clone https://github.com/Lausbub198/dokumentenassistent.git && cd dokumentenassistent
ollama pull gemma4:12b-it-q4_K_M
ollama pull qwen3-embedding:4b
uv sync --extra reranker --extra ocr-paddle   # beide Extras sind in der mitgelieferten modelle.yaml eingestellt
uv run dokumentenassistent                    # öffnet nichts selbst; dann http://127.0.0.1:8765/start im Browser
```

Dort Quellordner und Zielordner über **Ordner wählen** aussuchen. Der Zielordner muss **außerhalb**
des Quellordners liegen. Die Originale werden nie verändert, es entstehen nur Kopien nach deiner Freigabe.

Zum Ausprobieren liegt unter `beispiele/malerbetrieb-demo/` ein synthetischer Stapel mit 25 Dateien.

## Konfiguration

Alle Einstellungen stehen in `modelle.yaml`, jede mit Kommentar und Messbeleg (Tabellen unten). Wer eine
andere Datei will, gibt sie mit `--modelle` an. Für Mess- und Vergleichsskripte mit privaten Daten gibt es
keine festen Pfade: `DOKASS_BESTAND`, `DOKASS_ARBEIT`, `DOKASS_FRAGEN`, `DOKASS_LAEUFE` und
`DOKASS_GERMANQUAD` setzen die Orte (Standard `~/dokass-privat/<name>`, siehe
`src/dokumentenassistent/pfade_privat.py`).

## Betriebssysteme

| | Stand |
|---|---|
| macOS (Apple Silicon) | entwickelt, gemessen, getestet |
| Linux | nicht getestet; `start.command` ist ein Bash-Skript und sollte laufen, sonst den `uv run`-Befehl oben nehmen |
| Windows | nicht getestet; `start.command` läuft dort nicht, den `uv run`-Befehl direkt benutzen |

Das Produkt braucht kein macOS-Bauteil: Die OCR ist PaddleOCR (Tesseract als Alternative), Apple Vision
steckt nur im Mess-Extra `ocr`. Die Ordnerwahl läuft im Browser, nicht über einen Systemdialog.

## Tests

```bash
uv run pytest              # Modul- und Verdrahtungstests, ohne Modell
uv run pytest -m e2e       # gegen laufenden Ollama und den Beispielkorpus
```

## Die gemessene Konfiguration

Jede Zeile in `modelle.yaml` steht dort, weil sie gemessen wurde — Belege in `beweise/`, Begründungen in `docs/`
und in den Messberichten des LocalKI Lab (`docs/messungen/2026-09-29` bis `2026-10-03-phase-d-modellwechsel.md`).
Gemessen auf einem MacBook Pro M4 Pro, 24 GB, Ollama 0.34.0.

**Fragen (Stand 06.10.2026)** — privater Bestand (113 Dateien, 100 Goldfragen, davon 15 ohne Antwort im Bestand)
und GermanQuAD (474 Wikipedia-Absätze, 2204 menschliche Fragen) als zweiter, unabhängiger Prüfstein:

| Einstellung | Wert | Messung dahinter |
|---|---|---|
| `llm` | `gemma4:12b-it-q4_K_M` | bringt 159 von 163 soll-sicheren Dateien in den Index; die 4B-Modelle 127. Was nicht eingeordnet ist, findet keine Suche. |
| `embedding` | `qwen3-embedding:4b` | Ziel-Absatz im Kontext 64/85 (0,6B) → 73/85 (4B) bzw. 79/85 (8B). Im Produktpfad liegt 4B gleichauf mit 8B (62 gegen 60 belegte Antworten, 36,6 gegen 40,2 s); 8B und gemma passen auf 24 GB nicht gleichzeitig in den Speicher und werden je Frage umgeladen. |
| `kontext_praefix` | `pfad` | „Dokument: <relativer Pfad>“ vor jedem Chunk, nur für Embedding und Reranker, nie im Antwortprompt. 74 → 79/85 mit 8B. |
| `pdf_extraktion` / `seitenuebergreifend` | `pdftotext_layout` / `true` | Chunks über Seitengrenzen; Zitate tragen Seitenbereiche (z. B. S. 21–23). 61 → 66/85. |
| Suchverfahren | dense, **kein BM25/RRF** | jede gemessene Fusion lag unter dem reinen Embedding (43–64 % gegen 79 % Rang 1); deutsche Komposita. `docs/retrieval-befund-2026-09-21.md` |
| `reranker` / `rerank_k` | `BAAI/bge-reranker-v2-m3` / 20 | Recall@1 79 → 93 %, Recall@8 93 → 100 %; GermanQuAD 88 → 98 %. |
| `kontextauswahl` / `top_n` | `dynamisch` / 20 | gemma liest nur die Absätze mit Reranker-Score ≥ 0,5 × bester Score (höchstens 20). Feste Top 20 hängen von der Reihenfolge ab (41 in beiden Reihenfolgen korrekt gegen 50). |
| `kaskade` / `kaskade_stufe2` | `true` / `streng` | ohne gültiges Zitat zweiter Versuch mit den Top 20 und strenger Abweisungsanweisung: 57 Antworten in beiden Reihenfolgen korrekt, 15/15 Fragen ohne Antwort abgewiesen. |
| `schwelle` | 0 | die frühere Ähnlichkeitsschwelle 0,49 trennt beantwortbare von unbeantwortbaren Fragen nicht (C6); auf GermanQuAD wies die alte Gesamtkonfiguration 70 von 200 beantwortbaren Fragen ab — vermutlich an dieser Schwelle, aber nicht isoliert nachgemessen. |
| `think` | `false` | Pflicht: mit `low` legt Ollama 0.34 die Antwort ins Feld `thinking`. |
| `kontext` | 32768 | größter Antwortprompt 18 920 Tokens; mit 16384 würden 12 von 100 still gekürzt. |
| `max_antwort_tokens` | 1024 | ohne Grenze lief gemma bei einzelnen Fragen in Schleifen bis zum Timeout. |

Ergebnis: privater Bestand 62 von 85 beantwortbaren Fragen mit gültigem Beleg (Ausgangsstand 29.09.: 43),
15/15 unbeantwortbare abgewiesen, Median 37 s je Frage; „nicht gefunden“ dauert am längsten (bis gut 2 min),
weil zuvor beide Stufen versucht werden. GermanQuAD: 197 von 200 Antworten mit Beleg aus dem Soll-Absatz
(alte Konfiguration 129), Median 13 s.

**Einordnen (Stand 24.09.2026)**, gemessen an 200 Dokumenten (242 Seiten, 694 Absätze):

| Einstellung | Wert | Messung dahinter |
|---|---|---|
| `timeout` | 900 | Sekunden je Ollama-Aufruf. Mit den vorherigen 120 s brach der Profilvorschlag über 126 echte Dokumente ab — gemessen brauchte derselbe Aufruf 245 s. |
| `ocr` / `ocr_drehung` | `paddleocr` / `true` | auf 10 echten Scan-Seiten 7 brauchbar gegen 3 bei Tesseract, 0 gegen 1 Seite mit falschen Zahlen. `ocr_drehung` schaltet **nur** die Seitenorientierung: sie richtet die 3 verdrehten Seiten auf (122/97/91 → 495/564/413 Zeichen) und lässt die anderen 7 zeichenweise unverändert. Die beiden anderen PaddleOCR-Vorstufen bleiben aus — sie schaden gemessen. Kosten: ~29 s statt ~1 s je Seite. `docs/ocr-entscheidung-2026-09-24.md` |
| `ocr_schwelle` | `0.80` | unter diesem Wert geht eine Seite nicht ans Modell. **Weist mit aufgerichteten Seiten faktisch nichts mehr ab außer leeren Ergebnissen** — nach der Aufrichtung überlappen „brauchbar" und „unbrauchbar" (0,975 gegen 0,987), die Konfidenz trennt sie nicht mehr. Warum trotzdem kein schärferer Wert: Befund, Alternativsignal und Vorbehalt in `docs/ocr-entscheidung-2026-09-24.md`. |

Ergebnis dieser Konfiguration auf den 200 Dokumenten (Bestätigungslauf 24.09. auf ruhiger Maschine,
`beweise/last/2026-09-24/bericht.md`): 16,2 s je Datei, Kategorie 89 % richtig, Status 98,5 % richtig,
11 von 640 Belegen an der Zitatprüfung verworfen (1,7 %), 8 von 8 Konflikten erkannt, 8,4 GB Speicher
(damals noch mit 0,6B-Embedding und `kontext: 16384`; die Fragen-Zahlen dieses Laufs sind durch die Tabelle oben
ersetzt). Speicher heute: gemma 8,1 GB + 4B-Embedding 4,4 GB + Reranker im Python-Prozess — auf 24 GB knapp,
große Programme nebenher (Videoschnitt, VMs) verlangsamen jede Frage merklich.

**Für den eigenen Bestand gilt das nicht automatisch.** Die Rangfolge der Embeddings dreht sich zwischen zwei
Korpora um. `python -m dokumentenassistent.retrieval_eval` misst das auf eigenen Dokumenten in Minuten, ohne
Sprachmodell — dafür braucht es nur Fragen, deren Antwort man kennt.

## OCR ist wählbar

Bilder und PDFs ohne Textebene liest seit dem 24.09.2026 standardmäßig **PaddleOCR** statt Tesseract
(`ocr: paddleocr` in `modelle.yaml`, mit `ocr_drehung: true` und `ocr_schwelle: 0.80`). Der ganze Weg
zu dieser Entscheidung — welche Engines geprüft wurden, welche zwei Messarten sie tragen, warum Apple
Vision trotz der besten Rohwerte ausscheidet, warum von PaddleOCRs drei Vorstufen nur eine an ist und
was ungemessen bleibt — steht in `docs/ocr-entscheidung-2026-09-24.md`.

```bash
uv sync --extra ocr-paddle   # Voraussetzung für ocr: paddleocr
```

Das Extra zieht `paddleocr` und `paddlepaddle` nach (ein vollständiges Inferenz-Framework, u. a. mit
`opencv-contrib-python`, `shapely` und `pandas`). Beim **ersten** Lauf lädt PaddleOCR seine Modelle
einmalig aus dem Netz nach `~/.paddlex`; danach läuft alles offline. Fehlt das Extra und ist
`ocr: paddleocr` eingestellt, **bricht der Start mit einem Hinweis ab** — es gibt keinen stillen
Rückfall auf Tesseract, weil das eine andere Messlage wäre als die eingestellte.

Wer das nicht will, stellt `ocr: tesseract` ein. Dann genügt wie bisher
`brew install tesseract tesseract-lang`, eine Seite kostet rund eine statt 29 Sekunden — und die
Lesequalität auf echten Scans ist messbar schlechter (3 von 10 brauchbaren Seiten statt 7).
`ocr_sprache` und `ocr_schwelle` passen sich der gewählten Engine automatisch an; wer sie setzt,
überschreibt beide.

## Web-Oberfläche

Am schnellsten per Doppelklick auf `start.command` (Finder) oder im Terminal:

```bash
./start.command
```

Das Skript prüft erst, ob Ollama antwortet, startet dann den Server und öffnet
`/start` im Browser. Läuft schon eine Instanz, öffnet es nur das Fenster.

Oder direkt:

```bash
uv run dokumentenassistent                                   # Bestand unter http://127.0.0.1:8765/start wählen
uv run dokumentenassistent --quelle /pfad/zur/quelle --ziel /pfad/zur/ablage   # direkt öffnen
```

Ohne `--quelle/--ziel` fragt `/start` nach Quellordner und Zielablage (Vorschlag: `<Quelle>_sortiert`) und merkt sich die letzten fünf Bestände in `~/.config/dokumentenassistent/zuletzt.json`. Beide Pfade lassen sich eintippen oder einfügen (im Finder <kbd>Option</kbd>+<kbd>Cmd</kbd>+<kbd>C</kbd>) — oder über „Ordner wählen…“ neben dem Feld suchen: der Knopf öffnet ein Fenster, in dem man sich durch die Ordner klickt („↑ eine Ebene“ geht zurück), „Diesen Ordner wählen“ trägt den Pfad ins Feld, <kbd>Esc</kbd> bricht ab. Die Liste kommt vom Server (`GET /ordner`, beginnt im Heimatverzeichnis oder beim Pfad, der schon im Feld steht) und enthält ausschließlich Ordnernamen — keine Dateien, keine Inhalte; versteckte Ordner bleiben außen vor, Verweisen (Symlinks) folgt sie nicht. Ohne JavaScript bleibt der Knopf weg und die Textfelder tragen die Eingabe; geprüft wird ohnehin serverseitig. „Stapel einordnen“ läuft im Hintergrund mit Fortschritt und Abbruch; ein Abbruch verliert nichts, der nächste Start nimmt nur die Dateien ohne Vorschlag.

## MCP-Server (nur lesend)

`dokumentenassistent-mcp` stellt genau drei Werkzeuge über stdio bereit — `suchen(frage)`, `fundstelle_lesen(id)`, `datei_oeffnen(fundstelle_id)`. Sichtbar ist nur, was in der Web-Oberfläche freigegeben wurde; `datei_oeffnen` nennt die Kopie in der Zielablage, nie das Original. Kein Werkzeug schreibt, gibt frei oder korrigiert. Jeder Aufruf steht als Zeile `art: "mcp"` in `.dokumentenassistent/protokoll.jsonl` (Werkzeug, Argumente, gelieferte Fundstellen-IDs, Ablehnungen mit Grund); der Start als `mcp_start`.

**Ehrlich gesagt:** Belegkarten und Fundstellen-Texte gehen an den MCP-Client — bei Claude Desktop oder Claude Code also in die Cloud, sobald das Modell sie liest. Privat bleibt der Bestand nur mit einem lokalen Client (lokales LLM, lokaler MCP-Client, lokale Dateien).

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dokumentenassistent": {
      "command": "uv",
      "args": [
        "run", "--project", "/pfad/zu/dokumentenassistent", "dokumentenassistent-mcp",
        "--quelle", "/pfad/zur/quelle",
        "--ziel", "/pfad/zur/ablage",
        "--modelle", "/pfad/zu/dokumentenassistent/modelle.yaml"
      ]
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add dokumentenassistent -- uv run --project /pfad/zu/dokumentenassistent dokumentenassistent-mcp \
  --quelle /pfad/zur/quelle --ziel /pfad/zur/ablage --modelle /pfad/zu/dokumentenassistent/modelle.yaml
```

`--arbeitsordner` ist optional und muss auf denselben Ordner zeigen wie beim Web-Lauf (Standard: die Quelle), sonst sieht der Server einen leeren Index. Ollama muss laufen — `suchen` bettet die Frage lokal ein.

Architektur und Testplan: siehe `docs/` (wird mit dem ersten Release ergänzt).

## Kontakt

Fragen, Fehler und Ideen am liebsten als Issue hier im Repository. Für alles andere: built@kifuerdenmittelstand.tech

## Lizenz

MIT, siehe `LICENSE`. Die Modelle (Gemma, Qwen, BGE) und Pakete stehen unter ihren eigenen Lizenzen und werden nicht mitgeliefert.

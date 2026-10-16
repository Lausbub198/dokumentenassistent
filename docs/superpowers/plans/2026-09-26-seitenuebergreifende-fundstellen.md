# Seitenübergreifende Fundstellen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PDF-Seitengrenzen als Chunk-Grenze entfernen, ohne die korrekte PDF-Seitenangabe für Fundstellen und Zitate zu verlieren; danach A/B auf dem privaten Bestand prüfen.

**Architecture:** `Seite` bleibt das Extraktionsergebnis. `zerlege` erhält einen opt-in seitenübergreifenden Modus und erzeugt Chunktext und geordnete Seiten-Spannen gemeinsam. SQLite speichert diese Provenienz; Web/MCP zeigen Einzelseite oder Seitenbereich, während bestehende IDs und Altzeilen lesbar bleiben.

**Tech Stack:** Python 3.13, dataclasses, SQLite, Jinja2, pytest; bestehender lokaler Poppler- und Ollama-Pfad.

**Spec:** `docs/superpowers/specs/2026-09-26-seitenuebergreifende-fundstellen-design.md`

## Global Constraints

- Keine PDF→Markdown-Konvertierung, automatische Überschriftenerkennung oder Änderung von 120/380/30 in diesem Vergleich.
- Seite ist Provenienz, nicht Chunk-Grenze; nie Dokumentgrenzen überschreiten.
- `Fundstelle.seite` und MCP-`seite` bleiben als Startseite kompatibel; additive Spannen/`seiten` geben den vollständigen Bereich an.
- Quellindex, Originale, menschliche Freigaben und bisherige Messartefakte bleiben unverändert.
- Private Texte/Fragen nie in Git oder Berichtsausgaben; neue lokale Embeddings erst nach gesonderter Freigabe.
- Kein Default-Wechsel aus synthetischen Tests oder bloßer Wortlautverfügbarkeit.

## File Structure

- `typen.py`: `SeitenSpanne` und additive `Fundstelle.spannen`/`seiten`.
- `fundstellen.py`: opt-in dokumentweiter Chunker; bestehender seitengebundener Modus bleibt Referenzarm.
- `index.py`: nullable Spannen-Spalte, Validierung, Lesen/Schreiben und Altzeilen-Fallback.
- `werkstatt.py`: opt-in Weiterleitung an den Chunker; keine automatische Aktivierung.
- `suche.py`: optionale Elternseiten-Variante bei Mehrseiten-Chunks fail-closed.
- `mcp_server.py`, `templates/makros.html`, `templates/eingang_detail.html`: Seitenbereich ausgeben, alte Einzelseite unverändert.
- `seitenvergleich.py`: inhaltsfreier, lokaler Strukturvergleich auf zwei Indexkopien; Retrieval-Phase nur nach Embedding-Freigabe.

## Review Focus

1. Leere PDF-Seite zwischen zwei Textseiten: Provenienz nennt nur beitragende Seiten; Task 2 testet dies.
2. Seitenwechsel mitten im Wort oder mit PDF-Trennstrich: keine automatische Dehyphenierung/Zeichen-Erfindung; Task 2 testet den erhaltenen Wortlaut.
3. Überlappende Fenster an einer Seitengrenze: jedes Fenster hat eigene gültige Offsets; Task 2 testet dies.
4. Alter SQLite-Index ohne Spannen-Spalte: Einzelseiten-Zitate bleiben identisch und Vektoren erhalten ihre bisherige Provenienz; Task 1 testet dies.
5. Modell nennt eine unbekannte/mehrdeutige Quellen-ID oder optionaler Elternseitenmodus sieht Mehrseiten-Chunk: keine falsche Quellenzuordnung; Task 3 testet dies.

---

### Task 1: Seiten-Provenienz als persistierter Datenvertrag

**Files:** Modify `src/dokumentenassistent/typen.py`, `src/dokumentenassistent/index.py`; test `tests/test_index_konsistenz.py`, `tests/test_M5_index.py`.

**Interfaces:** Produce `SeitenSpanne(seite:int,start:int,ende:int)`; `Fundstelle.spannen: tuple[SeitenSpanne,...]=()`; `Fundstelle.seiten: tuple[int,...]` returns ordered unique contributing pages or `(seite,)` for legacy. SQLite column `fundstellen.spannen TEXT NULL`, JSON list of triples.

- [ ] **Step 1: Write failing tests.** A two-page `Fundstelle` round-trips through `Index.ersetze_fundstellen` with exact spans; malformed/out-of-range spans fail without modifying prior rows; a legacy DB without the column still returns the old one-page Fundstelle and valid vector provenance; metadata-only span correction preserves the same text vector.
- [ ] **Step 2: Verify red.** Run `.venv/bin/pytest -q tests/test_index_konsistenz.py tests/test_M5_index.py`; the new tests fail for missing model/schema behavior, not setup errors.
- [ ] **Step 3: Implement.** Add types/property, one schema migration in `Index.__init__`, one `_zeile_zu_fundstelle` reader used by all query paths, and atomic span validation/storage in `_speichere_fundstellen`. Do not derive unknown historical page positions from old text.
- [ ] **Step 4: Verify green.** Run the same focused command and then `.venv/bin/pytest -q`.
- [ ] **Step 5: Commit.** `git add src/dokumentenassistent/typen.py src/dokumentenassistent/index.py tests/test_index_konsistenz.py tests/test_M5_index.py` and commit `feat(rag): persist page spans on source chunks`.

### Task 2: Seitenwechsel aus der Chunk-Grenze entfernen

**Files:** Modify `src/dokumentenassistent/fundstellen.py`, `src/dokumentenassistent/werkstatt.py`; test `tests/test_M4_fundstellen.py`, `tests/test_werkstatt.py`.

**Interfaces:** Extend `zerlege(..., seitenuebergreifend: bool=False) -> tuple[Fundstelle,...]`; `Werkstatt.__init__(..., seitenuebergreifend: bool=False)` forwards the option from `auslesen()`. Default remains the unchanged reference arm.

- [ ] **Step 1: Write failing tests.** Two pages with one continuing sentence yield one chunk with both page spans; with `min_woerter=0`, a real blank-line paragraph break remains a break; an empty middle page adds no span; a long paragraph split with 30-word overlap yields correct text and offsets in every window; a trailing PDF hyphen is retained rather than guessed away; two separate files never join. Existing single-page IDs/text remain stable.
- [ ] **Step 2: Verify red.** Run `.venv/bin/pytest -q tests/test_M4_fundstellen.py tests/test_werkstatt.py` and confirm failures specifically in the new mode.
- [ ] **Step 3: Implement.** Build logical text fragments with page and offsets before merging/splitting; construct final text and spans from the same fragments. Keep existing `min_woerter=120`, `max_woerter=380`, `ueberlapp=30`. Do not reconstruct spans by searching repeated text after the fact. Pass the opt-in through Werkstatt without activating it in `modelle.yaml`.
- [ ] **Step 4: Verify green.** Run focused tests and `.venv/bin/pytest -q`.
- [ ] **Step 5: Commit.** Commit only these code/test files as `feat(rag): form chunks across PDF page breaks`.

### Task 3: Zitierausgabe und optionale Suchpfade absichern

**Files:** Modify `src/dokumentenassistent/mcp_server.py`, `src/dokumentenassistent/templates/makros.html`, `src/dokumentenassistent/templates/eingang_detail.html`, `src/dokumentenassistent/suche.py`; test `tests/test_mcp.py`, `tests/test_web.py`, `tests/test_M11_suche.py`.

**Interfaces:** `Fundstelle.seiten` from Task 1; MCP keeps `seite` and adds `seiten` array in Fundstellen/Belegkarten. Web displays `Seite n` or `Seiten n–m` from that property.

- [ ] **Step 1: Write failing tests.** One-page output is byte-for-byte equivalent where public contract requires it; two-page citation displays range in Web and MCP; unknown/ambiguous IDs still yield no card; `suche(..., eltern_seiten>0)` rejects multi-page Fundstellen explicitly instead of attaching a wrong page.
- [ ] **Step 2: Verify red.** Run `.venv/bin/pytest -q tests/test_mcp.py tests/test_web.py tests/test_M11_suche.py`.
- [ ] **Step 3: Implement.** Derive displayed range only from persisted spans; add MCP field without changing `seite`; guard optional parent-page mode at its entry. Do not infer quote-specific page from an ID-only model citation.
- [ ] **Step 4: Verify green.** Run focused tests and `.venv/bin/pytest -q`.
- [ ] **Step 5: Commit.** Commit these code/test files as `fix(rag): cite all pages of cross-page chunks`.

### Task 4: Struktureller Bestandsvergleich ohne Modellaufruf

**Files:** Create `src/dokumentenassistent/seitenvergleich.py`, `tests/test_seitenvergleich.py`; add inhaltsfreien Ergebnisbericht in `../lokalki-lab/docs/messungen/` after the run.

**Interfaces:** CLI takes exact `--quelle`, `--gold`, `--private` paths. It reads originals, writes two new private A/B index copies outside Git, pins SHA-256 for source files/config/code and refuses to overwrite an existing run. It invokes the same extractor once per document and both `zerlege` modes on identical `Seite` values; no Ollama.

- [ ] **Step 1: Write failing tests.** Synthetic two-document Gold fixture proves A/B use identical extracted pages and deterministic IDs; a duplicate output path aborts; report contains counts and question numbers but no question/document text; zero vectors are reported explicitly rather than as retrieval success.
- [ ] **Step 2: Verify red.** Run `.venv/bin/pytest -q tests/test_seitenvergleich.py`.
- [ ] **Step 3: Implement.** Add resumable per-document structural checkpoints with hash checks, aggregate exact/Whitespace-normalized Gold-text availability for 85 positives plus 15 negatives, and refuse private outputs under a Git tree. No embeddings in this task.
- [ ] **Step 4: Verify green.** Run `.venv/bin/pytest -q tests/test_seitenvergleich.py`, the full `.venv/bin/pytest -q`, `git diff --check`, and the structural run on the private working copy. Verify original SQLite SHA unchanged and report only counts/IDs.
- [ ] **Step 5: Commit.** Privacy-scan staged files against private questions, filenames and long answers; commit product runner/tests and the separate Lab report. Leave unrelated `.DS_Store` untouched; do not push.

### Task 5: Gepaarter Retrieval-Test nach ausdrücklicher Embedding-Freigabe

**Files:** Extend `src/dokumentenassistent/seitenvergleich.py`, `tests/test_seitenvergleich.py`; update the Lab report.

**Interfaces:** CLI subcommand `retrieval` consumes only the pinned A/B copies and the fixed Gold set from Task 4. It creates 100 identical local query embeddings for both arms, embeds changed chunks separately, and uses qwen3-embedding:0.6b, BGE reranker, threshold 0.49, top_n 20, no answer-LLM.

- [ ] **Step 1: Write failing tests.** Synthetic vectors/questions prove identical query vectors and configuration in A/B, correct Zielchunk-Rang and Kontexttreffer, stable 15 negative controls, explicit gains/losses, and refusal when hashes/model revision differ.
- [ ] **Step 2: Verify red.** Run `.venv/bin/pytest -q tests/test_seitenvergleich.py` and confirm the new retrieval assertions fail.
- [ ] **Step 3: Implement.** Batch and checkpoint local embeddings by document with revision/text hashes; resume only matching manifests. Score all 85 positive and 15 negative questions, report ranks, context hits, gains/losses, negatives and latency without raw private text.
- [ ] **Step 4: Verify green.** Run focused and full tests, `git diff --check`, then one serialized local A/B run after confirming no competing Ollama job. Verify source index SHA unchanged and 100 unique result IDs per arm.
- [ ] **Step 5: Commit.** Privacy-scan staged code/report, commit both repos separately, do not push. Report no answer-quality claim.

## Handoff and stopping rule

Read this plan and its spec before execution. Execute tasks in order with red/green evidence and review each commit. A retrieval result needs new embeddings for the changed chunks; the earlier explicit restriction remains in force until the user authorizes that local write. If permission is absent, finish Tasks 1–4 and report Task 5 as permission-gated rather than claiming a search-quality gain. No answer-LLM run belongs to this plan.

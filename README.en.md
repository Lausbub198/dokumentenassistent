# Document Assistant

🇩🇪 [Deutsch](README.md) · 🇬🇧 English

A local tool. It reads a folder of documents, proposes a profile (categories, fields, naming scheme), classifies each file with verbatim citations, creates sorted copies **only after human approval**, and answers questions exclusively with verified citations. Originals are never modified.

Models run through Ollama (`modelle.yaml`). No cloud access.

> **Status:** version 0.1, built by one person for their own use, not a finished product. Developed and measured **on macOS only** (MacBook Pro M4 Pro, 24 GB). The code is designed for Linux and Windows but **untested** there. The project was built with AI assistance (Claude).
>
> The configuration file, the code identifiers and the documents under `docs/` and `beweise/` are in German. Everything you need to install and start the tool is in this file.

## Requirements

| What | Why |
|---|---|
| Python 3.13 and [`uv`](https://docs.astral.sh/uv/) | installation and start |
| [Ollama](https://ollama.com) | language model and embedding, both run locally |
| about 13 GB of free memory | `gemma4:12b-it-q4_K_M` (8.1 GB) and `qwen3-embedding:4b` (4.4 GB); with 16 GB only with smaller models, see below |
| internet on the **first** start | the reranker (Hugging Face) and the OCR models (PaddleOCR) are downloaded once; afterwards everything runs offline |

## Quick start

```bash
git clone https://github.com/Lausbub198/dokumentenassistent.git && cd dokumentenassistent
ollama pull gemma4:12b-it-q4_K_M
ollama pull qwen3-embedding:4b
uv sync --extra reranker --extra ocr-paddle   # both extras are enabled in the bundled modelle.yaml
uv run dokumentenassistent                    # opens nothing itself; then open http://127.0.0.1:8765/start in a browser
```

Pick the source folder and the target folder with **Ordner wählen** (choose folder). The target folder must be **outside** the source folder. The originals are never changed; copies are only created after you approve them.

To try it out, `beispiele/malerbetrieb-demo/` contains a synthetic stack of 25 files.

## Configuration

All settings live in `modelle.yaml`, each with a comment and the measurement behind it (tables below). To use a different file, pass it with `--modelle`. The measurement and comparison scripts that work on private data have no fixed paths: `DOKASS_BESTAND`, `DOKASS_ARBEIT`, `DOKASS_FRAGEN`, `DOKASS_LAEUFE` and `DOKASS_GERMANQUAD` set the locations (default `~/dokass-privat/<name>`, see `src/dokumentenassistent/pfade_privat.py`).

## Operating systems

| | Status |
|---|---|
| macOS (Apple Silicon) | developed, measured, tested |
| Linux | untested; `start.command` is a Bash script and should work, otherwise use the `uv run` command above |
| Windows | untested; `start.command` does not run there, use the `uv run` command directly |

The product needs no macOS component: OCR is PaddleOCR (Tesseract as an alternative); Apple Vision only appears in the measurement extra `ocr`. Folder selection happens in the browser, not through a system dialog.

## Tests

```bash
uv run pytest              # module and wiring tests, no model needed
uv run pytest -m e2e       # against a running Ollama and the example corpus
```

## The measured configuration

Every line in `modelle.yaml` is there because it was measured. Evidence is in `beweise/`, reasoning in `docs/` and in the LocalKI Lab measurement reports (`docs/messungen/2026-09-29` to `2026-10-03-phase-d-modellwechsel.md`). Measured on a MacBook Pro M4 Pro, 24 GB, Ollama 0.34.0.

**Questions (as of 2026-10-06)**: a private collection (113 files, 100 gold questions, 15 of them without an answer in the collection) and GermanQuAD (474 Wikipedia paragraphs, 2,204 human-written questions) as a second, independent benchmark:

| Setting | Value | Measurement behind it |
|---|---|---|
| `llm` | `gemma4:12b-it-q4_K_M` | gets 159 of 163 should-be-confident files into the index; the 4B models get 127. What is not classified cannot be found by any search. |
| `embedding` | `qwen3-embedding:4b` | target paragraph in context 64/85 (0.6B) → 73/85 (4B) or 79/85 (8B). In the product path 4B is on par with 8B (62 vs 60 cited answers, 36.6 vs 40.2 s); 8B and gemma do not fit into 24 GB together and are reloaded for each question. |
| `kontext_praefix` | `pfad` | "Document: <relative path>" in front of every chunk, for embedding and reranker only, never in the answer prompt. 74 → 79/85 with 8B. |
| `pdf_extraktion` / `seitenuebergreifend` | `pdftotext_layout` / `true` | chunks span page boundaries; citations carry page ranges (e.g. p. 21–23). 61 → 66/85. |
| Search method | dense, **no BM25/RRF** | every fusion measured was below plain embedding (43–64 % vs 79 % rank 1); German compound words. `docs/retrieval-befund-2026-09-21.md` |
| `reranker` / `rerank_k` | `BAAI/bge-reranker-v2-m3` / 20 | recall@1 79 → 93 %, recall@8 93 → 100 %; GermanQuAD 88 → 98 %. |
| `kontextauswahl` / `top_n` | `dynamisch` / 20 | gemma only reads paragraphs with reranker score ≥ 0.5 × best score (at most 20). A fixed top 20 depends on the order (41 correct in both orders vs 50). |
| `kaskade` / `kaskade_stufe2` | `true` / `streng` | without a valid citation, a second attempt with the top 20 and a strict refusal instruction: 57 answers correct in both orders, 15/15 unanswerable questions refused. |
| `schwelle` | 0 | the earlier similarity threshold 0.49 does not separate answerable from unanswerable questions (C6); on GermanQuAD the old overall configuration refused 70 of 200 answerable questions, probably because of this threshold, but not measured in isolation. |
| `think` | `false` | mandatory: with `low`, Ollama 0.34 puts the answer into the `thinking` field. |
| `kontext` | 32768 | largest answer prompt 18,920 tokens; with 16384, 12 of 100 would be silently truncated. |
| `max_antwort_tokens` | 1024 | without a limit, gemma ran into loops on individual questions until the timeout. |

Result: private collection 62 of 85 answerable questions with a valid citation (baseline 2026-09-29: 43), 15/15 unanswerable questions refused, median 37 s per question; "not found" takes longest (just over 2 min) because both stages are tried first. GermanQuAD: 197 of 200 answers with a citation from the target paragraph (old configuration 129), median 13 s.

**Classifying (as of 2026-09-24)**, measured on 200 documents (242 pages, 694 paragraphs):

| Setting | Value | Measurement behind it |
|---|---|---|
| `timeout` | 900 | seconds per Ollama call. With the previous 120 s the profile proposal aborted over 126 real documents; the same call measured 245 s. |
| `ocr` / `ocr_drehung` | `paddleocr` / `true` | on 10 real scan pages, 7 usable vs 3 with Tesseract, 0 vs 1 page with wrong numbers. `ocr_drehung` switches **only** the page orientation: it straightens the 3 rotated pages (122/97/91 → 495/564/413 characters) and leaves the other 7 unchanged character by character. The other two PaddleOCR preprocessing steps stay off because they measurably hurt. Cost: ~29 s instead of ~1 s per page. `docs/ocr-entscheidung-2026-09-24.md` |
| `ocr_schwelle` | `0.80` | below this value a page does not go to the model. **With straightened pages it effectively refuses nothing except empty results**: after straightening, "usable" and "unusable" overlap (0.975 vs 0.987), the confidence no longer separates them. Why no stricter value anyway: finding, alternative signal and caveat in `docs/ocr-entscheidung-2026-09-24.md`. |

Result of this configuration on the 200 documents (confirmation run 2026-09-24 on a quiet machine, `beweise/last/2026-09-24/bericht.md`): 16.2 s per file, category 89 % correct, status 98.5 % correct, 11 of 640 citations rejected by the citation check (1.7 %), 8 of 8 conflicts found, 8.4 GB memory (still with the 0.6B embedding and `kontext: 16384` at that time; the question numbers of this run are superseded by the table above). Memory today: gemma 8.1 GB + 4B embedding 4.4 GB + reranker in the Python process, which is tight on 24 GB; large programs alongside (video editing, VMs) noticeably slow down every question.

**This does not automatically hold for your own collection.** The ranking of the embeddings flips between two corpora. `python -m dokumentenassistent.retrieval_eval` measures that on your own documents in minutes, without a language model; all it needs is questions whose answer you know.

## OCR is selectable

Since 2026-09-24, images and PDFs without a text layer are read by **PaddleOCR** by default instead of Tesseract (`ocr: paddleocr` in `modelle.yaml`, with `ocr_drehung: true` and `ocr_schwelle: 0.80`). The whole path to that decision (which engines were tested, which two kinds of measurement carry them, why Apple Vision is out despite the best raw values, why only one of PaddleOCR's three preprocessing steps is on, and what remains unmeasured) is in `docs/ocr-entscheidung-2026-09-24.md`.

```bash
uv sync --extra ocr-paddle   # prerequisite for ocr: paddleocr
```

The extra pulls in `paddleocr` and `paddlepaddle` (a full inference framework, including `opencv-contrib-python`, `shapely` and `pandas`). On the **first** run PaddleOCR downloads its models once to `~/.paddlex`; after that everything works offline. If the extra is missing and `ocr: paddleocr` is set, **startup aborts with a message**. There is no silent fallback to Tesseract, because that would be a different measurement setup than the one configured.

If you do not want that, set `ocr: tesseract`. Then `brew install tesseract tesseract-lang` is enough as before; a page costs about one second instead of 29, and reading quality on real scans is measurably worse (3 of 10 usable pages instead of 7). `ocr_sprache` and `ocr_schwelle` adapt to the chosen engine automatically; if you set them yourself, you override both.

## Web interface

The fastest way is a double-click on `start.command` (Finder) or in the terminal:

```bash
./start.command
```

The script first checks that Ollama answers, then starts the server and opens `/start` in the browser. If an instance is already running, it only opens the window.

Or directly:

```bash
uv run dokumentenassistent                                   # choose the collection at http://127.0.0.1:8765/start
uv run dokumentenassistent --quelle /path/to/source --ziel /path/to/target   # open directly
```

Without `--quelle/--ziel`, `/start` asks for the source folder and the target folder (suggestion: `<source>_sortiert`) and remembers the last five collections in `~/.config/dokumentenassistent/zuletzt.json`. Both paths can be typed or pasted (in Finder <kbd>Option</kbd>+<kbd>Cmd</kbd>+<kbd>C</kbd>), or picked with "Ordner wählen…" next to the field: the button opens a window where you click through the folders ("↑ eine Ebene" goes back), "Diesen Ordner wählen" puts the path into the field, <kbd>Esc</kbd> cancels. The list comes from the server (`GET /ordner`, starting in the home directory or at the path already in the field) and contains folder names only, no files and no contents; hidden folders are left out and symlinks are not followed. Without JavaScript the button is absent and the text fields carry the input; the server validates the input anyway. "Stapel einordnen" (classify the stack) runs in the background with progress and cancel; cancelling loses nothing, the next start only takes the files without a proposal.

## MCP server (read-only)

`dokumentenassistent-mcp` provides exactly three tools over stdio: `suchen(frage)`, `fundstelle_lesen(id)`, `datei_oeffnen(fundstelle_id)`. Only what was approved in the web interface is visible; `datei_oeffnen` names the copy in the target folder, never the original. No tool writes, approves or corrects. Every call is logged as a line `art: "mcp"` in `.dokumentenassistent/protokoll.jsonl` (tool, arguments, returned citation IDs, refusals with reason); the start as `mcp_start`.

**To be honest:** citation cards and citation texts go to the MCP client. With Claude Desktop or Claude Code that means the cloud as soon as the model reads them. The collection only stays private with a local client (local LLM, local MCP client, local files).

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dokumentenassistent": {
      "command": "uv",
      "args": [
        "run", "--project", "/path/to/dokumentenassistent", "dokumentenassistent-mcp",
        "--quelle", "/path/to/source",
        "--ziel", "/path/to/target",
        "--modelle", "/path/to/dokumentenassistent/modelle.yaml"
      ]
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add dokumentenassistent -- uv run --project /path/to/dokumentenassistent dokumentenassistent-mcp \
  --quelle /path/to/source --ziel /path/to/target --modelle /path/to/dokumentenassistent/modelle.yaml
```

`--arbeitsordner` is optional and must point to the same folder as in the web run (default: the source), otherwise the server sees an empty index. Ollama must be running, because `suchen` embeds the question locally.

Architecture and test plan: see `docs/` (to be completed with the first release).

## Contact

Questions, bugs and ideas are best raised as an issue here in the repository. For everything else: built@kifuerdenmittelstand.tech

## License

MIT, see `LICENSE`. The models (Gemma, Qwen, BGE) and packages are under their own licenses and are not bundled.

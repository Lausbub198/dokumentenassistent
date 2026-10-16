# Belastungstest — Ausgabeformat

Geschirr: `src/dokumentenassistent/lasttest.py` (Ablauf, CLI) und
`src/dokumentenassistent/lasttest_bericht.py` (Kennzahlen, Bericht).
Tests ohne Modell: `tests/test_lasttest.py` (L1–L6).

```bash
uv run python -m dokumentenassistent.lasttest --korpus beispiele/malerbetrieb \
    --stufen 10 25 50 100 --llm qwen3.5:9b qwen3:4b --embedding bge-m3 --ausgabe beweise/last/
uv run python -m dokumentenassistent.lasttest --korpus beispiele/steuerfall --golden tests/golden.json \
    --stufen 13 --llm qwen3.5:9b
uv run python -m dokumentenassistent.lasttest --bericht beweise/last/2026-09-19/
```

Je `(LLM × Stufe)` ein vollständiger Lauf in frischen Temp-Ordnern (Quelle = Kopie der
Dateien dieser Stufe, Zielablage, Arbeitsordner). Der Korpus wird nur gelesen. Reihenfolge:
äußere Schleife LLM (Modell bleibt geladen), innere Schleife Stufe. Phasen je Lauf:
erfassen → auslesen → profil_vorschlagen(`golden.zweck`) + bestätigen → einordnen →
alle offenen Konflikte mit „ersetzt" entscheiden → freigeben(alle Hashes; die Werkstatt
kopiert nur sichere) → alle Fragen mit `ab_stufe <= stufe`.
Provider: `OllamaProvider(host, embedding, llm, think=False, timeout=900)`.

## Ordner `beweise/last/<YYYY-MM-DD>/`

| Datei | Inhalt |
|---|---|
| `umgebung.md` | einmal je Datum: `ollama --version`, `sw_vers -productVersion`, `hw.model`, `hw.memsize`, `pmset -g batt` (Netzteil ja/nein) |
| `laeufe.jsonl` | eine JSON-Zeile je Lauf, **append-only** — ein Abbruch verliert nur den laufenden Lauf; Wiederholungen hängen an, im Bericht zählt die letzte Zeile je (LLM, Stufe) |
| `bericht.md` | aus `laeufe.jsonl` erzeugt (am Ende jeder Serie automatisch, sonst `--bericht`) |

## Zeile in `laeufe.jsonl`

| Feld | Bedeutung |
|---|---|
| `zeit` | Startzeit (lokal) |
| `stufe`, `llm`, `embedding` | Lauf-Kennung |
| `dateien` | kopierte Dateien der Stufe |
| `seiten` | Seiten mit mindestens einer Fundstelle (Seiten ohne Text zählen nicht) |
| `fundstellen` | Absätze insgesamt |
| `zeit_s` | Sekunden je Phase (`erfassen`, `auslesen`, `profil_vorschlagen`, `einordnen`, `konflikte_entscheiden`, `freigeben`, `fragen`) und `gesamt` |
| `modellaufrufe`, `modellzeit_s` | je Art `embed` / `generate_json` / `generate_text` (Wrapper `Protokollierender`) |
| `status_verteilung` | Zähler `sicher` / `konflikt` / `unklar` / `duplikat` / `ocr_unsicher` nach dem Einordnen |
| `soll_status_treffer` | Anteil golden-Dateien der Stufe (`dateien` + `weitere_dateien`), deren Ist-Status dem Soll entspricht |
| `soll_kategorie_treffer` | Anteil der Dateien mit Ist-Status `sicher` **und** Sollkategorie in golden, deren Kategorie stimmt — misst, ob „sicher" auch richtig ist. Synonymlisten: `profil_muss_enthalten.kategorien` als Dict Kanon → Liste (Malerbetrieb), `synonyme[<Kanon>]`, oder je Datei `kategorie_synonyme` |
| `belege_gesamt` | Felder mit Status `belegt` oder `unklar` (= vom Modell behauptet); `fehlt` zählt nicht; Dateien ohne Modellaufruf (`ocr_unsicher`) außen vor |
| `belege_ungueltig` | davon `unklar` (behauptet, von der Zitatprüfung verworfen) |
| `konflikte_gefunden` / `konflikte_soll` / `konflikte_treffer` | Konflikte nach dem Einordnen; Soll = `golden.konflikte`, deren beide Dateien in der Stufe liegen; Treffer = gleiches Feld und gleiches Dateipaar |
| `fragen` | je Frage `frage`, `status_ist`, `status_soll`, `datei_ist` (erste Belegkarte), `datei_soll`, `treffer`, `dauer_s`. Treffer = Status stimmt und, falls golden eine Datei nennt, eine Karte aus dieser Datei, deren Wortlaut `wortlaut_enthaelt` enthält (wie E8/E9) |
| `fragen_treffer_quote` | Anteil Treffer; `null` ohne Fragen |
| `korrekturen_mensch` | Protokolleinträge `korrektur` (hier immer 0, Feld bleibt) |
| `speicher` | `ollama ps` direkt nach dem Einordnen |
| `fehler` | `null` oder `{phase, typ, text}` — der Lauf endet in dieser Phase, spätere Kennzahlen bleiben `null`/0, der nächste Lauf startet |

## Stufenauswahl

In dieser Reihenfolge:

1. `golden.stufen[str(N)]` ist eine Liste relativer Pfade unter dem Korpus (Malerbetrieb:
   `{"10": ["Downloads/Rechnung (4).pdf", …], "25": […], …}`) → genau diese Dateien.
2. Sonst: trägt mindestens ein golden-Datei-Eintrag `ab_stufe`, gehört eine Datei zur
   Stufe N, wenn `ab_stufe <= N` (Dateien ohne Angabe immer).
3. Sonst: die ersten N Dateien in Pfadreihenfolge (dieselbe Sortierung wie `erfassen`).

Fragen: `ab_stufe <= N` (ohne Angabe immer). `--stufen` fehlt → Schlüssel bzw. Werte von
`golden.stufen`, sonst eine Stufe mit allen Dateien. Korpus: `<korpus>/Quelle/` falls
vorhanden, sonst `<korpus>` selbst (ohne `golden.json`, ohne Punkt-Dateien). golden:
`--golden`, sonst `<korpus>/golden.json`. Unterordner bleiben in der Kopie erhalten;
golden-Einträge und Konfliktpaare werden über den Dateinamen abgeglichen.

## `bericht.md`

Je LLM eine Tabelle, Zeile je Stufe: Dateien · Einordnen s · s/Datei · sicher % · unklar % ·
Kategorie-Treffer % · Belege ungültig/gesamt · Konflikte ist/soll · Fragen-Treffer · Fragen-Dauer Ø.
Zeilen mit `fehler` zeigen Phase und Text statt Kennzahlen. Darunter „Wo es bricht":
Matrix Frage × (LLM @Stufe) mit `grün` (Treffer), `rot` (kein Treffer), `–` (nicht gestellt).

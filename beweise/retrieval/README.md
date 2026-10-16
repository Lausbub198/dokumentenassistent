# Retrieval-Eval — Ausgabeformat

Geschirr: `src/dokumentenassistent/retrieval_eval.py` (Ablauf, CLI) und
`src/dokumentenassistent/retrieval_eval_bericht.py` (Berichtstabelle). Tests ohne Modell
(FakeProvider, kein Ollama): `tests/test_retrieval_eval.py` (R1–R7).

Misst nur `suche.py` (BM25, Dense, Hybrid/RRF) — kein LLM, keine Zitatprüfung. Fundstellen
entstehen wie in `werkstatt.py` (`erfassen` + `auslesen`/`zerlege`), ohne Profil oder
Einordnen.

```bash
uv run python -m dokumentenassistent.retrieval_eval --korpus beispiele/malerbetrieb --stufe 25 \
    --embedding bge-m3 nomic-embed-text qwen3-embedding:0.6b --ausgabe beweise/retrieval/
uv run python -m dokumentenassistent.retrieval_eval --bericht beweise/retrieval/2026-09-20/
```

Ablauf je Lauf: Dateien der Stufe (wie `lasttest.waehle_dateien`) in einen Temp-Ordner
kopiert, `Werkstatt.erfassen()` + `Werkstatt.auslesen()` liefern die Fundstellen (kein
Modellaufruf). BM25-Rangliste je Frage wird **einmal** berechnet (embedding-unabhängig).
Für jedes `--embedding`-Modell: alle Fundstellen-Texte **einmal** einbetten (`embed_sekunden`
misst genau das), danach je Frage ein Embed-Aufruf für den Fragevektor, Dense- und
Hybrid-Rangliste (RRF aus BM25 + Dense).

Seit 21.09. zusätzlich die Eval-Varianten aus `retrieval_varianten.py` (nicht in `suche.py`):
lexikalisch `bm25_komposita` (Frage-Tokens ≥ 8 Zeichen in zwei Bestandswörter zerlegt, Fuge s/n/en) und
`bm25_praefix` (Präfix-Treffer ab 5 Zeichen); je Embedding `hybrid_w0.5`, `hybrid_w0.25` (BM25-Gewicht in
der RRF) und `hybrid_komposita_w1.0`, `hybrid_komposita_w0.5`. Die dense-Liste wird je Embedding einmal
gerechnet und für alle Hybrid-Varianten wiederverwendet. Achtung: der Bericht nimmt je (Variante, Embedding)
die **letzte** Zeile, unabhängig von der Stufe — bei mehreren Stufen in einem Ordner die gewünschte zuletzt laufen.

## Zweiter Korpus seit 22.09.: GermanQuAD (`--germanquad`)

`beispiele/malerbetrieb` ist synthetisch — Dokumente und Fragen stammen aus derselben Quelle,
alle Zahlen oben tragen deshalb Autorenschafts-Bias. `--germanquad` nimmt Fundstellen und
Fragen stattdessen aus `beweise/germanquad/` (fremde Texte, menschliche Fragen, CC-BY-4.0;
Details dort im README). Alles danach ist identisch — dieselben Varianten, Embeddings,
Kennzahlen, derselbe Bericht:

```bash
uv run --extra eval python -m dokumentenassistent.retrieval_eval --germanquad \
    --fragen 200 --embedding qwen3-embedding:0.6b --ausgabe beweise/retrieval/
```

`--fragen N` zieht deterministisch (`--seed`, Standard 42); ohne die Angabe laufen alle 2204
Fragen. `--korpus` und `--germanquad` schließen sich aus. Zusätzliche Felder in der Zeile:
`korpus_quelle: "germanquad"`, `ziehung` (Seed, gezogen, angefordert, Ordner), `absatzgenau`
(Recall@1/5/8 + MRR auf den **Zielabsatz** statt nur auf die Datei) und je Frage
`absatz_soll` / `rang_absatz`. Der Bericht bekommt dann eine zweite Tabelle „Absatzgenau";
bei malerbetrieb fehlt sie, weil `golden.json` dort nur die Datei kennt.

## Ordner `beweise/retrieval/<YYYY-MM-DD>/`

| Datei | Inhalt |
|---|---|
| `laeufe.jsonl` | eine JSON-Zeile je Variante × Embedding, **append-only**; im Bericht zählt die letzte Zeile je (Variante, Embedding) |
| `bericht.md` | aus `laeufe.jsonl` erzeugt (am Ende jedes CLI-Laufs automatisch, sonst `--bericht`) |

## Zeile in `laeufe.jsonl`

| Feld | Bedeutung |
|---|---|
| `datum`, `korpus`, `stufe` | Lauf-Kennung |
| `embedding` | Embedding-Modell; `null` bei der `bm25`-Zeile (embedding-unabhängig) |
| `variante` | `bm25` \| `dense` \| `hybrid` |
| `fundstellenzahl` | Absätze der Stufe, über die gesucht wurde |
| `fragenzahl` | golden-Fragen mit `status == "gefunden"` und `datei` |
| `fragenzahl_nicht_gefunden` | golden-Fragen mit `status == "nicht_gefunden"` |
| `embed_sekunden` | Dauer, alle Fundstellen-Texte einmal einzubetten; `null` bei `bm25` |
| `recall_at_1` / `_5` / `_8` | Anteil der `gefunden`-Fragen, bei denen die erste Fundstelle aus der golden-Datei auf Rang ≤ 1/5/8 liegt |
| `mrr` | Mittelwert von `1/Rang` über die `gefunden`-Fragen (0, wenn die Datei nicht in der Rangliste steht) |
| `nicht_gefunden_treffer_quote` | Anteil der `nicht_gefunden`-Fragen, deren Top-Score unter der Schwelle liegt (`suche.SCHWELLE`, seit 21.09. Kosinus 0.49; davor RRF-Punkte 0.02) — korrekt abgewiesen. Nur für `dense` aussagekräftig |
| `dauer_s_frage_avg` | mittlere Dauer je Frage (Rang-Berechnung, bei `dense`/`hybrid` inklusive Embed-Aufruf für den Fragevektor) |
| `host` | `--host`, wie im CLI übergeben |
| `fragen` | je `gefunden`-Frage `frage`, `datei_soll`, `rang` (`null` = nicht in der Rangliste), `treffer_at_8`, `top_score` (Score des Top-Absatzes, seit 21.09.), `dauer_s` — Basis für „Wo es bricht" |
| `nicht_gefunden_fragen` | je `nicht_gefunden`-Frage `frage`, `top_score` (seit 21.09.) — Datengrundlage für die Schwelle in `suche.py` |

## `bericht.md`

Eine Tabelle Variante × Embedding (Fundstellen, Embed s, Recall@1/5/8, MRR,
Nicht-gefunden-Quote, Dauer/Frage). Darunter „Wo es bricht": je golden-Frage der Rang in
jeder (Variante, Embedding)-Spalte — Zahl, `nicht gefunden` (Datei nicht in der Rangliste)
oder `–` (Frage nicht Teil dieses Laufs).

## Bekannte Abweichung vom Auftrag

Die Ollama-Version wird **nicht** erfasst, obwohl der Brief das für „billig abfragbar"
vorsieht — `ollama --version` ist trotzdem ein `ollama`-Kommando, und die harte Regel
während des Baus (kein einziger Aufruf an `localhost:11434`, kein `ollama`) galt strenger
als das „billig". `host` bleibt der einzige Umgebungs-Hinweis in der Zeile.

# GermanQuAD — unabhängiger Prüfstein für das Retrieval

## Warum diese Dateien hier liegen

Der bisherige Goldstandard `beispiele/malerbetrieb` ist **synthetisch**: Dokumente *und*
Fragen wurden von derselben Quelle erzeugt (`beispiele/malerbetrieb/README.md`: „Alles frei
erfunden", `erzeugen.py`/`texte.py`, 19.09.2026). Wer den Text schreibt, den die eigene Frage
treffen soll, misst am Ende die eigene Wortwahl. Alle Retrieval-Zahlen aus
`docs/retrieval-befund-2026-09-21.md` tragen deshalb maximalen **Autorenschafts-Bias**.

Hier ist es umgekehrt, und **das ist der Zweck**: die Texte sind deutsche Wikipedia-Absätze,
die Fragen haben menschliche Annotatoren dazu geschrieben — beides von Dritten, beides ohne
Kenntnis dieses Projekts, dieses Retrievers und dieser Embedding-Modelle.

## Quelle und Lizenz

| | |
|---|---|
| Datensatz | GermanQuAD (deepset), hier der MTEB-Spiegel im BEIR-Format |
| Lizenz | **CC-BY-4.0** (Urheber: deepset GmbH; Texte aus der deutschen Wikipedia) |
| Abrufdatum | 22.09.2026 |
| Form | drei Arrow-IPC-Stream-Dateien, unverändert übernommen |

Die Dateien werden **nur gelesen**. Sie werden nicht verändert, nicht neu geschnitten und
nicht als eigene Arbeit ausgegeben.

## Inhalt

| Datei | Zeilen | Spalten |
|---|---|---|
| `corpus.arrow` | 474 | `_id`, `text` — je Zeile ein Wikipedia-Abschnitt |
| `queries.arrow` | 2204 | `_id`, `text` — je Zeile eine menschliche Frage |
| `qrels.arrow` | 2204 | `query-id`, `corpus-id`, `score` — welche Frage welchen Absatz belegt |

Mehrere Fragen können denselben Absatz belegen (2204 Fragen auf 474 Absätze).

## Wie es ins Eval kommt

`src/dokumentenassistent/germanquad.py` liest die drei Dateien und liefert
`(fundstellen, fragen)` in genau den Typen, die `retrieval_eval.py` schon benutzt.
**Kein Chunking** — die Korpuszeilen *sind* die Absätze; eine Zeile wird zu genau einer
`Fundstelle` (`seite=1`, `absatz=1`, `id` = `datei_name` = Korpus-`_id`). Ein erneutes
Zerlegen würde die Soll-ID auf mehrere Fundstellen verteilen und den absatzgenauen
Treffer zerstören.

```bash
uv run --extra eval python -m dokumentenassistent.retrieval_eval --germanquad \
    --fragen 200 --embedding qwen3-embedding:0.6b --ausgabe beweise/retrieval/
```

`--fragen N` zieht deterministisch (Seed 42, `--seed` änderbar); die Ziehung steht als Feld
`ziehung` in jeder Ergebniszeile. Ohne `--fragen` laufen alle 2204 Fragen.

## Was hier messbar ist, was bei malerbetrieb nicht messbar war

Die Soll-Angabe ist der **Absatz**, nicht die Datei. Der Bericht weist beides getrennt aus:
`recall_at_*` (dateigenau, wie bisher) und die Tabelle „Absatzgenau" (`absatzgenau` in der
JSONL-Zeile). Bei diesem Korpus fallen beide Zahlen bauartbedingt zusammen — eine Korpuszeile
ist genau eine Fundstelle. Bei malerbetrieb gibt es den absatzgenauen Maßstab gar nicht:
`golden.json` nennt nur die Datei, und ein Dokument hat viele Absätze.

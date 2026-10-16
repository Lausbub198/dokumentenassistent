# Retriever-Maßnahmen: Herangehensweise, bevor gemessen wird (21.09.2026)

> **Historisch, Stand 21.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


## Warum überhaupt

Der Retrieval-Eval vom 21.09. (`retrieval-befund-2026-09-21.md`) hat drei Dinge gezeigt, die der Lasttest bei 25
Dateien nicht sehen konnte:

1. Bei 200 Dateien steht die richtige Datei mit dem heutigen Hybrid (BM25 + bge-m3, RRF gleichgewichtet) nur in
   **57 %** der Fragen auf Rang 1 — mit bge-m3 **allein** wären es **71 %**. Das heutige BM25 macht das Ergebnis
   schlechter, nicht besser.
2. Das Embedding-Modell entscheidet: qwen3-embedding:0.6b 79 % Rang 1, bge-m3 71 %, nomic 29 %.
3. Eine von 14 Fragen findet **kein** Verfahren unter den ersten acht („Farben-Meister-Rechnung vom 14. August",
   bester Rang 7). Für diese Frage ist jedes Sprachmodell chancenlos.

Warum Rang 1 zählt, obwohl acht Absätze in den Prompt kommen: kleine Modelle gewichten die ersten Absätze stärker
(„lost in the middle"), und die Zitatpflicht verlangt, dass die *richtige* Stelle zitiert wird — nicht irgendeine
ähnliche. Recall@8 = 93 % sagt „die Antwort ist im Prompt", Rang 1 sagt „das Modell sieht sie zuerst".

## Grundsatz

**Erst messen, dann in den Produktcode.** Alle Varianten werden ausschließlich im Eval (`retrieval_eval.py`) gebaut
und gegen denselben Goldstandard (`beispiele/malerbetrieb/golden.json`, Stufe 200, 14 Fragen) gemessen. `suche.py`
bleibt unverändert, bis die Zahlen eine Variante rechtfertigen. Das Eval braucht kein Sprachmodell, läuft in
Sekunden, ist deterministisch — Änderungen am Retriever lassen sich damit beliebig oft prüfen, ohne eine Nacht.

Bewertet wird pro Variante: Recall@1, Recall@5, Recall@8, MRR über 14 Fragen. Entscheidungsregel: eine Maßnahme wird
empfohlen, wenn sie **Rang 1 oder MRR verbessert und Recall@8 nicht senkt**. Unterschiede von einer Frage (7 Punkte
bei 14) sind Rauschen und werden als solches benannt; Unterschiede von zwei und mehr Fragen zählen.

## Die drei Maßnahmen und ihre Hypothesen

### M1 — RRF-Gewichtung: BM25 herabgewichten oder weglassen

*Hypothese:* Reciprocal Rank Fusion addiert `1/(k+Rang)` beider Listen gleichgewichtet. Wenn BM25 die richtige
Datei auf Rang 45 hat, zieht es sie im Hybrid von Rang 1 herunter. Ein Gewicht `w` für die BM25-Liste
(`w/(k+Rang)`) mit `w < 1` sollte Rang 1 in Richtung des reinen Embeddings bewegen, ohne die Fälle zu verlieren, in
denen BM25 allein trifft (Tiefengrund, Rahmenvertrag: Rang 1).

*Gemessen wird:* `w ∈ {1.0 (heute), 0.5, 0.25, 0 (= nur dense)}` für bge-m3 und qwen3-embedding.

*Erwartung, nicht Behauptung:* Rang 1 steigt mit sinkendem `w` Richtung 71 % (bge-m3) bzw. 79 % (qwen3-emb);
Recall@8 bleibt 93 %. Falls ein mittleres `w` Recall@5 hält *und* Rang 1 hebt, ist das der Kandidat.

### M2 — Embedding-Modell wechseln

*Hypothese:* qwen3-embedding:0.6b trifft auf deutschen Geschäftsdokumenten besser als bge-m3 (79 vs 71 % Rang 1,
gemessen). Kosten: Embed-Zeit 21 s statt 11 s je 694 Absätze — einmalig beim Einlesen; Modell 639 MB statt 1,2 GB.

*Gemessen wird:* nichts Neues — die Zahlen liegen vor. M2 wird in Kombination mit M1 und M3 mitgeführt, damit die
Empfehlung am Ende eine **Kombination** ist, nicht drei Einzelbefunde.

### M3 — BM25 deutschfähig machen: Komposita zerlegen

*Hypothese:* BM25 versagt, weil die Frage „Telefonrechnung" sagt und das Dokument „Telefon" und „Rechnung" — für
eine Wortsuche zwei fremde Wörter. Wenn jedes Fragewort zusätzlich auf die **Teilwörter** trifft, die im Bestand
als eigene Wörter vorkommen (Telefonrechnung → telefon, rechnung), sollte BM25 diese Fälle finden.

*Wie (nur im Eval):* Vokabular des Bestands aufbauen (alle Tokens ≥ 4 Zeichen). Für jedes Fragewort ≥ 8 Zeichen
prüfen, ob es sich lückenlos aus zwei Vokabular-Tokens zusammensetzen lässt (mit optionalem Fugen-s/-n/-en:
„Rechnung**s**nummer"); wenn ja, die Teile als zusätzliche Frage-Tokens aufnehmen. Kein Wörterbuch, kein Modell,
deterministisch, nur Zeichenketten und der eigene Bestand. Zusätzlich eine einfache Variante zum Vergleich:
Präfix-Treffer (Fragewort trifft Dokumentwort, wenn eines Präfix des anderen ist, ≥ 5 Zeichen).

*Gemessen wird:* `bm25_komposita` allein, und im Hybrid mit `w ∈ {1.0, 0.5}` je Embedding.

*Erwartung:* BM25 allein steigt von 21/36/43 deutlich (die drei Telefonrechnung-/Kita-Fälle rutschen von Rang
39–52 nach vorn). Ob es im **Hybrid** dann etwas beiträgt, was das Embedding nicht ohnehin trifft, ist die
eigentliche Frage — dafür wird die Frage „14. August" beobachtet, die bisher niemand fand.

## Was danach passiert

Ergebnis in `beweise/retrieval/2026-09-21/` (append-only, neue Varianten-Namen) und als Tabelle in
`retrieval-befund-2026-09-21.md` (Nachtrag). Empfehlung als eine Kombination (Embedding × Gewicht × BM25-Variante)
mit Zahlen. **Erst dann** — und nur nach Freigabe — wandert die Kombination nach `suche.py`, mit dem Eval als
Regressionstest. Jede spätere Retriever-Änderung läuft über dasselbe Eval, bevor sie den Assistenten erreicht.

## Was nicht gemacht wird

- Kein Wechsel des Chunkings: Absätze mit Adresse sind die Grundlage der Zitatprüfung; das Eval kann Chunking-Varianten
  später ebenso messen, aber nicht in dieser Runde (eine Variable zur Zeit).
- Kein zweiter Korpus in dieser Runde — Vergleichbarkeit mit den bisherigen Zahlen geht vor.

## Reranker (M4)

*Warum jetzt doch:* M1–M3 haben die „14. August"-Frage nicht gelöst (bester Rang 6, sonst 7–13) — genau die
Bedingung, unter der dieses Dokument den Reranker oben noch zurückgestellt hat. dense@qwen3-embedding liegt bei
Recall@8 93 % (13/14 Fragen unter den ersten acht) aber Rang 1 nur 79 % (11/14) — drei Fragen liegen auf Rang
6–13, nicht auf 1.

*Hypothese:* Ein Cross-Encoder, der Frage und Absatz gemeinsam liest statt zwei getrennte Embeddings per Kosinus
zu vergleichen, kann die Top-k der dense-Liste feiner ordnen und diese drei Fragen Richtung Rang 1 ziehen. Er ist
der einzige noch nicht gemessene Hebel für Fragen, die dense nicht auf Rang 1 hat.

*Gebaut (nur im Eval, `suche.py` unverändert):* `src/dokumentenassistent/retrieval_reranker.py`
(`Reranker`-Protocol, `CrossEncoderReranker` über `sentence_transformers.CrossEncoder`, reine Funktion `rerank`),
Varianten `dense_rerank_<kurzname>_k<K>` für `K ∈ {8, 20}` je Embedding in `retrieval_eval.py`
(`--reranker <hf-id> ...`, Default: keiner → heutiges Verhalten unverändert).

*Was gemessen wird:* Recall@1/5/8, MRR wie bei jeder Variante, zusätzlich `rerank_sekunden` je Frage (reine
Cross-Encoder-Zeit, ohne Embed). Zwei Modelle: `BAAI/bge-reranker-v2-m3` und `Qwen/Qwen3-Reranker-0.6B` — beide
laden als `CrossEncoder` und liefern trennscharfe Scores (Trockenlauf, 3 Sätze, MPS): bge-reranker-v2-m3
`[0.9949, 0.000016, 0.000016]` in 1,55 s (Modell-Ladezeit 147 s, einmalig), Qwen3-Reranker-0.6B
`[9.81, -10.19, -10.13]` (rohe Logits, kein Sigmoid — für `rerank()` irrelevant, es sortiert nur absteigend) in
1,02 s (Ladezeit 134 s). Beide trennen den passenden Satz klar von den beiden unpassenden.

*Entscheidungsregel wie bei M1–M3:* eine Reranker-Variante wird empfohlen, wenn sie gegenüber
`dense@qwen3-embedding` (79/93/93, MRR 0,863) Rang 1 oder MRR verbessert und Recall@8 nicht senkt. Unterschiede
von einer Frage (7 Punkte bei 14) sind Rauschen, siehe die „Kita Sonnenschein"-Beobachtung oben.

*Kosten:* ein zusätzliches Modell im Speicher — bge-reranker-v2-m3 ≈ 1,1 GB, Qwen3-Reranker-0.6B ≈ 0,6 GB (beide
Sentence-Transformers-Downloads, nicht Teil des Produkts: `[project.optional-dependencies] reranker` in
`pyproject.toml`, `suche.py` importiert das Modul nicht). Latenz je Frage: im Trockenlauf 1,0–1,6 s für drei
Sätze auf MPS — bei `top_k=8` bzw. 20 Absätzen entsprechend mehr; das Eval misst das je Frage
(`rerank_sekunden`) und in der Berichtstabelle (`Dauer/Frage s`).

*Messkommando (heute Abend, nicht jetzt — Ollama gehört dem Filmdreh):*

    uv run --extra reranker python -m dokumentenassistent.retrieval_eval --korpus beispiele/malerbetrieb \
        --stufe 200 --embedding qwen3-embedding:0.6b bge-m3 \
        --reranker BAAI/bge-reranker-v2-m3 Qwen/Qwen3-Reranker-0.6B --ausgabe beweise/retrieval/

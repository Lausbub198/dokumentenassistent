# Retrieval-Eval, 21.09.2026: drei Embeddings, drei Varianten, zwei Bestandsgrößen

> **Historisch, Stand 21.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Messung: `python -m dokumentenassistent.retrieval_eval --korpus beispiele/malerbetrieb --stufe 25|200`,
Ollama 0.34.0, kein LLM beteiligt. Sollwerte: `golden.json` (`fragen[].datei`). Treffer = die Datei der
Fundstelle auf Rang r ist die Soll-Datei. Ergebnis in `beweise/retrieval/2026-09-21/`.

## Stufe 25 (25 Dateien, 9 Fragen mit Soll-Datei)

Alles trifft. Hybrid mit jedem Embedding: Recall@1 = 100 %. Dense allein 89 % (bge-m3, nomic), 100 %
(qwen3-embedding). BM25 allein 67 % Recall@1, aber 100 % Recall@5. **Bei 25 Dateien unterscheidet sich nichts —
deshalb war der Lasttest bisher blind für den Retriever.**

## Stufe 200 (200 Dateien, 694 Fundstellen, 14 Fragen)

| Variante | Embedding | Recall@1 | Recall@5 | Recall@8 | MRR | Embed s (694) |
|---|---|---|---|---|---|---|
| bm25 | – | 21 | 36 | **43** | 0.32 | – |
| dense | bge-m3 | 71 | 86 | 93 | 0.78 | 11.1 |
| dense | nomic-embed-text | 29 | 64 | 79 | 0.44 | 4.9 |
| dense | **qwen3-embedding:0.6b** | **79** | **93** | 93 | **0.86** | 20.8 |
| hybrid | bge-m3 | 57 | 93 | 93 | 0.69 | 11.1 |
| hybrid | nomic-embed-text | 36 | 79 | 93 | 0.56 | 4.9 |
| hybrid | qwen3-embedding:0.6b | 50 | 86 | 93 | 0.66 | 20.8 |

## Drei Befunde

**1. Das Embedding-Modell entscheidet — bei 200 Dateien, nicht bei 25.** qwen3-embedding:0.6b (79 % Rang 1) vor
bge-m3 (71 %) vor nomic-embed-text (29 %). nomic ist das kleinste und schnellste, aber auf deutschen
Rechnungen unbrauchbar: „Telefonrechnung März" auf Rang 10, „Farben-Meister-Rechnung 14. August" auf Rang 18.

**2. BM25, wie es heute im Code steht, trägt bei 200 Dateien fast nichts.** Recall@8 43 %. Die Ursache steht in
„Wo es bricht": *Telefonrechnung* → Rang 45, *Kita Sonnenschein* → Rang 52, *Telefonrechnung Oktober* → Rang 39.
Deutsche Komposita: die Frage sagt „Telefonrechnung", die Rechnung sagt „Telefon" und „Rechnung" — für BM25 zwei
fremde Wörter. Und die Behauptung „BM25 ist unschlagbar bei Rechnungsnummern" gilt nur, wenn die **Frage** die
Nummer enthält. Fragt man *nach* der Nummer („Welche Rechnungsnummer mahnt Farben Meister an?"), hat BM25 nichts
zum Suchen: Rang 21. BM25 gewinnt genau dort, wo die Frage den Wortlaut des Dokuments trifft (Tiefengrund,
Rahmenvertrag: Rang 1) — das ist die Ausnahme, nicht die Regel.

**3. Hybrid per RRF gleichgewichtet verschlechtert Rang 1.** bge-m3: dense 71 % → hybrid 57 %. qwen3-embedding:
79 % → 50 %. Reciprocal Rank Fusion addiert Plätze; wenn eine der beiden Listen (BM25) die richtige Datei auf
Platz 45 hat, zieht sie die andere herunter. Hybrid hilft nur bei Recall@5 (bge-m3 86 → 93) — es rettet, was dense
knapp verfehlt, und verdirbt, was dense sicher hatte. Bei acht Absätzen im Prompt (Recall@8) ist es egal: 93 % so oder so.

## Was das für den Assistenten heißt (nicht gebaut, nur benannt)

- **Embedding wechseln** auf `qwen3-embedding:0.6b` (639 MB, Embed-Zeit 21 s je 694 Absätze — einmalig beim Einlesen)
  oder bge-m3 behalten (11 s, 71/86/93). nomic streichen.
- **BM25 reparieren, bevor es im Hybrid mitstimmt**: Komposita zerlegen oder Teilwort-Treffer zulassen (Trigramme,
  einfaches Stemming) — oder BM25 im RRF geringer gewichten, solange es nicht deutschfähig ist. Beides messbar mit
  demselben Eval, ohne LLM, in Minuten.
- **Recall@8 = 93 % heißt: eine von 14 Fragen ist für das Sprachmodell unlösbar**, egal wie gut es ist
  („Farben-Meister-Rechnung vom 14. August", bester Rang 7 mit bge-m3 dense, sonst 9–20). Fehler in der Antwort sind
  ab hier zuerst Retriever-Fehler, dann Modellfehler — so wie Runtime-Effekte zuerst Runtime sind, nicht Modell.
- **Der Lasttest Stufe 25 misst den Retriever nicht** (alles 100 %). Modellunterschiede bei Stufe 25 sind reine
  Modellunterschiede; ab Stufe 100/200 mischt der Retriever mit. Die Finalisten-Nacht (Stufe 100/200) ist mit dieser
  Tabelle zu lesen.

## Nachtrag (21.09., abends): M1–M3 gemessen — gewichtete RRF, BM25-Komposita, BM25-Präfix

Varianten nur im Eval (`retrieval_varianten.py`), `suche.py` unverändert. Gleicher Korpus, gleiche 14 Fragen,
bge-m3 und qwen3-embedding:0.6b (nomic nicht erneut gemessen — Zahlen oben). Kontrolle Stufe 25: jede Hybrid-Variante
100/100/100, BM25 allein 67 → 78 (komposita) → 89 (präfix) Rang 1; nichts bricht. Rohdaten append-only in
`beweise/retrieval/2026-09-21/laeufe.jsonl` (44 Zeilen), Bericht `bericht.md`.

### Stufe 200: alle Varianten × Embedding (Recall@1 / @5 / @8 in %, MRR)

`hybrid` = heutiger Code (RRF, w=1.0). `hybrid_w<X>`: BM25-Liste mit Gewicht w in der RRF, dense 1.0.
`hybrid_komposita_w<X>`: dasselbe mit `bm25_komposita` statt `bm25`. w=0 wäre `dense`.

| Variante | Embedding | R@1 | R@5 | R@8 | MRR |
|---|---|---|---|---|---|
| bm25 (heute) | – | 21 | 36 | 43 | 0.321 |
| bm25_komposita | – | 29 | 50 | 57 | 0.405 |
| bm25_praefix | – | 21 | 50 | 57 | 0.364 |
| dense | bge-m3 | 71 | 86 | 93 | 0.779 |
| dense | **qwen3-embedding:0.6b** | **79** | **93** | 93 | **0.863** |
| hybrid (heute) | bge-m3 | 57 | 93 | 93 | 0.689 |
| hybrid (heute) | qwen3-embedding:0.6b | 43 | 86 | 93 | 0.622 |
| hybrid_w0.5 | bge-m3 | 57 | 93 | 100 | 0.713 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 50 | 93 | 93 | 0.655 |
| hybrid_w0.25 | bge-m3 | 57 | 93 | 100 | 0.711 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 57 | 93 | 93 | 0.720 |
| hybrid_komposita_w1.0 | bge-m3 | 64 | 93 | 93 | 0.731 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 57 | 93 | 93 | 0.720 |
| hybrid_komposita_w0.5 | bge-m3 | 64 | 93 | 100 | 0.748 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 64 | 93 | 93 | 0.744 |

**Rauschen, gemessen:** `hybrid@qwen3` stand heute Morgen bei 50 %, jetzt bei 43 % — gleicher Code
(`rrf_gewichtet` mit w=1.0 ist identisch zu `rrf`, per Test), gleiche 14 Fragen. Eine Frage („Kita Sonnenschein")
rutschte von Rang 1 auf 2, weil die dense-Liste *unterhalb* von Rang 1 anders sortiert war (Ollama-Embeddings
sind nicht bitgleich; die RRF verstärkt das). Die 7-Punkte-Regel aus dem Maßnahmen-Dokument ist damit keine
Konvention, sondern beobachtet.

### Wo es bricht — die vier beobachteten Fragen (Rang der Solldatei)

| Frage | bm25 | bm25_komp. | bm25_präfix | dense bge | dense qwen3 | hybrid bge | hybrid qwen3 | hyb_w0.25 bge | hyb_komp_w0.5 bge | hyb_komp_w0.5 qwen3 |
|---|---|---|---|---|---|---|---|---|---|---|
| Telefonrechnung März 2025 | 45 | 45 | 45 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Rechnung an die Kita Sonnenschein | 52 | 52 | 53 | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| Telefonrechnung Oktober 2025 | 39 | 39 | 39 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Farben-Meister-Rechnung vom 14. August | 21 | 21 | 19 | **7** | 13 | 9 | 13 | **6** | **7** | 12 |

### Befunde

**1. M3 (Komposita) trifft die Hypothese nicht — die Hypothese war falsch.** Die drei Telefonrechnung-/Kita-Ränge
bleiben bei 45/52/39. Nachgesehen in den Dokumenten: „Telefon März.pdf" enthält das Wort *Telefon* nicht — es
sagt „NeuKom Telekommunikation", „Festnetz", „Mobilfunk". *Telefonrechnung* kommt in 0 von 694 Absätzen vor,
*telefon* als Teilwort ebenfalls nicht im Zieldokument. Das ist ein semantischer Treffer, kein lexikalischer;
kein Zerlegen und kein Präfix kann ihn liefern. „Kita Sonnenschein" ist der andere Fall: *sonnenschein* steht im
Zieldokument (2 Absätze im Bestand, IDF 5,6) — und die Solldatei landet trotzdem auf Rang 52, hinter drei
`Police.pdf`-Paragraphen, die keines der seltenen Wörter enthalten. Ursache: die Stoppwörter der Frage („die",
„an", „hat", „welchen") zählen bei BM25 mit, und die Längennormierung (b = 0,75) drückt den langen
Rechnungs-Absatz. Komposita hilft dort, wo die Frage ein Kompositum trägt, das der Bestand in Teilen kennt:
„Zahlungserinnerung" → zahlung, erinnerung (Rechnungsnummer-Frage 21 → 1), „Korrekturrechnung" → korrektur,
rechnung (Vogel-Frage 10 → 2). BM25 allein: 21/36/43 → 29/50/57. „Rechnungsnummer" wurde *nicht* zerlegt,
weil *nummer* im Bestand nicht als eigenes Wort vorkommt (nur „Kundennummer", „Nr.").

**2. M1 (Gewicht) glättet, aber holt das Embedding nicht ein.** Mit bge-m3 steigt Rang 1 durch w<1 gar nicht
(57 → 57), nur MRR (0.689 → 0.713) und die „14. August"-Frage rückt von 9 auf 6/7 — also Recall@8 100 %,
aber das ist genau eine Frage. Mit qwen3 steigt Rang 1 von 43 auf 57 (w=0.25), bleibt aber 3 Fragen unter
`dense` (79). **Jede** Fusion mit BM25 — heutiges BM25 oder Komposita, w 1.0 bis 0.25 — liegt bei qwen3 unter
dem reinen Embedding: 43–64 % gegen 79 %. BM25 in jeder gemessenen Form nimmt qwen3 Rang-1-Treffer weg, weil
seine Rangliste bei diesen Fragen aus Stoppwort-Treffern besteht.

**3. „14. August" löst keine Variante.** Bester Rang 6 (`hybrid_w0.25@bge-m3`), sonst 7–13. Grund gesehen: das
Dokument sagt „14.08.2025", die Frage „14. August" — *august* steht in 2 Absätzen des Bestands, keiner davon
die Solldatei. Lexikalisch ist das eine Datums-Normalisierung (nicht Teil dieser Runde), dense findet es nur
mittelbar über „Farben Meister" + „Rechnung", was 26 Dokumente teilen.

### Empfehlung — eine Kombination

**qwen3-embedding:0.6b × w = 0 × kein BM25** — also `dense` allein: **79 / 93 / 93, MRR 0.863** gegen heute
`hybrid@bge-m3` 57 / 93 / 93, MRR 0.689. Nach der Entscheidungsregel: Rang 1 +22 Punkte (3 Fragen, nicht
Rauschen), MRR +0.17, Recall@8 gleich. Keine gemessene Fusion kommt näher als 15 Punkte an Rang 1 heran
(`hybrid_komposita_w0.5`: 64). Zweitbester Kandidat, wenn bge-m3 bleiben soll: `hybrid_komposita_w0.5@bge-m3`
64 / 93 / 100, MRR 0.748 (+1 Frage Rang 1 = Rauschen, +1 Frage Recall@8 = Rauschen, MRR +0.06 — schwach, aber
nicht schlechter in irgendeiner Spalte).

Was diese Empfehlung **nicht** sagt: dass BM25 überflüssig ist. Es sagt, dass BM25 *in dieser Form* — mit
Stoppwörtern in der Frage und b = 0,75 — bei 200 Dateien nichts beiträgt, was qwen3 nicht schon hat. Eine
Diagnose ohne Ollama (kein Eval-Lauf, keine neue Variante, nur `_bm25_scores` mit Frage-Tokens ≥ 4 Zeichen):
BM25 allein geht von 21/36/**43** auf 14/64/**93** Recall@8; Telefonrechnung März 45 → 4, Kita Sonnenschein
52 → 6, Kita Regenbogen 34 → 5, Ahornstraße 14 → 1. Das ist der nächste Hebel, wenn BM25 im Hybrid bleiben
soll — er ist hier **nicht** als Variante gemessen und nicht im Hybrid geprüft; Rang 1 sinkt dabei (21 → 14),
weil kurze Tokens wie „3-5" oder „14" verloren gehen.

### Bevor irgendetwas nach `suche.py` wandert

- **Die Schwelle 0,02 ist an w=1 und zwei Listen gebunden.** RRF-Punkte eines Absatzes, der nur in *einer*
  Liste steht, sind höchstens 1/61 = 0,0164 < 0,02. Heute heißt das: der Top-Absatz muss auch in der BM25-Liste
  auftauchen (bis Rang ~217), sonst „nicht gefunden". Mit w=0.5 muss er in BM25 unter Rang ~78 stehen, mit
  w=0.25 unter Rang ~9 — daher die „Nicht-gefunden-Quote" 50 % / 100 % in `bericht.md` für diese Varianten: die
  Schwelle beißt, nicht die Erkennung. Und `dense` allein hätte mit 1/61 **nie** einen Treffer über der
  Schwelle. Wer die Empfehlung umsetzt, muss die Schwelle neu ableiten (z. B. auf Kosinus statt RRF-Punkte)
  und die `nicht_gefunden`-Fragen erneut messen — bei allen heutigen Varianten liegt die Quote bei 0 %, die
  Schwelle unterscheidet bei 200 Dateien also ohnehin nichts.
- Eval als Regressionstest: `uv run python -m dokumentenassistent.retrieval_eval --korpus beispiele/malerbetrieb
  --stufe 200 --embedding qwen3-embedding:0.6b` muss nach der Umstellung 79/93/93 ± 1 Frage zeigen.

## Umgesetzt (21.09., nach Freigabe): dense allein, Kosinus-Schwelle, qwen3-embedding:0.6b

**Was geändert wurde.** `suche.py::suche` ruft nur noch `dense_rang` — kein `bm25_rang`, keine `rrf` im Suchpfad.
Beide Funktionen bleiben im Modul, weil `retrieval_eval.py` sie weiter als Vergleichsvarianten misst.
`modelle.yaml`: `embedding: qwen3-embedding:0.6b` (bge-m3 als kommentierte Alternative mit Zahlen). Tests: der
Bag-of-Words-FakeProvider liefert jetzt Kosinus statt RRF-Punkte; Einwort-Fragen („Heizung", 0.333) fallen
korrekt unter die Schwelle, die Fixture-Fragen tragen deshalb mehr Treffer-Wörter. Neu: „Top-Kosinus unter
Schwelle → nicht_gefunden ohne Modellaufruf" und „suche ruft kein BM25/RRF" (monkeypatch). `uv run pytest -q`:
272 passed. `lasttest_bericht.py` gruppiert Läufe jetzt nach LLM · Embedding, damit der neue Lauf den alten
(bge-m3, hybrid) in `bericht.md` nicht überschreibt.

**Schwelle: 0.49 Kosinus, abgeleitet aus Daten.** `retrieval_eval` schreibt seit heute je Frage den `top_score`
(auch für `nicht_gefunden`-Fragen, Feld `nicht_gefunden_fragen`). Stufe 200, qwen3-embedding:0.6b, dense:

| Klasse | Frage | Top-Kosinus |
|---|---|---|
| gefunden (niedrigste) | Kita Sonnenschein; Rollgerüst Bahnhofstraße 3 | **0.5062** |
| gefunden (nächste) | Farben-Meister 14. August (Rang 13) | 0.5298 |
| nicht_gefunden (höchste) | Alarmanlage Sicherheitsfirma | **0.5161** |
| nicht_gefunden (nächste) | Dachdecker | 0.4844 |
| nicht_gefunden | Photovoltaik / Bagger | 0.4719 / 0.3990 |

**Die Bereiche überlappen**: die Alarmanlage-Frage (0.5161) liegt über zwei gefunden-Fragen (0.5062). Eine
Schwelle, die alle vier nicht_gefunden-Fragen abweist, würde zwei echte Treffer verlieren. Entscheidung Recall vor
Abweisung: 0.49 liegt 0.016 unter der niedrigsten gefunden-Frage und 0.006 über der nächsten nicht_gefunden-Frage.
Die Alarmanlage-Frage passiert die Schwelle; sie wird vom Modell („nicht gefunden") plus Zitatprüfung abgewiesen —
so wie bisher bei 200 Dateien ohnehin alle nicht_gefunden-Fragen (die alte RRF-Schwelle 0,02 wies dort 0 % ab).
`nicht_gefunden_treffer_quote` für dense ist jetzt 0.75 (3/4). Die Schwelle gilt für qwen3-embedding:0.6b; ein
anderes Embedding hat andere Kosinus-Bereiche und braucht dieselbe Ableitung neu (Feld `top_score` im Eval).

**Regressionstest bestanden.** `retrieval_eval --stufe 200 --embedding qwen3-embedding:0.6b`, zweiter Lauf nach
der Umstellung: dense **79 / 93 / 93, MRR 0.863**, Embed 22,9 s — identisch zur Messung heute Morgen bis auf die
vierte Nachkommastelle der Top-Kosinus. Rohdaten `beweise/retrieval/2026-09-21/laeufe.jsonl` (53 Zeilen).

**Index-Hinweis.** `index.py` speichert Vektoren ohne Modellnamen (`embeddings(fundstelle_id, vektor)`). bge-m3
und qwen3-embedding:0.6b haben **beide 1024 Dimensionen** — ein Bestand, der mit bge-m3 embedded wurde, wirft mit
dem neuen Fragevektor keinen Fehler, sondern liefert still falsche Kosinus. Bestehende Ablagen müssen neu eingelesen
werden. Keine Migration gebaut; Hinweis steht in `modelle.yaml`.

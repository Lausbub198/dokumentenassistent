# Reranking — gibt es nicht, und warum das (noch) richtig ist

> **Historisch, Stand 23.09.2026.** Der Befund bleibt als Weg-Dokumentation stehen; die
> Konfiguration und die Leitzahlen wurden danach gemessen ersetzt — aktueller Stand: `~/Projects/lokalki-lab/docs/messungen/2026-10-07-gesamtprotokoll-dokumentenassistent.md`.


Stand 20.09.2026. Sachverhalt für das Skript (Block 5, Raum Bibliothek) und als Architekturentscheidung. Zahlen aus `beweise/last/2026-09-19/` (Stufe 200, `qwen3.5:9b` + `bge-m3`).

## Was das Werkzeug tut

Die Suche hat zwei Stufen, keine dritte:

1. **Zwei Ranglisten.** BM25 auf den Wortlaut (eigene Implementierung, Lucene-IDF) und Kosinus-Ähnlichkeit auf die Embeddings (`bge-m3`). Beide bewerten jeden Absatz *unabhängig von der Frage* — BM25 zählt Wörter, das Embedding misst Nähe zweier getrennt berechneter Vektoren.
2. **Verschmelzen.** Reciprocal Rank Fusion, k = 60. Jeder Absatz bekommt Punkte für seinen Platz in jeder Liste. Die besten acht gehen an das Modell. Kein Signal in beiden Listen → „nicht gefunden", ohne Modellaufruf.

Das ist ein Rang-Mix, kein Reranking.

## Was ein Reranker anders macht

Ein Cross-Encoder (z. B. `bge-reranker-v2-m3`) liest **Frage und Absatz zusammen** und bewertet, wie gut der Absatz die Frage beantwortet. Das ist genauer als Nähe messen, aber teuer: ein Modelldurchlauf je Kandidat. Bei 50 Kandidaten 50 Durchläufe, auf dem Laptop ein bis zwei Sekunden je Frage extra, plus eine zweite Laufzeit (ONNX), weil Ollama keine Reranker anbietet.

## Wann man ihn braucht — und der eine gemessene Fall

- **Viele ähnliche Treffer.** Der Korpus hat 21 Rechnungen von Farben Meister. Die Frage „Wie hoch war die Farben-Meister-Rechnung vom 14. August?" scheiterte bei 200 Dateien: `nicht_gefunden`, Soll `Rechnung (20).pdf`, 1.604,83 EUR. Alle 21 Rechnungen liegen im Wortlaut und in der Bedeutung dicht beieinander; das Datum trägt als Suchbegriff nicht („14. August" gegen „14.08.2025" im Dokument), und die Feinsortierung unter den Top 30 entscheidet, ob die richtige unter den Top 8 landet. Genau dafür ist ein Reranker gebaut. Das ist die einzige der 20 Fragen bei 200 Dateien, die an der Suche gescheitert ist (die anderen fünf roten: Dokumentart „unklar", nie freigegeben, oder Summenfrage, die das Werkzeug ehrlich nicht kann).
- **Große Bestände.** Ab einigen tausend Absätzen wird die Grobsuche unscharf; der richtige Absatz liegt dann oft auf Rang 12 statt unter den ersten 8. Bei 694 Absätzen zeigte sich das nicht: Suche 5–7 s, 14 von 20 Fragen richtig, davon alle drei Fangfragen sauber verweigert.
- **Umformulierte Fragen**, bei denen weder Wortlaut noch Embedding sicher greifen.

## Wann nicht

Kleine Bestände mit kleinem Modell dahinter. Bei 25 Dateien: 12 von 12 Fragen richtig, Embedding-Wahl egal (`bge-m3` und `nomic-embed-text` identische Treffer). Ein Reranker wäre Aufwand ohne messbaren Ertrag und würde die Antwortzeit verdoppeln.

## Entscheidung

Kein Reranker in V1. Bewusst, nicht vergessen. Die ehrliche Antwort auf die gescheiterte Datumsfrage wäre ein Reranker als **optionale dritte Stufe, abschaltbar**, mit `bge-reranker-v2-m3` lokal per ONNX. Das ist eine Erweiterung nach dem Video, mit einem Vorher-Nachher auf den 20 Fragen bei 200 Dateien — das Messgeschirr dafür existiert (`lasttest.py`, `retrieval_eval.py`).

## Für das Skript

Ein Satz im Raum Bibliothek, nach „Zwei Suchwege":

> „Zwei Suchwege, verschmolzen. Bei 200 Dateien reicht das. Bei tausenden käme eine dritte Stufe dazu, die jeden Treffer noch einmal gegen die Frage liest."

Optional, wenn Zeit ist, der ehrliche Beleg dazu:

> „Eine von zwanzig Fragen hat die Suche bei 200 Dateien nicht geschafft: die Farben-Meister-Rechnung vom 14. August, eine von einundzwanzig. Dafür wäre die dritte Stufe da. Die baue ich, wenn sie gebraucht wird — nicht vorher."

Nicht sagen: „Reranking ist Standard" oder „ohne Reranker findet es nichts". Gemessen ist: ohne Reranker 14 von 20 bei 200 Dateien, ein Suchfehler.

## Nachtrag 21.09., 00:02 — Retrieval-Eval bei 200 Dateien (694 Fundstellen, `beweise/retrieval/2026-09-21/`)

Die gescheiterte Datumsfrage („Farben-Meister-Rechnung vom 14. August") liegt bei Dense allein (bge-m3) auf **Rang 7**, im Hybrid auf **Rang 9**. Sie fiel also nicht an der Suche, sondern an der Fusion: BM25-Rauschen schiebt sie knapp aus den Top 8. Ein Reranker ist dafuer nicht die ehrliche Antwort — eine gewichtete Fusion (Dense staerker als BM25) oder ein Rang-Schnitt bei Dense ist es. Messbar in Minuten mit `retrieval_eval.py`, vor jeder Aenderung. Der Reranker bleibt die dritte Stufe fuer tausende Absaetze, nicht fuer diesen Fall.

Zahlen (Recall@1 / @8): BM25 21 / 43 · Dense bge-m3 71 / 93 · Dense qwen3-embedding:0.6b 79 / 93 · Dense nomic 29 / 79 · Hybrid bge-m3 57 / 93. Folgerung: das Embedding traegt die Hauptlast, BM25 rettet exakte Begriffe; der Hybrid kostet bei Rang 1, bringt bei Rang 8 nichts. Die Aussage „Embedding egal" gilt nur bei 25 Dateien; bei 200 ist nomic klar schwaecher (alter Befund bestaetigt).

---

## Nachtrag 2 (23.09.2026): Der Reranker ist drin. Die Einschätzung oben war falsch — und warum

Dieses Dokument empfahl am 20.09. **keinen Reranker in V1**, mit zwei Begründungen: bei 200 Dateien reiche
die Fusion, und der einzige gescheiterte Fall (Farben-Meister-Rechnung vom 14. August) sei ein Fusions-, kein
Rerankerproblem. Beides ist durch Messung überholt. Der alte Text bleibt stehen, weil er zeigt, worauf die
Fehleinschätzung beruhte: auf einer einzigen Frage.

**Was gemessen wurde** (`beweise/retrieval/2026-09-22/`, `2026-09-23/`, `docs/retrieval-befund-2026-09-21.md`):

| Korpus | ohne Reranker (Recall@1 / @8) | mit `bge-reranker-v2-m3`, k=20 |
|---|---|---|
| malerbetrieb, 200 Dateien, 694 Absätze, 14 Fragen | dense@qwen3-embedding 79 / 93 | **93 / 100** |
| GermanQuAD, 474 Absätze, 200 fremde Fragen | dense@bge-m3 88 / 97 | **98 / 100** |

**Warum das die Entscheidung dreht:**

1. **Es wirkt auf beiden Korpora.** Jede andere geprüfte Maßnahme (RRF-Gewichtung, Komposita-Zerlegung,
   Präfix-BM25, Embedding-Wechsel) half auf einem Korpus und schadete oder verpuffte auf dem anderen. Der
   Reranker ist die einzige, die überall gewinnt.
2. **Er macht die Embedding-Wahl zweitrangig.** Ohne Reranker kippt die Rangfolge der Embeddings je Bestand
   (malerbetrieb qwen 79 > bge 71; GermanQuAD bge 91 > qwen 82). Mit Reranker liegen beide bei 97–98.
3. **Die Kosten sind niedriger als angenommen.** Der alte Text rechnete mit „ein bis zwei Sekunden je Frage,
   plus ONNX-Laufzeit". Gemessen: **0,5 s** auf MPS bei kurzen Geschäftsabsätzen, über `sentence-transformers`
   als optionales Extra (`uv sync --extra reranker`). Auf CPU und bei langen Wikipedia-Absätzen 3–10 s — dann
   `rerank_geraet: cpu` und mit Ladezeit rechnen.
4. **k = 20 ist die Obergrenze, nicht 8.** Recall@20 ist bei beiden Embeddings 100 %, Recall@8 nur 93 %. Was
   der Reranker nicht sieht, kann er nicht nach vorne holen.

**Folge im Werkzeug** (Commit `93ebc5d`): `reranker`, `rerank_k`, `rerank_geraet`, `top_n` stehen in
`modelle.yaml`; `top_n` sank von 8 auf 5, weil zwischen fünf und acht Absätzen kein Treffer liegt. Fehlt das
Extra, bricht der Start mit Hinweis ab — kein stiller Verzicht.

**Was der Reranker NICHT kann** (`docs/abweisung-befund-2026-09-23.md`): erkennen, dass eine Frage im Bestand
gar nicht beantwortbar ist. 14 beantwortbare gegen 18 unbeantwortbare Fragen, neun Signale, bestes AUC 0,84 —
**kein einziges trennt**. Bei 95 % Spezifität gehen 9 von 14 echten Antworten verloren. Die Abweisung leisten
weiterhin das Modell und die Zitatprüfung, nicht ein Schwellwert.

**Für das Skript** ersetzt dieser Nachtrag den Satz „Zwei Suchwege, verschmolzen. Bei 200 Dateien reicht das."
Neu: „Eine Suche, und dahinter einer, der Frage und Absatz zusammen liest. Das hat mehr gebracht als alles,
was ich vorher an der Suche gedreht habe — und es ist das Einzige, das auf fremden Texten genauso wirkt."

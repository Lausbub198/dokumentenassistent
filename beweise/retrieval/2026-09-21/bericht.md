# Retrieval-Eval — beispiele/malerbetrieb/Quelle, Stufe 200

| Variante | Embedding | Fundstellen | Embed s | Recall@1 | Recall@5 | Recall@8 | MRR | Nicht-gefunden-Quote % | Dauer/Frage s |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | – | 694 | – | 21 | 36 | 43 | 0.321 | 0 | 0.005 |
| bm25_komposita | – | 694 | – | 29 | 50 | 57 | 0.405 | 0 | 0.005 |
| bm25_praefix | – | 694 | – | 21 | 50 | 57 | 0.364 | 0 | 0.009 |
| dense | bge-m3 | 694 | 10.3 | 71 | 86 | 93 | 0.779 | 0 | 0.058 |
| dense | nomic-embed-text | 694 | 4.9 | 29 | 64 | 79 | 0.442 | 0 | 0.036 |
| dense | qwen3-embedding:0.6b | 694 | 22.9 | 79 | 93 | 93 | 0.863 | 75 | 0.055 |
| hybrid | bge-m3 | 694 | 10.3 | 57 | 93 | 93 | 0.689 | 0 | 0.058 |
| hybrid | nomic-embed-text | 694 | 4.9 | 36 | 79 | 93 | 0.56 | 0 | 0.036 |
| hybrid | qwen3-embedding:0.6b | 694 | 22.9 | 50 | 86 | 93 | 0.657 | 100 | 0.055 |
| hybrid_komposita_w0.5 | bge-m3 | 694 | 10.3 | 64 | 93 | 100 | 0.748 | 50 | 0.058 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 694 | 22.9 | 64 | 93 | 93 | 0.744 | 100 | 0.055 |
| hybrid_komposita_w1.0 | bge-m3 | 694 | 10.3 | 64 | 93 | 93 | 0.731 | 0 | 0.058 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 694 | 22.9 | 64 | 93 | 93 | 0.755 | 100 | 0.055 |
| hybrid_w0.25 | bge-m3 | 694 | 10.3 | 57 | 93 | 100 | 0.711 | 100 | 0.058 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 694 | 22.9 | 57 | 93 | 93 | 0.72 | 100 | 0.055 |
| hybrid_w0.5 | bge-m3 | 694 | 10.3 | 57 | 93 | 100 | 0.713 | 50 | 0.058 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 694 | 22.9 | 50 | 93 | 93 | 0.655 | 100 | 0.055 |

## Wo es bricht

| Frage | bm25@- | bm25_komposita@- | bm25_praefix@- | dense@bge-m3 | dense@nomic-embed-text | dense@qwen3-embedding:0.6b | hybrid@bge-m3 | hybrid@nomic-embed-text | hybrid@qwen3-embedding:0.6b | hybrid_komposita_w0.5@bge-m3 | hybrid_komposita_w0.5@qwen3-embedding:0.6b | hybrid_komposita_w1.0@bge-m3 | hybrid_komposita_w1.0@qwen3-embedding:0.6b | hybrid_w0.25@bge-m3 | hybrid_w0.25@qwen3-embedding:0.6b | hybrid_w0.5@bge-m3 | hybrid_w0.5@qwen3-embedding:0.6b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wie hoch war die Telefonrechnung für März 2025? | 45 | 45 | 45 | 1 | 10 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welchen Betrag hat die Rechnung an die Kita Sonnenschein? | 52 | 52 | 53 | 1 | 9 | 1 | 1 | 6 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Was hat das Rollgerüst für die Bahnhofstraße 3 gekostet? | 8 | 8 | 8 | 10 | 7 | 1 | 3 | 2 | 2 | 3 | 3 | 3 | 2 | 5 | 2 | 3 | 3 |
| Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung von Farben Meister? | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung von Vogel? | 10 | 2 | 2 | 1 | 4 | 1 | 1 | 4 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 |
| Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer im Grundpreis enthalten? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Mit welcher Frist kann der Rahmenvertrag Gerüstbau gekündigt werden? | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wann ist der Betriebsurlaub 2025? | 2 | 3 | 4 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 |
| Wie oft wird Tiefengrund bei stark saugendem Untergrund aufgetragen? | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Wie hoch war die Farben-Meister-Rechnung vom 14. August? | 21 | 21 | 19 | 7 | 18 | 13 | 9 | 20 | 13 | 7 | 12 | 9 | 13 | 6 | 12 | 7 | 12 |
| Welchen Betrag hat die Rechnung an die Kita Regenbogen für den Turnraum? | 34 | 34 | 28 | 1 | 5 | 1 | 5 | 6 | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | 4 |
| Wie hoch war die Telefonrechnung für Oktober 2025? | 39 | 39 | 39 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Welche Rechnungsnummer mahnt Farben Meister in der Zahlungserinnerung an? | 21 | 1 | 2 | 1 | 1 | 1 | 4 | 2 | 8 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 4 |
| Welcher Restbetrag ist auf der Schlussrechnung an die WEG Ahornstraße 3-5 noch zu zahlen? | 14 | 14 | 14 | 3 | 6 | 2 | 4 | 5 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 |

# Retrieval-Eval — beweise/germanquad, Stufe 474

| Variante | Embedding | Fundstellen | Embed s | Recall@1 | Recall@5 | Recall@8 | MRR | Nicht-gefunden-Quote % | Dauer/Frage s |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | – | 474 | – | 80 | 92 | 95 | 0.856 | – | 0.027 |
| bm25_komposita | – | 474 | – | 82 | 93 | 97 | 0.875 | – | 0.027 |
| bm25_praefix | – | 474 | – | 88 | 98 | 98 | 0.928 | – | 0.051 |
| dense | bge-m3 | 474 | 34.4 | 88 | 95 | 97 | 0.922 | – | 0.055 |
| dense | qwen3-embedding:0.6b | 474 | 66.4 | 82 | 93 | 98 | 0.866 | – | 0.048 |
| dense | snowflake-arctic-embed2 | 694 | 14.3 | 21 | 64 | 71 | 0.376 | 100 | 0.066 |
| dense_rerank_bge-reranker-v2-m3_k20 | bge-m3 | 474 | – | 98 | 100 | 100 | 0.989 | – | 10.284 |
| dense_rerank_bge-reranker-v2-m3_k20 | qwen3-embedding:0.6b | 474 | – | 97 | 98 | 98 | 0.973 | – | 9.607 |
| dense_rerank_bge-reranker-v2-m3_k8 | bge-m3 | 474 | – | 95 | 97 | 97 | 0.959 | – | 3.215 |
| dense_rerank_bge-reranker-v2-m3_k8 | qwen3-embedding:0.6b | 474 | – | 97 | 98 | 98 | 0.973 | – | 3.114 |
| dense_rerank_qwen3-reranker-0.6b_k20 | bge-m3 | 694 | – | 86 | 100 | 100 | 0.929 | 75 | 2.053 |
| dense_rerank_qwen3-reranker-0.6b_k20 | qwen3-embedding:0.6b | 694 | – | 86 | 100 | 100 | 0.917 | 25 | 1.890 |
| dense_rerank_qwen3-reranker-0.6b_k8 | bge-m3 | 694 | – | 86 | 93 | 93 | 0.9 | 75 | 0.724 |
| dense_rerank_qwen3-reranker-0.6b_k8 | qwen3-embedding:0.6b | 694 | – | 86 | 93 | 93 | 0.898 | 25 | 0.693 |
| hybrid | bge-m3 | 474 | 34.4 | 87 | 98 | 98 | 0.912 | – | 0.055 |
| hybrid | qwen3-embedding:0.6b | 474 | 66.4 | 82 | 98 | 98 | 0.884 | – | 0.048 |
| hybrid | snowflake-arctic-embed2 | 694 | 14.3 | 21 | 71 | 79 | 0.398 | 100 | 0.066 |
| hybrid_komposita_w0.5 | bge-m3 | 474 | 34.4 | 93 | 98 | 98 | 0.956 | – | 0.055 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 474 | 66.4 | 85 | 97 | 97 | 0.899 | – | 0.048 |
| hybrid_komposita_w0.5 | snowflake-arctic-embed2 | 694 | 14.3 | 29 | 79 | 79 | 0.463 | 100 | 0.066 |
| hybrid_komposita_w1.0 | bge-m3 | 474 | 34.4 | 87 | 98 | 98 | 0.919 | – | 0.055 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 474 | 66.4 | 83 | 98 | 98 | 0.902 | – | 0.048 |
| hybrid_komposita_w1.0 | snowflake-arctic-embed2 | 694 | 14.3 | 36 | 79 | 79 | 0.497 | 100 | 0.066 |
| hybrid_w0.25 | bge-m3 | 474 | 34.4 | 90 | 100 | 100 | 0.933 | – | 0.055 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 474 | 66.4 | 85 | 97 | 98 | 0.894 | – | 0.048 |
| hybrid_w0.25 | snowflake-arctic-embed2 | 694 | 14.3 | 21 | 79 | 79 | 0.381 | 100 | 0.066 |
| hybrid_w0.5 | bge-m3 | 474 | 34.4 | 92 | 98 | 98 | 0.946 | – | 0.055 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 474 | 66.4 | 83 | 97 | 97 | 0.888 | – | 0.048 |
| hybrid_w0.5 | snowflake-arctic-embed2 | 694 | 14.3 | 21 | 71 | 79 | 0.402 | 100 | 0.066 |

## Absatzgenau

Treffer = genau der Zielabsatz (`absatz_id`), nicht nur die richtige Datei.

| Variante | Embedding | Recall@1 | Recall@5 | Recall@8 | MRR |
|---|---|---|---|---|---|
| bm25 | – | 80 | 92 | 95 | 0.856 |
| bm25_komposita | – | 82 | 93 | 97 | 0.875 |
| bm25_praefix | – | 88 | 98 | 98 | 0.928 |
| dense | bge-m3 | 88 | 95 | 97 | 0.922 |
| dense | qwen3-embedding:0.6b | 82 | 93 | 98 | 0.866 |
| dense_rerank_bge-reranker-v2-m3_k20 | bge-m3 | 98 | 100 | 100 | 0.989 |
| dense_rerank_bge-reranker-v2-m3_k20 | qwen3-embedding:0.6b | 97 | 98 | 98 | 0.973 |
| dense_rerank_bge-reranker-v2-m3_k8 | bge-m3 | 95 | 97 | 97 | 0.959 |
| dense_rerank_bge-reranker-v2-m3_k8 | qwen3-embedding:0.6b | 97 | 98 | 98 | 0.973 |
| hybrid | bge-m3 | 87 | 98 | 98 | 0.912 |
| hybrid | qwen3-embedding:0.6b | 82 | 98 | 98 | 0.884 |
| hybrid_komposita_w0.5 | bge-m3 | 93 | 98 | 98 | 0.956 |
| hybrid_komposita_w0.5 | qwen3-embedding:0.6b | 85 | 97 | 97 | 0.899 |
| hybrid_komposita_w1.0 | bge-m3 | 87 | 98 | 98 | 0.919 |
| hybrid_komposita_w1.0 | qwen3-embedding:0.6b | 83 | 98 | 98 | 0.902 |
| hybrid_w0.25 | bge-m3 | 90 | 100 | 100 | 0.933 |
| hybrid_w0.25 | qwen3-embedding:0.6b | 85 | 97 | 98 | 0.894 |
| hybrid_w0.5 | bge-m3 | 92 | 98 | 98 | 0.946 |
| hybrid_w0.5 | qwen3-embedding:0.6b | 83 | 97 | 97 | 0.888 |

## Wo es bricht

| Frage | bm25@- | bm25_komposita@- | bm25_praefix@- | dense@bge-m3 | dense@qwen3-embedding:0.6b | dense@snowflake-arctic-embed2 | dense_rerank_bge-reranker-v2-m3_k20@bge-m3 | dense_rerank_bge-reranker-v2-m3_k20@qwen3-embedding:0.6b | dense_rerank_bge-reranker-v2-m3_k8@bge-m3 | dense_rerank_bge-reranker-v2-m3_k8@qwen3-embedding:0.6b | dense_rerank_qwen3-reranker-0.6b_k20@bge-m3 | dense_rerank_qwen3-reranker-0.6b_k20@qwen3-embedding:0.6b | dense_rerank_qwen3-reranker-0.6b_k8@bge-m3 | dense_rerank_qwen3-reranker-0.6b_k8@qwen3-embedding:0.6b | hybrid@bge-m3 | hybrid@qwen3-embedding:0.6b | hybrid@snowflake-arctic-embed2 | hybrid_komposita_w0.5@bge-m3 | hybrid_komposita_w0.5@qwen3-embedding:0.6b | hybrid_komposita_w0.5@snowflake-arctic-embed2 | hybrid_komposita_w1.0@bge-m3 | hybrid_komposita_w1.0@qwen3-embedding:0.6b | hybrid_komposita_w1.0@snowflake-arctic-embed2 | hybrid_w0.25@bge-m3 | hybrid_w0.25@qwen3-embedding:0.6b | hybrid_w0.25@snowflake-arctic-embed2 | hybrid_w0.5@bge-m3 | hybrid_w0.5@qwen3-embedding:0.6b | hybrid_w0.5@snowflake-arctic-embed2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wo spielte der FC Barcelona bei dessen Gründung? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie ist das Zehrgebiet des Gletschers definiert? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wann wurde der Hatt-i Hümayun erlassen? | 2 | 2 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie viele Steuerzeichen gibt es im ASCII-Code? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Woran grenzt Zhejiang im Norden? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wann kommen die meisten Touristen nach Bern? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was war die kälteste gemessene Temperatur in Oklahoma City? | 1 | 1 | 1 | 2 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 2 | 1 | – | 1 | 1 | – | 2 | 1 | – | 2 | 1 | – |
| Was war ein Spitzname für Herzog Ernst II. von Sachsen-Coburg? | 1 | 1 | 1 | 1 | 3 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Ab wann gab es die erste Zugstrecke in Thüringen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Warum unterstütze al-Gaddafi die IRA? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was sind Verbrechen gegen die Menschlichkeit? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was behandelt eine bekannte Veröffentlichung von Carnot von 1824? | 1 | 1 | 1 | 2 | 3 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 2 | – | 1 | 1 | – | 1 | 2 | – | 1 | 2 | – |
| Wie war der bürgerliche Name von Thayendanegea? | 1 | 1 | 1 | 9 | 3 | – | 1 | 1 | 9 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 2 | 1 | – | 1 | 1 | – |
| Wann ist in Mexiko City Regenzeit? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wo spielt "Wer die Nachtigall stört"? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Städte außerhalb Kanada sind von dem St. John's International Airport erreichbar? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie viel Prozent der Stimmen hat der Vorgänger von Miguel Angel Mancera bei den Wahlen bekommen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wer war der Vorgänger von Marcelo Ebrard? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was ist der Unterschied zwischen einer Amygdala eines Mannes und einer Frau? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie wird die Zugfestigkeit von Papier gemessen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Als was bezeichnen die Demokraten bei Wahlen die im Ausland lebenden Wähler? | 1 | 1 | 2 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was sind die Folgen von zu viel Zink? | 3 | 3 | 3 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 2 | 2 | – | 1 | 1 | – | 2 | 2 | – | 1 | 1 | – | 1 | 1 | – |
| Was ist die Fundstelle Neumark-Nord? | 1 | 1 | 1 | 1 | 57 | – | 1 | 57 | 1 | 57 | – | – | – | – | 1 | 4 | – | 1 | 11 | – | 1 | 2 | – | 1 | 30 | – | 1 | 10 | – |
| Was ist Spin von teilchen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was war laut MIcheal Carley der ideologische Antrieb der Politik von England und Frankreich vor dem 2. Weltkrieg? | 8 | 6 | 3 | 10 | 8 | – | 1 | 1 | 10 | 1 | – | – | – | – | 5 | 3 | – | 4 | 3 | – | 3 | 2 | – | 5 | 5 | – | 3 | 3 | – |
| Welches Studio kaufte DreamWorks? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Seit wann werden US-Dollarnoten mit Sicherheitsaufdrucken versehen? | 16 | 2 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 4 | 3 | – | 1 | 1 | – | 2 | 2 | – | 3 | 3 | – | 3 | 3 | – |
| Welchen Zweig der Physik etablierte Planck mit der Entdeckung des Wirkungsquantums? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wann starb Alexander der Große? | 4 | 4 | 2 | 8 | 6 | – | 1 | 1 | 1 | 1 | – | – | – | – | 2 | 3 | – | 2 | 3 | – | 2 | 3 | – | 4 | 3 | – | 2 | 3 | – |
| Nach welchem Konzil entstand die koptische Kirche? | 1 | 1 | 1 | 1 | 6 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 2 | – | 1 | 1 | – | 1 | 2 | – | 1 | 2 | – |
| Wofür wurde Queen Elisabeth II. 1987 in Kanada kritisiert? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Zu welcher Unterteilung der Immunreaktion führten u.a. die Ergebnisse von Jacques Miller? | 2 | 2 | 2 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Stoffe werden bei der Herstellung von Bier zugesetzt? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was wird bei der Herstellung von Wein und Bier gegärt? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wer ist derzeit der CIA-Chef? | 1 | 1 | 1 | 1 | 3 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 3 | – | 1 | 1 | – | 1 | 3 | – | 1 | 3 | – |
| Wie sehen die Böden der atlantischen Küstenebene von North Carolina? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| In welchem Teil von North Carolina werden heutzutage verschiedene Baumaterialen abgebaut? | 2 | 2 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 2 | – | 1 | 1 | – | 1 | 2 | – | 1 | 1 | – | 1 | 1 | – |
| Was beinhaltet das Hauptwerk von Edmund Burke? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Warum kam es zu so vielen Toten nach dem Erdbeben 1985 in Mexiko-Stadt? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie sieht die Landschaft der Mexiko-Stadt aus? | 6 | 6 | 1 | 1 | 3 | – | 1 | 1 | 1 | 1 | – | – | – | – | 2 | 4 | – | 1 | 4 | – | 2 | 4 | – | 1 | 4 | – | 1 | 4 | – |
| Wie lang ist die Straßenbahnstrecke in Mexiko-Stadt heutzutage? | 3 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 2 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Sportveranstaltung findet häufig in Miami statt? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wo spielen die Detroit Red Wings heutzutage? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Bakterien sterben von Sauerstoff? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wo liegt der Der Élysée-Palast? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Was ist das Monumento a los Niños Héroes? | 1 | 1 | 1 | 2 | 2 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie hoch lieg der Ort Säntis? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wer wurde 1968 Präsident des FC Barcelona? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wie viele der Kinder Nigerias im Schulalter gehen zur Schule? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wo hat die US Army Rekrutierungsstellen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Einstellung hatte Hans Blüher gegenüber der humanistischen Bildung? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wann waren die ersten Spiele der Zweitmannschaft vom FC Everton? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Wo steht der Schiedsrichter beim Canadian Football vor dem Snap? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Warum brauchten die Amerikaner eine eigene See Armee? | 121 | 121 | 149 | 2 | 3 | – | 3 | 3 | 3 | 3 | – | – | – | – | 20 | 20 | – | 11 | 11 | – | 20 | 20 | – | 5 | 7 | – | 11 | 11 | – |
| Wie viel kosteten die Tribut- und Lösegeldzahlungen die USA 1800? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| An welchem Ort von North Carolina haben sich die Hugenotten und Deutschschweizer niedergelassen? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Warum hatten andere Menschen Angst vor von Neumann? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Durch welches Zusammentreffen wurde die Luxemburgkrise  beendet? | 1 | 1 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – | 1 | 1 | – |
| Welche Platzierung erreichte Beyonces Album "4" in den Billboard 200? | 2 | 2 | 2 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 2 | 2 | – | 1 | 1 | – | 2 | 2 | – | 1 | 1 | – | 1 | 1 | – |
| Seit wann leben in Indien menschliche Kulturen? | 12 | 12 | 1 | 1 | 1 | – | 1 | 1 | 1 | 1 | – | – | – | – | 4 | 2 | – | 1 | 2 | – | 4 | 2 | – | 1 | 1 | – | 1 | 2 | – |
| Wie hoch war die Telefonrechnung für März 2025? | – | – | – | – | – | 137 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 67 | – | – | 61 | – | – | 67 | – | – | 79 | – | – | 61 |
| Welchen Betrag hat die Rechnung an die Kita Sonnenschein? | – | – | – | – | – | 4 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 4 | – | – | 4 | – | – | 4 | – | – | 4 | – | – | 4 |
| Was hat das Rollgerüst für die Bahnhofstraße 3 gekostet? | – | – | – | – | – | 10 | – | – | – | – | 2 | 3 | 10 | 2 | – | – | 5 | – | – | 4 | – | – | 5 | – | – | 4 | – | – | 4 |
| Was kostet die Fassadenfarbe für die Ringstraße 8 laut korrigierter Rechnung von Farben Meister? | – | – | – | – | – | 3 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 2 | – | – | 2 | – | – | 2 | – | – | 3 | – | – | 2 |
| Welcher Betrag gilt für das Gerüst Ringstraße 8 nach der Korrekturrechnung von Vogel? | – | – | – | – | – | 3 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 2 | – | – | 1 | – | – | 1 | – | – | 3 | – | – | 2 |
| Wie viele Wochen Standzeit sind im Rahmenvertrag mit dem Gerüstbauer im Grundpreis enthalten? | – | – | – | – | – | 1 | – | – | – | – | 2 | 2 | 2 | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 |
| Mit welcher Frist kann der Rahmenvertrag Gerüstbau gekündigt werden? | – | – | – | – | – | 1 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 |
| Wann ist der Betriebsurlaub 2025? | – | – | – | – | – | 3 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 2 | – | – | 2 | – | – | 2 | – | – | 2 | – | – | 2 |
| Wie oft wird Tiefengrund bei stark saugendem Untergrund aufgetragen? | – | – | – | – | – | 1 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 | – | – | 1 |
| Wie hoch war die Farben-Meister-Rechnung vom 14. August? | – | – | – | – | – | 40 | – | – | – | – | 1 | 1 | 1 | 13 | – | – | 20 | – | – | 22 | – | – | 20 | – | – | 28 | – | – | 22 |
| Welchen Betrag hat die Rechnung an die Kita Regenbogen für den Turnraum? | – | – | – | – | – | 4 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 5 | – | – | 5 | – | – | 5 | – | – | 5 | – | – | 5 |
| Wie hoch war die Telefonrechnung für Oktober 2025? | – | – | – | – | – | 81 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 26 | – | – | 47 | – | – | 26 | – | – | 59 | – | – | 47 |
| Welche Rechnungsnummer mahnt Farben Meister in der Zahlungserinnerung an? | – | – | – | – | – | 2 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 8 | – | – | 2 | – | – | 1 | – | – | 5 | – | – | 7 |
| Welcher Restbetrag ist auf der Schlussrechnung an die WEG Ahornstraße 3-5 noch zu zahlen? | – | – | – | – | – | 8 | – | – | – | – | 1 | 1 | 1 | 1 | – | – | 5 | – | – | 5 | – | – | 5 | – | – | 5 | – | – | 5 |

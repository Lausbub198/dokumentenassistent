# Abweisung — beispiele/malerbetrieb Stufe 200

14 beantwortbare gegen 18 unbeantwortbare Fragen. „trennt" = niedrigster Wert der beantwortbaren liegt über dem höchsten der unbeantwortbaren.

| Signal | AUC | beste Schwelle | Genauigkeit % | Sensitivität % | Spezifität % | Überlappung (min b / max u) | trennt | Schwelle bei 95 % Spez. | Verlust bei 95 % Spez. |
|---|---|---|---|---|---|---|---|---|---|
| rerank_bge-reranker-v2-m3_k20@qwen3-embedding:0.6b | 0.8433 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k8@bge-m3 | 0.8393 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k20@bge-m3 | 0.8353 | 0.9075 | 78 | 79 | 78 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| rerank_bge-reranker-v2-m3_k8@qwen3-embedding:0.6b | 0.8333 | 0.6099 | 75 | 93 | 61 | 0.0592 / 0.9947 | nein | 0.9954 | 9/14 (64 %) |
| dense@qwen3-embedding:0.6b | 0.7679 | 0.5476 | 72 | 79 | 67 | 0.5062 / 0.7402 | nein | 0.7445 | 13/14 (93 %) |
| dense@bge-m3 | 0.7579 | 0.6289 | 75 | 79 | 72 | 0.4965 / 0.7439 | nein | 0.7607 | 13/14 (93 %) |
| bm25 | 0.6806 | 14.4526 | 66 | 43 | 83 | 8.7382 / 20.5138 | nein | 22.3959 | 13/14 (93 %) |
| rrf@qwen3-embedding:0.6b | 0.6250 | 0.0325 | 66 | 50 | 78 | 0.0253 / 0.0328 | nein | 0.0328 | 9/14 (100 %) |
| rrf@bge-m3 | 0.6111 | 0.0253 | 59 | 100 | 28 | 0.0253 / 0.0328 | nein | 0.0328 | 10/14 (100 %) |

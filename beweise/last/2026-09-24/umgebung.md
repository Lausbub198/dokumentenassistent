# Umgebung des Belastungstests

- Zeit (lokal): 2026-09-24T00:20:42
- ollama --version: ollama version is 0.34.0
- macOS: 26.6.2
- Rechner: Mac16,7, RAM 24 GB
- Netzteil angeschlossen: ja
- pmset -g batt:

```
Now drawing from 'AC Power'
 -InternalBattery-0 (id=24379491)	99%; finishing charge; 0:11 remaining present: true
```

## Ollama-Umgebung

- OLLAMA_KV_CACHE_TYPE: nicht gesetzt (Ollama-Standard)
- OLLAMA_FLASH_ATTENTION: nicht gesetzt (Ollama-Standard)
- OLLAMA_NUM_PARALLEL: nicht gesetzt (Ollama-Standard)
- OLLAMA_MODELS: /Volumes/exSSD/ollama-models
- OLLAMA_CONTEXT_LENGTH: nicht gesetzt (Ollama-Standard)
- KV-Cache: f16 (Standard), solange OLLAMA_KV_CACHE_TYPE nicht gesetzt ist

# Umgebung des Belastungstests

- Zeit (lokal): 2026-09-20T00:08:52
- ollama --version: ollama version is 0.34.0
- macOS: 26.6.2
- Rechner: Mac16,7, RAM 24 GB
- Netzteil angeschlossen: ja
- pmset -g batt:

```
Now drawing from 'AC Power'
 -InternalBattery-0 (id=24379491)	51%; charging; 1:31 remaining present: true
```

## Ollama-Umgebung (nachtraeglich geprueft am 20.09., LaunchAgent local.ollama-env.plist und launchctl getenv)

- OLLAMA_KV_CACHE_TYPE: nicht gesetzt -> KV-Cache f16 (Standard). Die fruehere LaunchAgent-Falle (q8_0) liegt nicht mehr vor.
- OLLAMA_FLASH_ATTENTION / NUM_PARALLEL / CONTEXT_LENGTH: nicht gesetzt (Standard)
- OLLAMA_MODELS: /Volumes/exSSD/ollama-models (externe SSD; Ladezeiten haengen am Port, nicht am Modell)
- Gewichte: Bibliotheks-Standard-Tags (4-Bit), MLX-Tag siehe Nachtrag

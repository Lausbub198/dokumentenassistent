# Umgebung des e2e-Laufs

- Zeit (lokal): 2026-09-19T14:52:00
- ollama --version: ollama version is 0.34.0
- macOS: 26.6.2 (macOS-26.6.2-arm64-arm-64bit-Mach-O)
- Python: 3.13.12
- Host: http://localhost:11434
- modelle.yaml: embedding=bge-m3 llm=qwen3.5:9b think='low'
- think im Lauf tatsaechlich: False (Workaround, siehe Kopf von test_e2e.py)
- Modelle in /api/tags: bge-m3:latest, gemma3:4b, gemma4:e4b, granite4.1:3b, granite4.1:8b, hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M, hf.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M, hf.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF:Q5_K_M, hf.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF:Q8_0, lfm2.5:latest, nomic-embed-text:latest, qwen3-vl:8b, qwen3.5:9b, qwen3:1.7b, qwen3:4b
- Netzteil angeschlossen: unbekannt
- Powermode: unbekannt

Alle Zeiten in `zeiten.json`. Sollwerte: tests/golden.json.
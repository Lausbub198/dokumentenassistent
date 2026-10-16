#!/bin/bash
# Startet die Web-Oberflaeche und oeffnet sie im Browser.
# Doppelklick im Finder genuegt; im Terminal: ./start.command
# Ohne --quelle/--ziel: den Bestand waehlst du unter /start (mit "Zuletzt geoeffnet").
set -euo pipefail

cd "$(dirname "$0")"
PORT=8765

if ! curl -sf --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama antwortet nicht auf 127.0.0.1:11434."
  echo "Ohne Ollama bricht schon 'Profil vorschlagen' ab."
  echo
  echo "Ollama starten (Mac: open -a Ollama, Linux: ollama serve) und dann nochmal ausfuehren."
  exit 1
fi

if curl -sf --max-time 2 "http://127.0.0.1:$PORT/start" >/dev/null; then
  echo "Laeuft schon auf Port $PORT — oeffne nur das Fenster."
  open "http://127.0.0.1:$PORT/start"
  exit 0
fi

# Browser erst aufmachen, wenn der Server antwortet
( for _ in $(seq 1 40); do
    curl -sf --max-time 1 "http://127.0.0.1:$PORT/start" >/dev/null && { open "http://127.0.0.1:$PORT/start"; exit 0; }
    sleep 0.5
  done ) &

echo "Dokumentenassistent startet auf http://127.0.0.1:$PORT/start"
echo "Beenden mit Ctrl+C."
exec uv run dokumentenassistent --port "$PORT"

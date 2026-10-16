#!/bin/zsh
# Abendlauf 2026-09-29: erst AnythingLLM-Vergleich, danach gepaarter Antwortlauf A gegen B (Präfix).
# Beide teilen sich ein Ollama und laufen deshalb strikt nacheinander. Wiederaufnehmbar: nach einem
# Abbruch einfach erneut starten, fertige Fragen werden übersprungen.
#
#   ./scripts/abendlauf.sh              beide Phasen
#   ./scripts/abendlauf.sh anythingllm  nur AnythingLLM
#   ./scripts/abendlauf.sh e2e          nur Antwortlauf A gegen B
#
# Private Daten und Logs nur unter $DOKASS_LAEUFE (Standard ~/dokass-privat/laeufe). Der Mac bleibt per caffeinate wach.
set -u
cd "${0:A:h}/.."
PHASE="${1:-alle}"
LAUF=${DOKASS_LAEUFE:-$HOME/dokass-privat/laeufe}
PY=(env PYTHONPATH=src .venv/bin/python -m)
log() { print -r -- "[$(date +%H:%M:%S)] $*" | tee -a "$LAUF/abendlauf.log"; }

[[ -d $LAUF ]] || { print "Laufordner fehlt ($LAUF) – DOKASS_LAEUFE setzen oder den Ordner anlegen"; exit 1; }
caffeinate -i -w $$ &

if [[ -n "$(ollama ps | tail -n +2)" ]]; then
  log "Ollama ist belegt – bitte laufende Modelle/Messungen beenden:"; ollama ps | tee -a "$LAUF/abendlauf.log"; exit 1
fi

if [[ $PHASE == alle || $PHASE == anythingllm ]]; then
  gestartet=0
  if ! curl -sf http://127.0.0.1:3001/api/ping >/dev/null; then
    log "Starte AnythingLLM"; open -a AnythingLLM; gestartet=1
    for i in {1..90}; do curl -sf http://127.0.0.1:3001/api/ping >/dev/null && break; sleep 2; done
  fi
  log "AnythingLLM: konfigurieren → einlesen → messen → auswerten → zurücksetzen"
  if "${PY[@]}" dokumentenassistent.anythingllm_vergleich alles --zuruecksetzen >>"$LAUF/anythingllm.log" 2>&1; then
    log "AnythingLLM fertig: $LAUF/anythingllm/bericht.json"
  else
    log "AnythingLLM abgebrochen (siehe $LAUF/anythingllm.log) – Einstellungen ggf. mit 'zuruecksetzen' wiederherstellen"
  fi
  (( gestartet )) && osascript -e 'quit app "AnythingLLM"' >/dev/null 2>&1
  sleep 5
fi

if [[ $PHASE == alle || $PHASE == e2e ]]; then
  log "Antwortlauf A gegen B (Schwelle 0,47)"
  if "${PY[@]}" dokumentenassistent.praefix_e2e --arm B --schwelle 0.47 >>"$LAUF/praefix-e2e.log" 2>&1; then
    log "Antwortlauf fertig: $LAUF/praefix-e2e-2026-09-29/bericht.json"
  else
    log "Antwortlauf abgebrochen (siehe $LAUF/praefix-e2e.log)"
  fi
fi
log "Abendlauf beendet"

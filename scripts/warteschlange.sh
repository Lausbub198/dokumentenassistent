#!/bin/zsh
# Messwarteschlange (Testprogramm 2026-09-30, A4): arbeitet Aufträge nacheinander ab.
#
#   Aufträge:  $Q/offen/NN-name.sh   (zsh-Schnipsel, läuft im Dokumentenassistent-Repo)
#   Ablauf:    offen/ → laeuft/ → erledigt/ (Exit 0) bzw. fehlgeschlagen/
#   Start:     scripts/warteschlange.sh [--nur-nachts]
#
# Ein Auftrag startet nur, wenn Ollama kein Modell geladen hat und kein anderer Messprozess läuft,
# 3 Minuten am Stück. Mit --nur-nachts startet zwischen 07:00 und 18:00 kein neuer Auftrag
# (ein laufender wird zu Ende gebracht). Der Läufer endet, wenn offen/ leer ist.
set -u
cd "${0:A:h}/.."
Q=${WARTESCHLANGE:-${DOKASS_LAEUFE:-$HOME/dokass-privat/laeufe}/warteschlange}
RUHE=${WARTESCHLANGE_RUHE_MIN:-3}
NACHTS=0; [[ "${1:-}" == --nur-nachts ]] && NACHTS=1
mkdir -p $Q/{offen,laeuft,erledigt,fehlgeschlagen}
log() { print -r -- "[$(date '+%d.%m. %H:%M:%S')] $*" | tee -a $Q/warteschlange.log; }
caffeinate -i -w $$ &

frei() {
  [[ -z "$(ollama ps | tail -n +2)" ]] || return 1
  ! pgrep -f "anythingllm_vergleich|praefix_e2e|praefix_test|embedding_vergleich|antwortstufe|seitenvergleich|neu_einlesen|germanquad_pruefstein|nightrun|python -m lab|pytest" >/dev/null
}

log "Läufer gestartet (nur nachts: $NACHTS)"
while true; do
  # Glob-Array statt ls: leer bleibt leer. (ls ohne Treffer listete am 01.10. das Repo auf,
  # und der Läufer verschob Repo-Dateien als „Aufträge“.)
  auftraege=($Q/offen/*.sh(N))
  (( ${#auftraege} )) || { log "keine offenen Aufträge – Läufer beendet"; break; }
  auftrag=${auftraege[1]}
  [[ $auftrag == $Q/offen/*.sh && -f $auftrag ]] || { log "ABBRUCH: ungültiger Auftrag $auftrag"; exit 2; }
  h=$(date +%H)
  if (( NACHTS )) && (( 10#$h >= 7 && 10#$h < 18 )); then sleep 300; continue; fi
  ruhig=0
  while (( ruhig < RUHE )); do if frei; then (( ruhig++ )); else ruhig=0; fi; sleep 60; done
  name=${auftrag:t}
  mv -- $auftrag $Q/laeuft/$name
  log "START $name"
  if zsh $Q/laeuft/$name >>$Q/${name%.sh}.log 2>&1; then
    mv $Q/laeuft/$name $Q/erledigt/$name; log "OK    $name"
  else
    mv $Q/laeuft/$name $Q/fehlgeschlagen/$name; log "FEHLER $name (siehe ${name%.sh}.log)"
  fi
done

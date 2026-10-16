#!/bin/bash
# Veröffentlicht den Stand von HEAD ins öffentliche Repository, ohne die lokale Historie.
#
#   ./scripts/veroeffentlichen.sh "Nachricht"          zeigt nur, was sich ändern würde
#   ./scripts/veroeffentlichen.sh "Nachricht" --push   committet und pusht
#
# Warum so: Die lokale Historie trägt eine Firmen-Mailadresse und alte private Pfade. Sie darf nie
# hochgeladen werden (kein "git push", nie force). Öffentlich liegt eine eigene Historie unter der
# GitHub-noreply-Adresse; jede Veröffentlichung ist dort ein Commit mit dem Stand von HEAD.
#
# Der Klon (Standard ~/Projects/dokumentenassistent-public, überschreibbar mit DOKASS_PUBLIC_KLON)
# ist reiner Spiegel: nie von Hand bearbeiten, er wird bei jedem Lauf zurückgesetzt.
set -euo pipefail

NACHRICHT="${1:-}"
PUSH=0
[[ "${2:-}" == "--push" ]] && PUSH=1
KLON="${DOKASS_PUBLIC_KLON:-$HOME/Projects/dokumentenassistent-public}"
HIER="$(cd "$(dirname "$0")/.." && pwd)"

[[ ! -z "$NACHRICHT" ]] || { echo "Aufruf: $0 \"Nachricht\" [--push]"; exit 2; }
[[ -d "$KLON/.git" ]] || { echo "Klon fehlt: $KLON (git clone https://github.com/Lausbub198/dokumentenassistent.git)"; exit 1; }

cd "$HIER"
[[ -z "$(git status --porcelain)" ]] || { echo "Lokal sind Änderungen nicht committet. Erst committen, dann veröffentlichen."; exit 1; }

echo "== 1/5 Tests"
uv run pytest -q 2>&1 | tail -1

echo "== 2/5 Klon aktualisieren"
git -C "$KLON" reset -q --hard
git -C "$KLON" pull -q --ff-only origin main
EMAIL="$(git -C "$KLON" config user.email)"
[[ "$EMAIL" == *"@users.noreply.github.com" ]] || { echo "Klon-Identität ist nicht die noreply-Adresse ($EMAIL). Abbruch."; exit 1; }

echo "== 3/5 Stand von HEAD übernehmen"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git archive HEAD . ':(exclude)CLAUDE.md' | tar -x -C "$TMP"
rsync -a --delete --exclude .git "$TMP"/ "$KLON"/
git -C "$KLON" add -A
if git -C "$KLON" diff --cached --quiet; then
  echo "Nichts zu veröffentlichen, der öffentliche Stand ist aktuell."
  exit 0
fi

echo "== 4/5 Prüfung auf private Spuren"
TREFFER="$(git -C "$KLON" grep --cached -I -l -i -E 'cariad|Mietwohnungen|/Users/[a-z0-9]+/|SEPA_Mandat|Selbstauskunft|Zeichnungsschein|@gmail\.com' \
  -- . ':!tests/test_pfade_privat.py' ':!scripts/veroeffentlichen.sh' ':!*.arrow' || true)"
if [[ ! -z "$TREFFER" ]]; then
  echo "Private Spuren gefunden, nichts veröffentlicht:"; echo "$TREFFER"
  git -C "$KLON" reset -q --hard
  exit 1
fi
echo "keine"

echo "== 5/5 Änderung"
git -C "$KLON" diff --cached --stat | tail -8
if [[ $PUSH -eq 0 ]]; then
  echo
  echo "Nur Vorschau. Zum Veröffentlichen: $0 \"$NACHRICHT\" --push"
  git -C "$KLON" reset -q --hard
  exit 0
fi

git -C "$KLON" commit -q -m "$NACHRICHT"
git -C "$KLON" push -q origin main
echo "Veröffentlicht: $(git -C "$KLON" log --format='%h %an' -1)"
echo "https://github.com/Lausbub198/dokumentenassistent"

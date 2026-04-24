#!/bin/bash
# git-autosync.sh — Auto-commit y push de cambios pendientes
# Ejecutado por cron o tarea programada. Sale en silencio si no hay nada que subir.

set -euo pipefail

REPO_DIR="${CLAUDIA_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

cd "$REPO_DIR"

# Sin remote configurado, no hay nada que hacer
if ! git remote get-url origin &>/dev/null; then
  exit 0
fi

# Sin cambios pendientes (tracked ni untracked relevantes), salir
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
  exit 0
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

git add -A
git commit -m "backup: auto-sync $TIMESTAMP" --quiet
git push --quiet

echo "[$TIMESTAMP] auto-sync: cambios subidos"

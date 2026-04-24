#!/bin/bash
# Hook SessionStart: git pull antes de cargar contexto
set -euo pipefail

CLAUDIA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$CLAUDIA_ROOT"

# Solo si es un repo git con remote configurado
if ! git rev-parse --git-dir &>/dev/null; then
  exit 0
fi

if ! git remote get-url origin &>/dev/null; then
  exit 0
fi

# Stash de cambios locales si los hay
stashed=false
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  git stash push --quiet -m "auto-stash before pull" 2>/dev/null && stashed=true
fi

# Pull con rebase para evitar merge commits innecesarios
output=$(git pull --rebase --quiet 2>&1) || {
  echo "⚠ git pull falló — puede haber conflictos pendientes"
  echo "$output"
  # Restaurar stash si lo hicimos
  $stashed && git stash pop --quiet 2>/dev/null
  exit 0  # No bloquear la sesión
}

# Restaurar stash
$stashed && git stash pop --quiet 2>/dev/null

# Informar solo si hubo cambios
if [[ "$output" != *"Already up to date"* && "$output" != *"Current branch"* && -n "$output" ]]; then
  echo "↓ git pull: cambios recibidos del remote"
fi

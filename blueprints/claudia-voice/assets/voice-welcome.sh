#!/bin/bash
# Hook SessionStart: mensaje de bienvenida por voz
set -euo pipefail

CLAUDIA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEAK="$CLAUDIA_ROOT/.claude/skills/claudia-voice/speak.sh"
[[ ! -x "$SPEAK" ]] && exit 0

INPUT=$(cat)

# Leer nombre del usuario de identity.md si existe
IDENTITY="$CLAUDIA_ROOT/user/context/identity.md"
USER_NAME=""
if [[ -f "$IDENTITY" ]]; then
  USER_NAME=$(grep -m1 "^## Quién es " "$IDENTITY" | sed 's/^## Quién es //')
fi

if [[ -n "$USER_NAME" ]]; then
  "$SPEAK" "Hola $USER_NAME, estoy aquí." &
else
  "$SPEAK" "Hola, estoy aquí." &
fi
exit 0

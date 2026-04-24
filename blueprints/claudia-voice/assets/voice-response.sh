#!/bin/bash
# Hook Stop: extrae texto marcado con [voice]...[/voice] y lo reproduce
set -euo pipefail

CLAUDIA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEAK="$CLAUDIA_ROOT/.claude/skills/claudia-voice/speak.sh"
[[ ! -x "$SPEAK" ]] && exit 0

INPUT=$(cat)

# Extraer last_assistant_message
MESSAGE=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')
[[ -z "$MESSAGE" ]] && exit 0

# Extraer texto entre [voice] y [/voice]
# Puede haber múltiples bloques — los concatenamos
VOICE_TEXT=$(echo "$MESSAGE" | sed -n 's/.*\[voice\]\(.*\)\[\/voice\].*/\1/p' | tr '\n' ' ' | sed 's/^ *//;s/ *$//')
[[ -z "$VOICE_TEXT" ]] && exit 0

# Reproducir en background para no bloquear Claude
"$SPEAK" "$VOICE_TEXT" &
exit 0

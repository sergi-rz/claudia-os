#!/bin/bash
# Claudia OS — Watchdog para el bot de Telegram
#
# Añadir a cron (sustituye /ruta/a/claudia-os por la ruta absoluta de tu clon):
#   */5 * * * * /ruta/a/claudia-os/.claude/skills/telegram-bot/watchdog.sh

CLAUDIA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BOT_NAME="claudia-telegram"
BOT_DIR="$CLAUDIA_ROOT/.claude/skills/telegram-bot"
LOG_DIR="$BOT_DIR/user/logs"
LOG="$LOG_DIR/watchdog.log"
MAX_CLAUDE_MINUTES=10

mkdir -p "$LOG_DIR"

# ¿Está el bot corriendo?
if ! pm2 describe "$BOT_NAME" > /dev/null 2>&1; then
  echo "$(date -Iseconds): Bot no encontrado, arrancando..." >> "$LOG"
  cd "$BOT_DIR" && pm2 start ecosystem.config.cjs >> "$LOG" 2>&1
  exit 0
fi

STATUS=$(pm2 describe "$BOT_NAME" 2>/dev/null | grep "status" | head -1 | awk '{print $4}')

if [ "$STATUS" != "online" ]; then
  echo "$(date -Iseconds): Bot en estado '$STATUS', reiniciando..." >> "$LOG"
  pm2 restart "$BOT_NAME" --update-env >> "$LOG" 2>&1
  exit 0
fi

# Matar procesos claude colgados (más de MAX_CLAUDE_MINUTES)
ps aux | grep '[/]claude' | while read -r line; do
  PID=$(echo "$line" | awk '{print $2}')
  ELAPSED=$(ps -o etimes= -p "$PID" 2>/dev/null | tr -d ' ')
  if [ -n "$ELAPSED" ] && [ "$ELAPSED" -ge $((MAX_CLAUDE_MINUTES * 60)) ] 2>/dev/null; then
    echo "$(date -Iseconds): Matando claude colgado PID=$PID (${ELAPSED}s)" >> "$LOG"
    kill "$PID" 2>/dev/null
  fi
done

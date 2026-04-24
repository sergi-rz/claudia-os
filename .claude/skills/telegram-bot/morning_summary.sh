#!/bin/bash
# Claudia OS — Resumen matutino por Telegram
#
# Añadir a cron (sustituye /ruta/a/claudia-os por la ruta absoluta de tu clon):
#   0 8 * * * /ruta/a/claudia-os/.claude/skills/telegram-bot/morning_summary.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDIA_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CALENDAR_SCRIPT="$CLAUDIA_ROOT/.claude/skills/claudia-calendar/fetch_calendar.py"

# Leer .env de user/credentials/
CREDS_FILE="$CLAUDIA_ROOT/user/credentials/.env"
if [ -f "$CREDS_FILE" ]; then
  export $(grep -v '^#' "$CREDS_FILE" | xargs)
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_USER_ID" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no definidos" >&2
  exit 1
fi

# Obtener eventos de hoy
AGENDA=$(python3 "$CALENDAR_SCRIPT" --days 1 2>&1)

if [ -z "$AGENDA" ] || echo "$AGENDA" | grep -q "^Error"; then
  AGENDA="No he podido consultar el calendario."
fi

# Construir mensaje (hora local según user/config/settings.json)
SETTINGS_FILE="$CLAUDIA_ROOT/user/config/settings.json"
if [ -f "$SETTINGS_FILE" ] && command -v python3 >/dev/null 2>&1; then
  TZ_FROM_SETTINGS=$(python3 -c "import json,sys; print(json.load(open('$SETTINGS_FILE')).get('timezone',''))" 2>/dev/null)
  [ -n "$TZ_FROM_SETTINGS" ] && export TZ="$TZ_FROM_SETTINGS"
fi
TODAY=$(date +"%A %d/%m/%Y")
MESSAGE="Buenos días.

Hoy es $TODAY.

$AGENDA"

# Enviar por Telegram
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="$TELEGRAM_USER_ID" \
  -d text="$MESSAGE" \
  > /dev/null

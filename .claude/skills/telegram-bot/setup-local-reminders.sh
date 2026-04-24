#!/bin/bash
# Claudia OS — Instalar notificaciones locales via launchd (macOS)
# Instala: recordatorios (siempre) + briefings (si briefing.json existe)
#
# Uso: bash setup-local-reminders.sh [--uninstall]

set -e

CLAUDIA_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
CREDS_FILE="$CLAUDIA_ROOT/user/credentials/.env"
SETTINGS_FILE="$CLAUDIA_ROOT/user/config/settings.json"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

PLIST_REMINDERS="com.claudia-os.reminders.plist"
PLIST_BRIEFING_PREFIX="com.claudia-os.briefing"

# --- Uninstall ---
if [ "$1" = "--uninstall" ]; then
  echo "Desinstalando notificaciones locales..."
  launchctl bootout "gui/$(id -u)/$PLIST_REMINDERS" 2>/dev/null || true
  rm -f "$LAUNCH_AGENTS/$PLIST_REMINDERS"
  # Eliminar todos los briefings
  for plist in "$LAUNCH_AGENTS"/${PLIST_BRIEFING_PREFIX}.*.plist; do
    [ -f "$plist" ] || continue
    label=$(basename "$plist" .plist)
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    rm -f "$plist"
  done
  echo "Hecho. Todos los LaunchAgents de Claudia OS han sido eliminados."
  exit 0
fi

# --- Validaciones ---
if [[ "$(uname)" != "Darwin" ]]; then
  echo "Error: este script solo funciona en macOS (usa launchd)." >&2
  echo "En Windows usa setup-local-reminders.ps1. En Linux, configura un cron (ver SKILL.md)." >&2
  exit 1
fi

if [ ! -f "$CREDS_FILE" ]; then
  echo "Error: no existe $CREDS_FILE" >&2
  echo "Crea el fichero con TELEGRAM_BOT_TOKEN y TELEGRAM_USER_ID." >&2
  exit 1
fi

# Verificar que las vars existen
source <(grep -v '^#' "$CREDS_FILE" | sed 's/^/export /')
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_USER_ID" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no definidos en .env" >&2
  exit 1
fi

# Verificar node
if ! command -v node &>/dev/null; then
  echo "Error: node no encontrado. Instala Node.js 18+." >&2
  exit 1
fi

mkdir -p "$LAUNCH_AGENTS"
mkdir -p "$CLAUDIA_ROOT/user/logs"

NODE_PATH="$(which node)"

# ============================================================
# 1. RECORDATORIOS (siempre)
# ============================================================

cat > "$LAUNCH_AGENTS/$PLIST_REMINDERS" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_REMINDERS</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_PATH</string>
        <string>$SKILL_DIR/check_reminders.js</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SKILL_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>$TELEGRAM_BOT_TOKEN</string>
        <key>TELEGRAM_USER_ID</key>
        <string>$TELEGRAM_USER_ID</string>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>StandardOutPath</key>
    <string>$CLAUDIA_ROOT/user/logs/reminders.log</string>
    <key>StandardErrorPath</key>
    <string>$CLAUDIA_ROOT/user/logs/reminders.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$PLIST_REMINDERS" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/$PLIST_REMINDERS"

echo ""
echo "✓ Recordatorios instalados (check cada 5 min)"

# ============================================================
# 2. BRIEFINGS (solo si briefing.json existe)
# ============================================================

# Limpiar briefings anteriores
for plist in "$LAUNCH_AGENTS"/${PLIST_BRIEFING_PREFIX}.*.plist; do
  [ -f "$plist" ] || continue
  label=$(basename "$plist" .plist)
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  rm -f "$plist"
done

if [ -f "$SETTINGS_FILE" ]; then
  if command -v python3 &>/dev/null; then
    SCHEDULES=$(python3 -c "
import json, sys
with open('$SETTINGS_FILE') as f:
    cfg = json.load(f).get('skill_briefing', {})
if not cfg.get('enabled', False):
    sys.exit(0)
for s in cfg.get('schedules', []):
    name = s['name']
    hour = s.get('hour', 8)
    minute = s.get('minute', 0)
    print(f'{name}|{hour}|{minute}')
" 2>/dev/null) || true

    if [ -n "$SCHEDULES" ]; then
      while IFS='|' read -r sname shour sminute; do
        # Sanitizar nombre para el label del plist
        safe_name=$(echo "$sname" | sed 's/[^a-zA-Z0-9_-]/_/g')
        plist_label="${PLIST_BRIEFING_PREFIX}.${safe_name}"
        plist_file="$LAUNCH_AGENTS/${plist_label}.plist"

        cat > "$plist_file" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$plist_label</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_PATH</string>
        <string>$SKILL_DIR/send_briefing.js</string>
        <string>$sname</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SKILL_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>$TELEGRAM_BOT_TOKEN</string>
        <key>TELEGRAM_USER_ID</key>
        <string>$TELEGRAM_USER_ID</string>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$shour</integer>
        <key>Minute</key>
        <integer>$sminute</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$CLAUDIA_ROOT/user/logs/briefing.log</string>
    <key>StandardErrorPath</key>
    <string>$CLAUDIA_ROOT/user/logs/briefing.log</string>
</dict>
</plist>
PLIST

        launchctl bootstrap "gui/$(id -u)" "$plist_file"
        echo "✓ Briefing \"$sname\" instalado (${shour}:$(printf '%02d' $sminute))"
      done <<< "$SCHEDULES"
    fi
  else
    echo "⚠ python3 no encontrado — skill_briefing ignorado. Instala Python 3 para activar briefings."
  fi
else
  echo "  (Sin briefing — añade skill_briefing a user/config/settings.json para activarlo)"
fi

echo ""
echo "Logs en: $CLAUDIA_ROOT/user/logs/"
echo ""
echo "Notas:"
echo "  - Funciona mientras el Mac esté encendido (no necesita VPS)"
echo "  - Si el Mac estaba dormido, las notificaciones se envían al despertar"
echo "  - Los recordatorios con ctx=yes se envían como notificación simple"
echo "    (el enriquecimiento con Claude requiere el bot completo)"
echo ""
echo "Para desinstalar: bash $0 --uninstall"
echo "Para actualizar tras cambiar settings.json: volver a ejecutar este script"

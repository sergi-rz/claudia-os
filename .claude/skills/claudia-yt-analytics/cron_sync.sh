#!/usr/bin/env bash
# Sync semanal de YouTube Analytics
# Ejecutar después de corpus-sync para que el corpus esté actualizado

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SKILL_DIR/venv/bin/activate"
SCRIPT="$SKILL_DIR/yt_analytics.py"

CHANNEL="${1:?Uso: cron_sync.sh <nombre-canal>}"

source "$VENV"

# Sync incremental (desde último sync - 3 días de overlap)
python3 "$SCRIPT" --action sync --channel "$CHANNEL"

# Linkear corpus si hay workspace configurado
python3 "$SCRIPT" --action corpus-link --channel "$CHANNEL"

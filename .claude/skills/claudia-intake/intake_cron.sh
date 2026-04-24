#!/bin/bash
# Claudia OS — Intake Pipeline Cron
#
# Uso:
#   intake_cron.sh feeds     — poll de feeds (cada 6h)
#   intake_cron.sh process   — procesar cola + briefing (diario 7:30)
#   intake_cron.sh full      — feeds + process + briefing
#
# Crontab (sustituye /ruta/a/claudia-os por la ruta absoluta de tu clon;
# horas configurables en user/config/settings.json → skill_intake):
#   0 */6 * * * /ruta/a/claudia-os/.claude/skills/claudia-intake/intake_cron.sh feeds >> ~/.claude/logs/intake.log 2>&1
#   0 13 * * * /ruta/a/claudia-os/.claude/skills/claudia-intake/intake_cron.sh process >> ~/.claude/logs/intake.log 2>&1

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDIA_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CREDS_FILE="$CLAUDIA_ROOT/user/credentials/.env"
LOG_DIR="$HOME/.claude/logs"

mkdir -p "$LOG_DIR"

# Load env
if [ -f "$CREDS_FILE" ]; then
  set -a
  source "$CREDS_FILE"
  set +a
fi

cd "$CLAUDIA_ROOT"
git pull --rebase 2>/dev/null || true

MODE="${1:-process}"
TS=$(date -Iseconds)

echo ""
echo "=== intake_cron [$MODE] — $TS ==="

if [ "$MODE" = "feeds" ] || [ "$MODE" = "full" ]; then
  echo "[$TS] Polling feeds..."
  python3 "$SCRIPT_DIR/intake_feeds.py" || echo "[WARN] intake_feeds.py failed"
fi

if [ "$MODE" = "process" ] || [ "$MODE" = "full" ]; then
  echo "[$TS] Processing queue..."
  python3 "$SCRIPT_DIR/intake_process.py" || echo "[WARN] intake_process.py failed"

  echo "[$TS] Generating briefing..."
  python3 "$SCRIPT_DIR/intake_briefing.py" || echo "[WARN] intake_briefing.py failed"
fi

# Expire old items (lightweight, runs always)
python3 -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from intake_queue import expire_old
n = expire_old(14)
if n: print(f'Expired {n} items')
" || true

# Git commit if changes
cd "$CLAUDIA_ROOT"
git add user/vault/ user/config/feeds.json 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "intake cron: $(date +%Y-%m-%d) [$MODE]" || true
  git push 2>/dev/null || true
fi

echo "=== intake_cron done ==="

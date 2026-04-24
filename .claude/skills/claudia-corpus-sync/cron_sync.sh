#!/bin/bash
# Sincronización automatizada del corpus de un workspace.
# Pensado para ejecutarse vía cron — hace pull, sincroniza, commit y push.
#
# Uso (cron — sustituye /ruta/a/claudia-os por la ruta absoluta de tu clon):
#   */30 * * * * /ruta/a/claudia-os/.claude/skills/claudia-corpus-sync/cron_sync.sh <workspace>
#
# Uso manual:
#   ./cron_sync.sh <workspace>

set -e

if [ -z "$1" ]; then
    echo "Uso: $0 <workspace>"
    exit 1
fi

WORKSPACE="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
WORKSPACE_DIR="$REPO_DIR/user/workspaces/$WORKSPACE"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "ERROR: workspace '$WORKSPACE' no existe en $WORKSPACE_DIR"
    exit 1
fi

if [ ! -f "$WORKSPACE_DIR/corpus.json" ]; then
    echo "ERROR: falta $WORKSPACE_DIR/corpus.json"
    exit 1
fi

LOG_DIR="$WORKSPACE_DIR/logs"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d).md"
mkdir -p "$LOG_DIR"

log() {
    echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"
}

log "Inicio sincronización corpus ($WORKSPACE)"

cd "$REPO_DIR" && git pull >> "$LOG_FILE" 2>&1

python3 "$SCRIPT_DIR/sync.py" "$WORKSPACE" --sync >> "$LOG_FILE" 2>&1

CORPUS_PATHS=$(python3 -c "
import json
c = json.load(open('$WORKSPACE_DIR/corpus.json'))
print(' '.join(f'user/workspaces/$WORKSPACE/{s[\"corpus_dir\"]}/' for s in c.get('sources', {}).values()))
")

cd "$REPO_DIR"
if [ -n "$(git status --porcelain $CORPUS_PATHS 2>/dev/null)" ]; then
    git add $CORPUS_PATHS
    git commit -m "corpus-sync: $WORKSPACE (auto)"
    git push
    log "Commit y push realizados"
else
    log "Corpus al día, sin cambios"
fi

log "Fin sincronización"

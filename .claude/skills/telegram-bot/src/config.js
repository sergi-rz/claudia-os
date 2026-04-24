import { join } from 'path';
import { readFileSync } from 'fs';
import { CLAUDIA_ROOT } from './env.js';

export const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
export const ALLOWED_USER_ID = Number(process.env.TELEGRAM_USER_ID);

export { CLAUDIA_ROOT };

// Workspaces: "claudia" (raíz) siempre existe; los demás se cargan de user/config.json
const SKILL_DIR = join(CLAUDIA_ROOT, '.claude/skills/telegram-bot');
const USER_CONFIG = join(SKILL_DIR, 'user/config.json');

function loadProjects() {
  const projects = { claudia: CLAUDIA_ROOT };
  try {
    const cfg = JSON.parse(readFileSync(USER_CONFIG, 'utf-8'));
    for (const [name, relPath] of Object.entries(cfg.workspaces || {})) {
      projects[name] = join(CLAUDIA_ROOT, relPath);
    }
  } catch {
    // user/config.json no existe o es inválido — solo "claudia" disponible
  }
  return projects;
}

export const PROJECTS = loadProjects();

// Default: raíz de claudia-os (carga CLAUDE.md global, Claudia decide el workspace)
export const DEFAULT_PROJECT = 'claudia';

export const CLAUDE_TIMEOUT = 5 * 60 * 1000;  // 5 minutos
export const CLAUDE_MAX_TURNS = 25;
export const MAX_MESSAGE_LENGTH = 4096;        // límite de Telegram

export const WHISPER_PATH = '/opt/whisper.cpp/build/bin/whisper-cli';
export const WHISPER_MODEL = '/opt/whisper.cpp/models/ggml-base.bin';

export const HTTP_PORT   = Number(process.env.HTTP_PORT) || 3001;
export const HTTP_SECRET = process.env.HTTP_SECRET;

export const SESSIONS_FILE = join(CLAUDIA_ROOT, '.claude/skills/telegram-bot/user/sessions.json');
export const TMP_DIR = '/tmp/claudia-telegram';

// Ruta al script de calendario
export const CALENDAR_SCRIPT = join(CLAUDIA_ROOT, '.claude/skills/claudia-calendar/fetch_calendar.py');

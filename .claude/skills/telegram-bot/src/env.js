/**
 * Resolución de la raíz de Claudia OS y carga de variables desde user/credentials/.env.
 *
 * Orden de resolución de CLAUDIA_ROOT:
 *   1. process.env.CLAUDIA_ROOT si está definido (override explícito)
 *   2. Derivado de la ubicación de este fichero:
 *        src/env.js → .claude/skills/telegram-bot/src/env.js
 *        (subir 4 niveles hasta la raíz del repo)
 *
 * No asume $HOME/claudia-os — el repo puede clonarse en cualquier ruta.
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

function resolveClaudiaRoot() {
  if (process.env.CLAUDIA_ROOT) return process.env.CLAUDIA_ROOT;
  const here = fileURLToPath(import.meta.url);
  // src → telegram-bot → skills → .claude → <repo>
  return resolve(dirname(here), '..', '..', '..', '..');
}

const CLAUDIA_ROOT = resolveClaudiaRoot();
const ENV_FILE = join(CLAUDIA_ROOT, 'user/credentials/.env');

if (existsSync(ENV_FILE)) {
  const lines = readFileSync(ENV_FILE, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const value = trimmed.slice(eqIdx + 1).trim();
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
}

export { CLAUDIA_ROOT };

#!/usr/bin/env node
/**
 * send_briefing.js
 * Lee briefing.json, genera el mensaje del briefing y lo envía por Telegram.
 *
 * Uso: node send_briefing.js <schedule_name>
 * Ejemplo: node send_briefing.js mañana
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import https from 'https';
import { CLAUDIA_ROOT } from './src/env.js';

const SETTINGS_FILE = join(CLAUDIA_ROOT, 'user/config/settings.json');

if (!existsSync(SETTINGS_FILE)) {
  console.log('[briefing] No existe settings.json, nada que hacer.');
  process.exit(0);
}

const settings = JSON.parse(readFileSync(SETTINGS_FILE, 'utf8'));
const config = settings.skill_briefing;

if (!config) {
  console.log('[briefing] No hay skill_briefing en settings.json, nada que hacer.');
  process.exit(0);
}

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_USER_ID;

if (!BOT_TOKEN || !CHAT_ID) {
  console.error('[briefing] Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID');
  process.exit(1);
}

if (!config.enabled) {
  console.log('[briefing] Briefing desactivado.');
  process.exit(0);
}

const scheduleName = process.argv[2];
if (!scheduleName) {
  console.error('[briefing] Uso: node send_briefing.js <schedule_name>');
  process.exit(1);
}

const schedule = config.schedules?.find(s => s.name === scheduleName);
if (!schedule) {
  console.error(`[briefing] Schedule "${scheduleName}" no encontrado en settings.json`);
  process.exit(1);
}

const tz = settings.timezone || 'UTC';
const now = new Date();

// Utilidades de fecha en la timezone configurada.
function todayIsoInTz(date, timeZone) {
  // 'en-CA' produce formato 'YYYY-MM-DD', estable y ordenable.
  return date.toLocaleDateString('en-CA', { timeZone });
}

function dayCodeInTz(date, timeZone) {
  const short = date.toLocaleDateString('en-US', { timeZone, weekday: 'short' }).toLowerCase();
  return short.slice(0, 3); // 'mon', 'tue', ...
}

// Verificar que hoy es un día válido para este schedule (en la TZ del usuario).
const today = dayCodeInTz(now, tz);
if (schedule.days && !schedule.days.includes(today)) {
  console.log(`[briefing] Hoy (${today}) no está en los días del schedule "${scheduleName}".`);
  process.exit(0);
}

// Generar las secciones
const parts = [];
const dateStr = now.toLocaleDateString('es-ES', {
  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: tz
});

parts.push(`Buenos días. Hoy es ${dateStr}.`);

for (const sectionName of (schedule.sections || [])) {
  const sectionConfig = config.sections?.[sectionName];
  if (!sectionConfig) continue;

  if (sectionName === 'calendar') {
    const calendarText = buildCalendarSection(sectionConfig);
    if (calendarText) parts.push(calendarText);
  } else if (sectionName === 'tasks') {
    const tasksText = buildTasksSection(sectionConfig);
    if (tasksText) parts.push(tasksText);
  }
}

const message = parts.join('\n\n');
await sendTelegram(message);
console.log(`[briefing] Enviado schedule "${scheduleName}".`);

// --- Section builders ---

function buildCalendarSection(cfg) {
  const daysAhead = cfg.days_ahead || 1;
  const calendarScript = join(CLAUDIA_ROOT, '.claude/skills/claudia-calendar/fetch_calendar.py');

  if (!existsSync(calendarScript)) {
    return '📅 Calendario: no disponible (fetch_calendar.py no encontrado).';
  }

  try {
    const output = execSync(`python3 "${calendarScript}" --days ${daysAhead}`, {
      timeout: 30000,
      encoding: 'utf8',
      env: { ...process.env, TZ: tz }
    }).trim();

    if (!output || output.startsWith('Error')) {
      return '📅 Calendario: no he podido consultar el calendario.';
    }
    return `📅 Agenda:\n${output}`;
  } catch (e) {
    console.error('[briefing] Error consultando calendario:', e.message);
    return '📅 Calendario: error al consultar.';
  }
}

function buildTasksSection(cfg) {
  const tasksFile = join(CLAUDIA_ROOT, cfg.source || 'user/workspaces/_me/notes/tasks.md');
  if (!existsSync(tasksFile)) return null;

  const content = readFileSync(tasksFile, 'utf8');
  const lines = content.split('\n');
  const parts = [];

  if (cfg.show_due_today) {
    const todayStr = todayIsoInTz(now, tz);
    const dueToday = lines.filter(l =>
      l.match(/^- \[ \]/) && l.includes(todayStr)
    ).map(l => l.replace(/^- \[ \] \d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?(?:\s+\[ctx=\w+\])? — /, '• '));

    if (dueToday.length > 0) {
      parts.push(`⏰ Vence hoy:\n${dueToday.join('\n')}`);
    }
  }

  if (cfg.show_pending) {
    const pending = lines.filter(l => l.match(/^- \[ \]/) && !l.match(/\d{4}-\d{2}-\d{2}/));
    if (pending.length > 0) {
      const items = pending.map(l => l.replace(/^- \[ \] /, '• ')).slice(0, 10);
      parts.push(`📋 Pendiente:\n${items.join('\n')}`);
    }
  }

  return parts.length > 0 ? parts.join('\n\n') : null;
}

// --- Telegram ---

function sendTelegram(text) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ chat_id: CHAT_ID, text });
    const req = https.request({
      hostname: 'api.telegram.org',
      path: `/bot${BOT_TOKEN}/sendMessage`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (res) => {
      res.resume();
      resolve();
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

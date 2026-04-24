#!/usr/bin/env node
/**
 * check_reminders.js
 * Cron script: lee tasks.md, envía por Telegram los recordatorios que vencen ahora
 * y los marca como completados.
 *
 * Formato de recordatorio:
 *   - [ ] YYYY-MM-DD HH:MM [ctx=no] — descripción   (notificación directa)
 *   - [ ] YYYY-MM-DD HH:MM [ctx=yes] — descripción  (Claude enriquece antes de notificar)
 *
 * Uso: node check_reminders.js
 * Cron sugerido: cada 5 minutos
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import https from 'https';
import http from 'http';
import { CLAUDIA_ROOT } from './src/env.js';

// Config
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID   = process.env.TELEGRAM_USER_ID;
const CLAUDIA_OS = CLAUDIA_ROOT;
const TASKS_FILE = join(CLAUDIA_OS, 'user/workspaces/_me/notes/tasks.md');
const SETTINGS_FILE = join(CLAUDIA_OS, 'user/config/settings.json');
const WINDOW_MINUTES = 5; // margen de tiempo para considerar un recordatorio como "ahora"

function loadDefaultHour() {
  try {
    if (existsSync(SETTINGS_FILE)) {
      const s = JSON.parse(readFileSync(SETTINGS_FILE, 'utf8'));
      if (Number.isInteger(s.default_reminder_hour)) return s.default_reminder_hour;
    }
  } catch {}
  return 9;
}
const DEFAULT_HOUR = String(loadDefaultHour()).padStart(2, '0');

if (!BOT_TOKEN || !CHAT_ID) {
  console.error('[reminders] Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID');
  process.exit(1);
}

if (!existsSync(TASKS_FILE)) {
  console.log('[reminders] tasks.md no existe, nada que hacer.');
  process.exit(0);
}

// Lee el fichero
let content = readFileSync(TASKS_FILE, 'utf8');
const now = new Date();

// Regex: - [ ] YYYY-MM-DD HH:MM [ctx=yes/no] — descripción
// El flag [ctx=] es opcional para compatibilidad con recordatorios sin flag
const reminderRegex = /^- \[ \] (\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?(?:\s+\[ctx=(yes|no)\])? — (.+)$/gm;

const due = [];
let match;

while ((match = reminderRegex.exec(content)) !== null) {
  const [fullLine, dateStr, timeStr, ctxFlag, description] = match;
  const datetimeStr = timeStr ? `${dateStr}T${timeStr}:00` : `${dateStr}T${DEFAULT_HOUR}:00:00`;
  const reminderDate = new Date(datetimeStr);

  const diffMs = now - reminderDate;
  const diffMin = diffMs / 60000;

  // Vence entre ahora y los últimos WINDOW_MINUTES minutos
  if (diffMin >= 0 && diffMin <= WINDOW_MINUTES) {
    due.push({ fullLine, description, dateStr, needsContext: ctxFlag === 'yes' });
  }
}

if (due.length === 0) {
  process.exit(0);
}

// Envía cada recordatorio y actualiza el fichero
for (const item of due) {
  // Marca como completada en el fichero
  const completed = item.fullLine.replace('- [ ]', `- [x]`);
  content = content.replace(item.fullLine, completed);

  // Mueve la línea a ## Completadas
  content = content.replace(completed + '\n', '');
  content = content.replace(
    /## Completadas\n/,
    `## Completadas\n${completed}\n`
  );

  let messageText;
  if (item.needsContext) {
    messageText = await enrichWithClaude(item.description);
  } else {
    messageText = `⏰ Recordatorio: ${item.description}`;
  }

  await sendTelegram(messageText);
  console.log(`[reminders] Enviado: ${item.description}${item.needsContext ? ' (con contexto)' : ''}`);
}

writeFileSync(TASKS_FILE, content, 'utf8');

// Commit y push
import { execSync } from 'child_process';
try {
  execSync(
    `cd ${CLAUDIA_OS} && git add -A && git commit -m "Recordatorio completado: ${due.map(d => d.description).join(', ')}" && git push`,
    { stdio: 'inherit' }
  );
} catch (e) {
  console.error('[reminders] Error en git:', e.message);
}

// --- Helpers ---

async function enrichWithClaude(description) {
  const prompt = `Tienes este recordatorio para el usuario: "${description}"

Busca contexto relevante en el sistema (user/workspaces/_me/notes/tasks.md, ideas.md, logs recientes, etc.) y genera una notificación enriquecida. Solo el texto de la notificación, sin markdown ni explicaciones. Empieza con ⏰`;

  const HTTP_PORT = process.env.HTTP_PORT || 3001;
  const HTTP_SECRET = process.env.HTTP_SECRET;

  return new Promise((resolve) => {
    const body = JSON.stringify({ text: prompt, secret: HTTP_SECRET, return_only: true });

    const req = http.request({
      hostname: 'localhost',
      port: HTTP_PORT,
      path: '/message',
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.ok && parsed.result) {
            console.log('[reminders] Claude enriqueció el recordatorio OK');
            resolve(parsed.result);
          } else {
            console.error('[reminders] Bot no devolvió result:', data.slice(0, 200));
            resolve(`⏰ Recordatorio: ${description}`);
          }
        } catch (e) {
          console.error('[reminders] Error parseando respuesta del bot:', e.message);
          resolve(`⏰ Recordatorio: ${description}`);
        }
      });
    });

    req.setTimeout(120000, () => {
      req.destroy();
      console.error('[reminders] Timeout esperando respuesta del bot');
      resolve(`⏰ Recordatorio: ${description}`);
    });

    req.on('error', (e) => {
      console.error('[reminders] Error HTTP al bot:', e.message);
      resolve(`⏰ Recordatorio: ${description}`);
    });

    req.write(body);
    req.end();
  });
}

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

import { Telegraf } from 'telegraf';
import { createServer } from 'http';
import { existsSync, mkdirSync, appendFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import {
  BOT_TOKEN, ALLOWED_USER_ID, PROJECTS, DEFAULT_PROJECT,
  TMP_DIR, CALENDAR_SCRIPT, HTTP_PORT, HTTP_SECRET,
  CLAUDIA_ROOT,
} from './config.js';
import { runClaude } from './claude.js';
import { enqueue, cancelCurrent, getQueueLength, isBusy } from './queue.js';
import { loadSessions, getSession, setSession, clearSession } from './session.js';
import { transcribeAudio, isWhisperAvailable } from './transcriber.js';
import { splitMessage, downloadFile, cleanupFile } from './utils.js';

// Init
loadSessions();

if (!existsSync(TMP_DIR)) mkdirSync(TMP_DIR, { recursive: true });

const bot = new Telegraf(BOT_TOKEN, { handlerTimeout: 10 * 60 * 1000 });

// Auth: solo el usuario autorizado. El resto se ignora.
bot.use((ctx, next) => {
  if (ctx.from?.id !== ALLOWED_USER_ID) return;
  return next();
});

// --- Comandos ---

bot.command('start', (ctx) => ctx.reply(helpText()));
bot.command('help', (ctx) => ctx.reply(helpText()));

bot.command('new', (ctx) => {
  clearSession(ctx.chat.id);
  ctx.reply('Nueva sesión. Contexto limpio.');
});

bot.command('project', (ctx) => {
  const name = ctx.message.text.split(/\s+/)[1]?.toLowerCase();
  if (!name || !PROJECTS[name]) {
    const available = Object.keys(PROJECTS).join(', ');
    return ctx.reply(`Proyecto no válido. Disponibles: ${available}`);
  }
  setSession(ctx.chat.id, { project: name, sessionId: null });
  ctx.reply(`Proyecto: ${name}\nSesión reiniciada.`);
});

bot.command('status', (ctx) => {
  const session = getSession(ctx.chat.id);
  const project = session?.project || DEFAULT_PROJECT;
  const hasSession = session?.sessionId ? 'Sí' : 'No';

  ctx.reply(
    `Proyecto: ${project}\n` +
    `Sesión activa: ${hasSession}\n` +
    `Procesando: ${isBusy() ? 'Sí' : 'No'}\n` +
    `Cola: ${getQueueLength()} pendientes\n` +
    `Whisper: ${isWhisperAvailable() ? 'OK' : 'No disponible'}`
  );
});

bot.command('cancel', (ctx) => {
  if (cancelCurrent()) {
    ctx.reply('Tarea cancelada.');
  } else {
    ctx.reply('No hay tarea en ejecución.');
  }
});

// /agenda [días] — consulta directa al calendario sin pasar por Claude
bot.command('agenda', async (ctx) => {
  const days = parseInt(ctx.message.text.split(/\s+/)[1]) || 1;
  try {
    const result = execSync(`python3 "${CALENDAR_SCRIPT}" --days ${Math.min(days, 30)}`, {
      timeout: 15000,
      encoding: 'utf8',
    });
    const chunks = splitMessage(result || 'No hay eventos.');
    for (const chunk of chunks) {
      await ctx.reply(chunk);
    }
  } catch (err) {
    ctx.reply(`Error al consultar el calendario: ${err.message.slice(0, 300)}`);
  }
});

// --- Intake: paths ---

const INTAKE_ADD_SCRIPT = join(
  CLAUDIA_ROOT,
  '.claude/skills/claudia-intake/intake_add.py'
);

// --- Mensajes de texto ---

bot.on('text', async (ctx) => {
  const text = ctx.message.text;
  if (text.startsWith('/')) return;

  // Intake: comando "procesa N,M" (respuesta a briefing de feeds)
  const processMatch = text.trim().match(/^procesa\s+([\d,\s]+)$/i);
  if (processMatch) {
    try {
      const indices = processMatch[1].split(',').map(s => s.trim()).filter(Boolean).join(',');
      const result = execSync(
        `python3 "${INTAKE_ADD_SCRIPT}" --promote-feed ${indices}`,
        { timeout: 10000, encoding: 'utf8' }
      );
      const parsed = JSON.parse(result);
      if (parsed.promoted > 0) {
        await ctx.reply(`Encolados: ${parsed.titles.join(', ')}. Se procesarán en el próximo ciclo.`);
      } else {
        await ctx.reply('No se encontraron items de feeds con esos índices.');
      }
    } catch (err) {
      await ctx.reply(`Error al procesar feeds: ${err.message.slice(0, 200)}`);
    }
    return;
  }

  // Intake: URL bare o con keyword "intake"/"encola"
  const urlMatch = text.match(/https?:\/\/[^\s]+/);
  const isIntakeKeyword = /\b(intake|encola|guarda esto)\b/i.test(text);
  const isBareUrl = urlMatch && text.trim() === urlMatch[0];

  if (urlMatch && (isBareUrl || isIntakeKeyword)) {
    try {
      const url = urlMatch[0];
      const context = text !== url ? text.replace(url, '').trim() : '';
      const args = [`--url`, url, `--source`, `telegram`];
      if (context) args.push(`--context`, context);
      const result = execSync(
        `python3 "${INTAKE_ADD_SCRIPT}" ${args.map(a => `"${a}"`).join(' ')}`,
        { timeout: 10000, encoding: 'utf8' }
      );
      const parsed = JSON.parse(result);
      if (parsed.status === 'duplicate') {
        await ctx.reply('Ya está en la cola.');
      } else {
        await ctx.reply('Encolado para el próximo briefing.');
      }
    } catch (err) {
      await ctx.reply(`Error al encolar: ${err.message.slice(0, 200)}`);
    }
    return;
  }

  await handlePrompt(ctx, text);
});

// --- Audio ---

bot.on('voice', async (ctx) => {
  if (!isWhisperAvailable()) {
    return ctx.reply('Whisper no está disponible. Escríbelo.');
  }

  const waiting = await ctx.reply('Transcribiendo audio...');

  try {
    const fileId = ctx.message.voice.file_id;
    const oggPath = join(TMP_DIR, `voice_${Date.now()}.ogg`);
    await downloadFile(bot, fileId, oggPath);

    const transcription = await transcribeAudio(oggPath);
    await ctx.telegram.editMessageText(
      ctx.chat.id, waiting.message_id, null,
      `Transcripción: ${transcription}\n\nProcesando...`
    );

    await handlePrompt(ctx, transcription);
  } catch (err) {
    console.error('[VOICE ERR]', err.message);
    await ctx.telegram.editMessageText(
      ctx.chat.id, waiting.message_id, null,
      `No pude transcribir el audio: ${err.message}`
    );
  }
});

// --- Fotos ---

bot.on('photo', async (ctx) => {
  const photo = ctx.message.photo[ctx.message.photo.length - 1];
  const caption = ctx.message.caption || 'Describe esta imagen';
  const imgPath = join(TMP_DIR, `img_${Date.now()}.jpg`);

  const waiting = await ctx.reply('Procesando imagen...');

  try {
    await downloadFile(bot, photo.file_id, imgPath);
    const prompt = `Lee la imagen en ${imgPath} y responde: ${caption}`;

    await handlePrompt(ctx, prompt);
  } catch (err) {
    console.error('[PHOTO ERR]', err.message);
    await ctx.telegram.editMessageText(
      ctx.chat.id, waiting.message_id, null,
      `Error con la imagen: ${err.message}`
    );
  } finally {
    cleanupFile(imgPath);
  }
});

// --- Handler principal ---

async function handlePrompt(ctx, prompt) {
  const chatId = ctx.chat.id;

  if (isBusy()) {
    const pos = getQueueLength() + 1;
    await ctx.reply(`En cola (posición ${pos}). Espera...`);
  }

  try {
    const result = await enqueue(async () => {
      const typing = setInterval(() => {
        ctx.sendChatAction('typing').catch(() => {});
      }, 4000);

      try {
        ctx.sendChatAction('typing').catch(() => {});
        return await runClaude(chatId, prompt);
      } finally {
        clearInterval(typing);
      }
    });

    const chunks = splitMessage(result);
    for (const chunk of chunks) {
      await ctx.reply(chunk, { parse_mode: undefined });
    }

    logInteraction(ctx, prompt, result);
  } catch (err) {
    console.error(`[CLAUDE ERR] ${err.message}`);
    await ctx.reply(`Error: ${err.message.slice(0, 500)}`);
    logInteraction(ctx, prompt, `ERROR: ${err.message}`);
  }
}

// --- Logging ---

function logInteraction(ctx, prompt, response) {
  try {
    const session = getSession(ctx.chat.id);
    const project = session?.project || DEFAULT_PROJECT;
    const logDir = join(PROJECTS[project] || PROJECTS.claudia, 'logs');

    if (!existsSync(logDir)) mkdirSync(logDir, { recursive: true });

    const now = new Date();
    const dateStr = now.toISOString().slice(0, 10);
    const timeStr = now.toISOString();
    const logFile = join(logDir, `${dateStr}.md`);

    const entry = `\n### ${timeStr} — Telegram\n- **Prompt:** ${prompt.slice(0, 200)}\n- **Respuesta:** ${response.slice(0, 300)}\n`;
    appendFileSync(logFile, entry);
  } catch {
    // Logging no debería romper el flujo
  }
}

function helpText() {
  return (
    'Claudia OS — Bot de Telegram\n\n' +
    'Envía texto, audio o imagen y Claudia responde.\n\n' +
    'Comandos:\n' +
    '/agenda [días] — Consultar calendario (sin IA)\n' +
    '/new — Nueva sesión (olvida contexto)\n' +
    '/project <nombre> — Cambiar workspace\n' +
    '/status — Estado del bot\n' +
    '/cancel — Cancelar tarea en ejecución\n' +
    '/help — Esta ayuda\n\n' +
    `Workspaces: ${Object.keys(PROJECTS).join(', ')}`
  );
}

// --- HTTP API (Siri / Tailscale) ---

createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/message') {
    res.writeHead(404).end();
    return;
  }

  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', async () => {
    try {
      const { text, secret, return_only } = JSON.parse(body);

      if (!text || !HTTP_SECRET || secret !== HTTP_SECRET) {
        res.writeHead(401).end('Unauthorized');
        return;
      }
      const voice = /[,.]?\s*responde por voz\.?$/i.test(text);
      const cleanText = text.replace(/[,.]?\s*responde por voz\.?$/i, '').trim();

      // return_only: solo devuelve el texto, sin enviar por Telegram (usado por check_reminders.js)
      if (return_only) {
        const result = await enqueue(async () => runClaude(ALLOWED_USER_ID, cleanText));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, result }));
        return;
      }

      let fullResponse = '';
      const fakeCtx = {
        chat: { id: ALLOWED_USER_ID },
        reply: (msg, opts) => {
          fullResponse += (fullResponse ? ' ' : '') + msg;
          return bot.telegram.sendMessage(ALLOWED_USER_ID, msg, opts);
        },
        sendChatAction: (action) => bot.telegram.sendChatAction(ALLOWED_USER_ID, action).catch(() => {}),
      };

      await handlePrompt(fakeCtx, cleanText);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, voice_text: voice ? fullResponse : '' }));
    } catch {
      res.writeHead(400).end('Bad request');
    }
  });
}).listen(HTTP_PORT, '0.0.0.0', () => {
  console.log(`Claudia HTTP API escuchando en :${HTTP_PORT}`);
});

// --- Arranque ---

bot.launch({ dropPendingUpdates: true });
console.log('Claudia OS — Bot de Telegram iniciado');

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

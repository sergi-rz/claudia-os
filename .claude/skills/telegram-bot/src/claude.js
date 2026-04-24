import { spawn } from 'child_process';
import { getSession, setSession } from './session.js';
import { setChildProcess } from './queue.js';
import { PROJECTS, DEFAULT_PROJECT, CLAUDE_TIMEOUT, CLAUDE_MAX_TURNS } from './config.js';

export async function runClaude(chatId, prompt) {
  const session = getSession(chatId);
  const project = session?.project || DEFAULT_PROJECT;
  const cwd = PROJECTS[project];

  const args = [
    '-p', prompt,
    '--output-format', 'json',
    '--max-turns', String(CLAUDE_MAX_TURNS),
    '--allowedTools', 'Bash,Read,Write,Edit,Glob,Grep',
  ];

  // Continuar conversación anterior
  if (session?.sessionId) {
    args.push('--resume', session.sessionId);
  }

  // Env explícito — PM2 no carga .bashrc
  const env = {
    HOME: process.env.HOME,
    PATH: process.env.PATH || '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    TERM: 'dumb',
    USER: process.env.USER,
    LANG: 'en_US.UTF-8',
  };

  // Pasar token de Claude si existe en el entorno
  if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
    env.CLAUDE_CODE_OAUTH_TOKEN = process.env.CLAUDE_CODE_OAUTH_TOKEN;
  }

  return new Promise((resolve, reject) => {
    // CRÍTICO: stdin en 'ignore' — sin esto Claude se cuelga esperando input
    const child = spawn('claude', args, {
      cwd,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    setChildProcess(child);

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => { stdout += chunk; });
    child.stderr.on('data', (chunk) => { stderr += chunk; });

    const timeout = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error('Claude tardó demasiado. Intenta algo más concreto.'));
    }, CLAUDE_TIMEOUT);

    child.on('close', (code) => {
      clearTimeout(timeout);

      if (code !== 0 && !stdout) {
        const errMsg = stderr.slice(0, 500) || `Claude salió con código ${code}`;
        reject(new Error(errMsg));
        return;
      }

      try {
        const parsed = parseClaudeOutput(stdout);
        if (parsed.sessionId) {
          setSession(chatId, { sessionId: parsed.sessionId, project });
        }
        resolve(parsed.text);
      } catch {
        resolve(stdout?.slice(0, 4000) || 'Claude no devolvió respuesta.');
      }
    });

    child.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

function parseClaudeOutput(raw) {
  const lines = raw.trim().split('\n').filter(Boolean);
  let text = '';
  let sessionId = null;

  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      if (obj.session_id) sessionId = obj.session_id;
      if (obj.result) text = extractText(obj.result);
    } catch {
      // Not JSON
    }
  }

  if (!text) {
    try {
      const obj = JSON.parse(raw);
      if (obj.result) text = extractText(obj.result);
      if (obj.session_id) sessionId = obj.session_id;
    } catch {
      text = raw.slice(0, 4000);
    }
  }

  return { text: text || 'Sin respuesta.', sessionId };
}

function extractText(result) {
  if (typeof result === 'string') return result;
  if (Array.isArray(result)) {
    return result
      .filter((b) => b.type === 'text')
      .map((b) => b.text)
      .join('\n');
  }
  return JSON.stringify(result).slice(0, 4000);
}

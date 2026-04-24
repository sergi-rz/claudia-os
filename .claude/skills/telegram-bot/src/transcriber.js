import { execFile } from 'child_process';
import { promisify } from 'util';
import { existsSync, unlinkSync } from 'fs';
import { WHISPER_PATH, WHISPER_MODEL } from './config.js';

const exec = promisify(execFile);

export async function transcribeAudio(oggPath) {
  const wavPath = oggPath.replace(/\.\w+$/, '.wav');

  try {
    // Convertir OGG/OPUS a WAV 16kHz mono (lo que necesita whisper)
    await exec('ffmpeg', ['-i', oggPath, '-ar', '16000', '-ac', '1', '-y', wavPath], {
      timeout: 30000,
    });

    if (!existsSync(wavPath)) {
      throw new Error('ffmpeg no generó el archivo WAV');
    }

    // Transcribir
    const { stdout } = await exec(WHISPER_PATH, [
      '-m', WHISPER_MODEL,
      '-f', wavPath,
      '-l', 'auto',
      '--no-timestamps',
      '-nt',
    ], {
      timeout: 60000,
    });

    const text = stdout.trim();
    if (!text) {
      throw new Error('Whisper no produjo transcripción');
    }

    return text;
  } finally {
    // Limpiar ficheros temporales
    try { unlinkSync(oggPath); } catch {}
    try { unlinkSync(wavPath); } catch {}
  }
}

export function isWhisperAvailable() {
  return existsSync(WHISPER_PATH) && existsSync(WHISPER_MODEL);
}

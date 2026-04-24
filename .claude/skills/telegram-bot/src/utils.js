import { writeFileSync, unlinkSync } from 'fs';
import { MAX_MESSAGE_LENGTH } from './config.js';
import https from 'https';

// Telegram tiene un límite de 4096 caracteres por mensaje
export function splitMessage(text) {
  if (text.length <= MAX_MESSAGE_LENGTH) return [text];

  const chunks = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= MAX_MESSAGE_LENGTH) {
      chunks.push(remaining);
      break;
    }

    // Intentar cortar por salto de línea
    let splitAt = remaining.lastIndexOf('\n', MAX_MESSAGE_LENGTH);
    if (splitAt < MAX_MESSAGE_LENGTH / 2) {
      splitAt = remaining.lastIndexOf(' ', MAX_MESSAGE_LENGTH);
    }
    if (splitAt < MAX_MESSAGE_LENGTH / 2) {
      splitAt = MAX_MESSAGE_LENGTH;
    }

    chunks.push(remaining.slice(0, splitAt));
    remaining = remaining.slice(splitAt).trimStart();
  }

  return chunks;
}

export async function downloadFile(bot, fileId, destPath) {
  const fileLink = await bot.telegram.getFileLink(fileId);
  const url = fileLink.href || fileLink;

  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        writeFileSync(destPath, Buffer.concat(chunks));
        resolve(destPath);
      });
      res.on('error', reject);
    }).on('error', reject);
  });
}

// Limpiar imagen temporal tras procesarla
export function cleanupFile(filePath) {
  try { unlinkSync(filePath); } catch {}
}

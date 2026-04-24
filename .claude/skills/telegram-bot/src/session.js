import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { SESSIONS_FILE } from './config.js';

let sessions = {};

export function loadSessions() {
  if (existsSync(SESSIONS_FILE)) {
    try {
      sessions = JSON.parse(readFileSync(SESSIONS_FILE, 'utf8'));
    } catch {
      sessions = {};
    }
  }
}

function saveSessions() {
  mkdirSync(dirname(SESSIONS_FILE), { recursive: true });
  writeFileSync(SESSIONS_FILE, JSON.stringify(sessions, null, 2));
}

export function getSession(chatId) {
  return sessions[chatId] || null;
}

export function setSession(chatId, data) {
  sessions[chatId] = { ...sessions[chatId], ...data };
  saveSessions();
}

export function clearSession(chatId) {
  delete sessions[chatId];
  saveSessions();
}

// PM2 config — los valores reales van en .env (no commitear este fichero con tokens)
// Uso: pm2 start ecosystem.config.cjs

const { readFileSync, existsSync } = require('fs');
const { join } = require('path');

// Leer .env de user/credentials/
const envPath = join(__dirname, '..', '..', '..', 'user', 'credentials', '.env');
const env = {};

if (existsSync(envPath)) {
  const lines = readFileSync(envPath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...rest] = trimmed.split('=');
      env[key.trim()] = rest.join('=').trim();
    }
  }
}

module.exports = {
  apps: [{
    name: 'claudia-telegram',
    script: 'src/index.js',
    cwd: __dirname,
    env: {
      HOME: process.env.HOME,
      PATH: process.env.PATH,
      USER: process.env.USER,
      ...env,
    },
    max_memory_restart: '200M',
    restart_delay: 5000,
    max_restarts: 10,
    autorestart: true,
  }],
};

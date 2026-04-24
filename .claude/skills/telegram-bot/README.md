# Telegram Bot — Comunicacion bidireccional con Claudia

Habla con Claudia desde el movil via Telegram. Recibe briefings, recordatorios y respuestas; envia texto, audio e imagenes.

## Que hace

Este bot conecta Telegram con Claudia de forma bidireccional. Le puedes escribir desde el movil como si fuera un chat, y Claudia responde usando Claude. Tambien es el canal principal para recibir notificaciones automaticas: briefing diario con tu agenda y tareas, recordatorios programados, y alertas del sistema.

Tiene dos modos de operacion. El modo local (solo notificaciones) funciona sin servidor y es el punto de partida recomendado. El modo completo añade el bot interactivo y requiere un servidor siempre encendido.

## Funcionalidades

- **Chat interactivo** — escribe a Claudia en lenguaje natural y recibe respuestas (modo completo)
- **Audio** — envia notas de voz, se transcriben con whisper.cpp
- **Imagenes** — envia fotos para que Claudia las analice
- **Briefing diario** — resumen programado con agenda y tareas pendientes
- **Recordatorios** — notificaciones de tareas que vencen, con check cada 5 minutos
- **Deteccion de URLs** — envia una URL y se encola automaticamente en el intake pipeline
- **Workspaces** — cambia el contexto de Claudia con `/project <nombre>`
- **HTTP API** — endpoint local para integraciones (Siri, Tailscale, scripts)

## Comandos del bot

- `/agenda [dias]` — ver calendario sin pasar por IA (rapido)
- `/new` — iniciar una nueva sesion de conversacion
- `/project <nombre>` — cambiar el workspace activo
- `/status` — estado del bot y proceso PM2
- `/cancel` — cancelar la tarea en ejecucion

## Configuracion

### Paso 1 — Crear el bot en Telegram

1. Abre Telegram y busca @BotFather
2. Envia `/newbot`, elige nombre y username
3. BotFather te dara un token (formato `123456:ABC-DEF...`)

### Paso 2 — Obtener tu User ID

1. Busca @userinfobot en Telegram
2. Envia `/start`
3. Te devuelve tu ID numerico

### Paso 3 — Configurar credenciales

Añade ambos valores a `user/credentials/.env`:

```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_USER_ID=tu_id_aqui
```

Variables opcionales:
- `HTTP_PORT` — puerto del API HTTP (default: 3001)
- `HTTP_SECRET` — secreto para autenticar llamadas al API
- `CLAUDE_CODE_OAUTH_TOKEN` — necesario para que el bot ejecute Claude en cron/background

### Paso 4 — Instalar dependencias

```bash
cd .claude/skills/telegram-bot && npm install
```

Requisito: Node.js 18+.

## Modos de operacion

### Modo local (solo notificaciones)

Recordatorios por Telegram sin necesidad de servidor. Funciona mientras el equipo este encendido.

```bash
# Linux
cd .claude/skills/telegram-bot && npm install
# Añadir a crontab:
*/5 * * * * cd .claude/skills/telegram-bot && node check_reminders.js
```

```bash
# macOS
cd .claude/skills/telegram-bot && npm install
bash setup-local-reminders.sh
```

```powershell
# Windows
cd ~\.claude\skills\telegram-bot; npm install
powershell -ExecutionPolicy Bypass -File setup-local-reminders.ps1
```

Limitaciones: no hay bot interactivo (no puedes escribirle a Claudia), los recordatorios con `ctx=yes` se envian sin enriquecimiento, y si el equipo esta apagado las notificaciones se pierden (Linux) o se envian al despertar (macOS/Windows).

Para desinstalar:
- macOS: `bash setup-local-reminders.sh --uninstall`
- Windows: `powershell -File setup-local-reminders.ps1 -Uninstall`
- Linux: `crontab -e` y eliminar la linea

### Modo completo (bot interactivo + notificaciones)

Bot bidireccional con todas las automatizaciones. Requiere un servidor siempre encendido.

```bash
cd .claude/skills/telegram-bot && npm install
npm install -g pm2
pm2 start ecosystem.config.cjs
```

Crons necesarios:
```
*/5 * * * * .claude/skills/telegram-bot/watchdog.sh
*/5 * * * * cd .claude/skills/telegram-bot && node check_reminders.js
```

El watchdog revive el bot si cae y mata procesos claude colgados.

## Briefing diario

El briefing es una notificacion programada que te envia un resumen del dia (agenda, tareas pendientes). Se configura en `user/config/settings.json` (key `skill_briefing`).

La forma mas facil de configurarlo es pedirle a Claudia: "configura el briefing de la mañana". Te guiara paso a paso preguntando hora, dias y que incluir.

Ejemplo de configuracion:

```json
{
  "enabled": true,
  "schedules": [
    {
      "name": "mañana",
      "hour": 8,
      "minute": 0,
      "days": ["mon", "tue", "wed", "thu", "fri"],
      "sections": ["calendar", "tasks"]
    }
  ]
}
```

Para probar manualmente:
```bash
node .claude/skills/telegram-bot/send_briefing.js mañana
```

## HTTP API

El bot expone un endpoint HTTP local para integraciones externas:

```
POST http://localhost:3001/message
Content-Type: application/json

{
  "text": "Recuerdame comprar leche",
  "secret": "tu_HTTP_SECRET",
  "return_only": false
}
```

Usado internamente por `check_reminders.js` para enriquecer recordatorios con contexto de Claude. Tambien accesible via Tailscale o Siri Shortcuts.

## Nota de privacidad

Los bots de Telegram no soportan cifrado de extremo a extremo (solo los Secret Chats entre usuarios lo tienen). Todo lo que pase por el bot — briefings, recordatorios, notas, respuestas de Claudia — viaja por servidores de Telegram. Apto para uso personal; no lo uses para informacion confidencial de clientes o datos sensibles de negocio.

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Credenciales | `user/credentials/.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID`) |
| Config del briefing | `user/config/settings.json` → `skill_briefing` |
| Sesiones de conversacion | `user/sessions.json` (gitignored) |
| Config de PM2 | `.claude/skills/telegram-bot/ecosystem.config.cjs` |
| Logs del watchdog | `user/logs/` |

## Skills relacionadas

- **claudia-calendar** — el briefing y el comando `/agenda` consultan el calendario
- **claudia-intake** — las URLs enviadas al bot se encolan automaticamente en el pipeline de intake
- **claudia-gmail** — el briefing del intake se envia tambien por email
- **notes** — mensajes tipo "recuerdame X" se capturan como tareas/recordatorios

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/telegram-bot/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "El briefing diario debe empezar con un emoji del tiempo según la estación del año"
- "Cuando recibas una URL de YouTube, avísame antes de encolarla en vez de hacerlo automáticamente"
- "Los recordatorios con ctx=yes deben incluir el texto completo de la tarea, no solo el título"
- "Añade al comando /status el número de items pendientes en la cola del intake"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **El bot no responde**: comprobar `pm2 status` y revisar logs con `pm2 logs`. Si esta caido, `pm2 start ecosystem.config.cjs`
- **Briefing no llega**: verificar que el cron esta configurado y que `skill_briefing` en `settings.json` tiene `enabled: true`. Probar con `node send_briefing.js <nombre_schedule>`
- **Recordatorios no se envian**: comprobar que el cron de `check_reminders.js` esta activo (`crontab -l`)
- **Watchdog mata el bot**: revisar logs del watchdog en `user/logs/`. Puede ser un proceso claude colgado consumiendo recursos
- **Error de autenticacion**: verificar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_USER_ID` en `user/credentials/.env`

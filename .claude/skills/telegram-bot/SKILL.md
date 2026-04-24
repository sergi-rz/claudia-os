---
name: telegram-bot
description: "Bot de Telegram para comunicación bidireccional usuario ↔ Claudia. Gestión del proceso PM2, watchdog, briefing y recordatorios. Usar cuando haya que gestionar, debuggear o modificar el bot."
scope: core
---

# Telegram Bot — Comunicación bidireccional

Bot de Telegram que permite al usuario interactuar con Claudia desde el móvil. Soporta texto, audio (whisper.cpp), imágenes y comando /agenda.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Proceso

- **Runtime:** Node.js con PM2
- **Arranque:** `cd .claude/skills/telegram-bot && pm2 start ecosystem.config.cjs`
- **Watchdog:** cron cada 5 min → `watchdog.sh` (revive el bot si cae, mata claudes colgados)
- **Recordatorios:** cron cada 5 min → `node check_reminders.js`
- **Briefing:** configurable por el usuario (ver sección Briefing)

## Comandos del bot

- `/agenda [días]` — calendario sin IA
- `/new` — nueva sesión
- `/project <nombre>` — cambiar workspace (los disponibles se definen en `user/config.json`)
- `/status` — estado del bot
- `/cancel` — cancelar tarea en ejecución

## HTTP API (Siri / Tailscale)

POST `http://localhost:3001/message` con `{ text, secret, return_only }`. Usado por check_reminders.js para enriquecer recordatorios con contexto.

## Setup (primera vez)

> **Privacidad:** los bots de Telegram no soportan cifrado de extremo a extremo (sólo los Secret Chats lo hacen, y sólo entre usuarios). Todo lo que pase por este bot (briefings, recordatorios, notas, respuestas de Claudia) viaja por servidores de Telegram. Apto para uso personal del día a día; no lo uses como canal para información confidencial de clientes o datos sensibles de negocio.

1. Abre Telegram y busca @BotFather
2. Envía `/newbot`, elige nombre y username
3. BotFather te dará un token (formato `123456:ABC-DEF...`)
4. Para obtener tu User ID: busca @userinfobot en Telegram y envía `/start`
5. Añade ambos a `user/credentials/.env`:
   ```
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   TELEGRAM_USER_ID=tu_id_aqui
   ```

Opcionales en `.env`: `HTTP_PORT` (default 3001), `HTTP_SECRET`, `CLAUDE_CODE_OAUTH_TOKEN`.

## Modos de operación

### Modo local (solo notificaciones — recomendado para empezar)

Recordatorios de tareas via Telegram. No necesita VPS ni PM2. Funciona mientras el equipo esté encendido.

**macOS:**
```bash
cd ~/.claude/skills/telegram-bot && npm install
bash setup-local-reminders.sh
```

**Windows:**
```powershell
cd ~\.claude\skills\telegram-bot; npm install
powershell -ExecutionPolicy Bypass -File setup-local-reminders.ps1
```

**Linux:**
```bash
cd ~/.claude/skills/telegram-bot && npm install
# Añadir a crontab:
crontab -l | { cat; echo "*/5 * * * * cd .claude/skills/telegram-bot && node check_reminders.js"; } | crontab -
```

Qué hace:
- **Recordatorios** — check cada 5 min, envía por Telegram los que vencen

Limitaciones del modo local:
- Los recordatorios `ctx=yes` se envían como notificación simple (sin enriquecimiento con Claude)
- Si el equipo está dormido/apagado, las notificaciones se envían al despertar (macOS/Windows) o se pierden (Linux sin servidor)
- No hay bot interactivo (no puedes enviar mensajes a Claudia por Telegram)

Para desinstalar:
- macOS: `bash setup-local-reminders.sh --uninstall`
- Windows: `powershell -File setup-local-reminders.ps1 -Uninstall`
- Linux: editar `crontab -e` y eliminar la línea

**Requisitos:** Node.js 18+.

### Modo completo (bot interactivo + notificaciones)

Bot bidireccional + todas las automatizaciones. Requiere un servidor siempre encendido (VPS, servidor casero, o Mac que no se apague).

```bash
cd ~/.claude/skills/telegram-bot && npm install
npm install -g pm2
pm2 start ecosystem.config.cjs
```

Crons del servidor:
```
*/5 * * * * .claude/skills/telegram-bot/watchdog.sh
*/5 * * * * cd .claude/skills/telegram-bot && node check_reminders.js
```

**Requisitos:** Node.js 18+, PM2, servidor siempre encendido.

## Briefing diario

El briefing es una notificación programada con información del día (calendario, tareas, etc.). Es independiente de los recordatorios y se configura en `user/config/settings.json` (key `skill_briefing`).

### Setup conversacional

Cuando el usuario quiera configurar el briefing (dice "quiero un resumen matutino", "configura el briefing", "mándame la agenda cada mañana", etc.), **no le mandes a editar JSON**. Guíale con preguntas, una a una:

1. **¿Cuándo?**
   > ¿A qué hora quieres recibir el briefing? ¿Todos los días o solo entre semana?
   - Si dice "por la mañana" → sugerir 08:00
   - Si quiere varios envíos (mañana + tarde) → crear un schedule por cada uno
   - Pedir nombre para cada schedule si hay más de uno ("mañana", "cierre", etc.)

2. **¿Qué incluir?**
   > ¿Qué quieres que incluya? Las opciones son:
   > - **Agenda del día** — eventos de tu calendario
   > - **Tareas pendientes** — lo que tienes en tu lista
   > - Ambas
   - Si tiene calendario configurado → ofrecer ambas
   - Si no tiene calendario → ofrecer solo tareas, mencionar que puede añadir calendario después

3. **Detalles (solo si aplica):**
   - Si eligió calendario: ¿Solo hoy o también mañana? ¿Todos los calendarios o alguno específico?
   - Si eligió tareas: ¿Solo las que vencen hoy o también las pendientes sin fecha?

4. **Generar y activar:**
   - Genera la key `skill_briefing` en `user/config/settings.json` con las respuestas
   - Ejecuta el setup script correspondiente (o indica el cron para VPS)
   - Envía un briefing de prueba: `node send_briefing.js <nombre_schedule>`
   - Confirma: *"Te acabo de enviar uno de prueba. ¿Te ha llegado bien? ¿Quieres cambiar algo?"*

Si el usuario quiere **modificar** un briefing existente, lee la key `skill_briefing` de `settings.json`, pregunta qué quiere cambiar, actualiza la key y re-ejecuta el setup.

### Formato de la configuración

Key `skill_briefing` en `user/config/settings.json`:

```json
{
  "skill_briefing": {
    "enabled": true,
    "schedules": [
      {
        "name": "mañana",
        "hour": 8,
        "minute": 0,
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "sections": ["calendar", "tasks"]
      }
    ],
    "sections": {
      "calendar": {
        "days_ahead": 1,
        "calendars": "all"
      },
      "tasks": {
        "source": "user/workspaces/_me/notes/tasks.md",
        "show_pending": true,
        "show_due_today": true
      }
    }
  }
}
```

**schedules[]** — cuándo enviar. Se pueden definir varios (ej. briefing de mañana + resumen de tarde):
- `name` — identificador libre
- `hour`, `minute` — hora local (según `timezone`)
- `days` — días de la semana (`mon`-`sun`). Omitir para todos los días.
- `sections` — qué secciones incluir en este envío

**sections** — qué información incluir:
- `calendar` — eventos del calendario. `days_ahead`: cuántos días mostrar. `calendars`: `"all"` o lista de nombres de calendario específicos.
- `tasks` — tareas pendientes. `show_pending`: todas las pendientes. `show_due_today`: las que vencen hoy.

**Zona horaria** — se lee de `user/config/settings.json` (campo `timezone`). Si el usuario no la tiene configurada, preguntar y guardarla allí.

### Activación

El briefing se activa con el mismo mecanismo que los recordatorios:

- **Modo local:** el setup script (`setup-local-reminders.sh` / `.ps1`) detecta si existe la key `skill_briefing` en `settings.json` y crea los LaunchAgents/tareas programadas correspondientes.
- **Modo completo (VPS):** se añaden los crons según la configuración.
- **Sin configuración:** no se envía ningún briefing. Los recordatorios funcionan independientemente.

### Script

`send_briefing.js` — lee `skill_briefing` de `settings.json`, genera el mensaje y lo envía por Telegram. Se invoca con el nombre del schedule: `node send_briefing.js mañana`.

## Estado (gitignored)

`user/sessions.json` — sesiones persistentes de conversación.
`user/logs/` — logs del watchdog y recordatorios.

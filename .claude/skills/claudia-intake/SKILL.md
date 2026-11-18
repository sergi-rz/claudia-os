---
name: claudia-intake
description: "Pipeline de captura, procesamiento y entrega de contenido. Encola URLs, extrae wisdom en batch, genera briefing diario dual (Telegram + email)."
scope: core
user-invocable: true
argument-hint: "<url> | digest | digest feeds | status | feeds | add-feed <url>"
---

# Intake — Pipeline de contenido inteligente

Sistema de captura asíncrona y procesamiento batch de contenido externo. El usuario envía URLs por cualquier canal; el sistema las procesa en batch, extrae wisdom y envía un briefing dual (Telegram + email).

Los shorts de YouTube de los feeds se omiten (`"include_shorts": true` en el feed para incluirlos). Si
una pieza se encola con `--date` (fecha de publicación), esa es la fecha que queda en el vault.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio, si existe. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario. Si el usuario pide un ajuste permanente de la skill, guárdalo ahí: crea el fichero si no existe (`behavior.example.md` tiene ideas).

## Modelo de dos velocidades

- **Items manuales** (Telegram, `/intake`, notas): se procesan automáticamente en el cron diario
- **Items de feeds** (RSS, YouTube, Substack): se listan en el briefing sin procesar. El usuario responde "procesa 1,3" para seleccionar cuáles extraer
- **Histórico de mentores** (`claudia-mentors --backfill`): se procesa como los manuales, pero en el
  briefing sale en una sola línea con el recuento por autor. Cuenta como histórico una pieza de
  mentor publicada más de 14 días antes de procesarse

## Comandos

### `/intake <url> [contexto]`
Añade una URL a la cola de procesamiento.

```bash
python3 .claude/skills/claudia-intake/intake_add.py --url "$URL" --source manual --context "$CONTEXT"
```

Confirma: "Encolado para el próximo briefing."

### `/intake digest`
Procesa la cola pendiente ahora y genera el briefing. Sigue *Procesar la cola desde el agente* y
termina con `python3 .claude/skills/claudia-intake/intake_briefing.py`.

### `/intake digest feeds`
Igual, pero antes revisa los feeds: `python3 .claude/skills/claudia-intake/intake_feeds.py`.

### Procesar la cola desde el agente

Cuando la cola la procesa un agente (en el chat o en una tarea programada de la app de
escritorio), **el wisdom lo sintetiza ese agente**. Nunca lances `intake_process.py` sin opciones
desde aquí: eso arranca otro Claude con `claude -p`, que solo es para los crons de servidor.

1. `python3 .claude/skills/claudia-intake/intake_process.py --prepare` — descarga el contenido de
   las piezas pendientes y deja el lote en `user/vault/.index/intake_batch.json`.
2. Lee ese fichero. Para cada tanda de `batches`, haz lo que pide su `prompt`. Junta las respuestas
   en un único objeto JSON `{item_id: wisdom}` y escríbelo en `user/vault/.index/intake_batch_result.json`.
   Si una pieza pide `FETCH_URL`, léela con tu herramienta de lectura de URLs.
3. `python3 .claude/skills/claudia-intake/intake_process.py --save` — guarda en el vault, reindexa y
   borra el lote. Las piezas que no estén en el resultado vuelven a la cola.

Si `--prepare` dice que ya hay un lote sin guardar, termina ese (pasos 2 y 3) antes de preparar otro.

### `/intake status`
Muestra estadísticas de la cola.

```bash
python3 .claude/skills/claudia-intake/intake_queue.py --stats
```

### `/intake feeds`
Lista los feeds configurados en `user/config/feeds.json`.

Lee y muestra el contenido de `user/config/feeds.json`, listando nombre, URL, tipo y estado (activo/inactivo).

### `/intake add-feed <url> [nombre]`
Añade un feed al fichero de suscripciones.

Lee `user/config/feeds.json`, añade el nuevo feed al array `feeds` con `active: true` y tipo autodetectado:
- YouTube channel URLs → type: "youtube"
- Substack URLs → type: "rss" (Substack expone RSS)
- Todo lo demás → type: "rss"

Guarda el fichero y confirma.

## Arquitectura

```
Captura → queue.jsonl → Procesamiento (agente, o claude -p en cron) → vault/wisdom/ → Briefing (TG + email)
```

### Ficheros clave
- `user/vault/intake/queue.jsonl` — Cola JSONL
- `user/config/feeds.json` — Suscripciones a feeds
- `user/vault/wisdom/` — Output (mismo vault que wisdom manual)

### Qué hay que programar

Dos tareas. El cómo (crontab, tarea de la app de escritorio o programador del sistema) depende de
dónde vive la instalación: ver *Tareas programadas* en `core/architecture.md`.

| Tarea | Cada cuánto | Comandos |
|---|---|---|
| Revisar feeds | Cada 6 h (en un portátil, 1-2 veces al día basta) | `python3 .claude/skills/claudia-intake/intake_feeds.py` |
| Procesar la cola y enviar el briefing | Una vez al día | Ver abajo según dónde corra; al final, `python3 .claude/skills/claudia-intake/intake_briefing.py` |

- **En un servidor (cron)**: `intake_cron.sh feeds` e `intake_cron.sh process` (las líneas de
  crontab están en su cabecera). `process` lanza `intake_process.py` sin opciones, que sintetiza con
  `claude -p`: el único caso en que se usa.
- **En la app de escritorio**: el prompt de la tarea sigue *Procesar la cola desde el agente*
  (`--prepare`, síntesis del propio agente, `--save`) y después el briefing. Los scripts cargan el
  `.env` por su cuenta. No hace falta tener instalado ni con sesión el CLI `claude`.

### Env requerido (user/credentials/.env)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID` — Para briefing Telegram
- `CLAUDE_CODE_OAUTH_TOKEN` — Solo en servidor, para el `claude -p` del cron
- Gmail OAuth tokens — Para briefing email

## Setup

No hace falta instalar paquetes de Python: los scripts usan solo la librería estándar (las
peticiones HTTP van por `intake_http.py`). En un servidor con cron, además, el CLI `claude` con
`CLAUDE_CODE_OAUTH_TOKEN`; en el chat o en la app no hace falta.

1. Los tokens de Telegram y Gmail ya deben estar configurados (ver skills `telegram-bot` y `claudia-gmail`)
2. Añadir feeds en `user/config/feeds.json` (o usar `/intake add-feed`)
3. Programar las dos tareas (ver *Qué hay que programar*) y comprobar que la primera ejecución termina

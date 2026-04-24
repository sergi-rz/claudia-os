---
name: claudia-intake
description: "Pipeline de captura, procesamiento y entrega de contenido. Encola URLs, extrae wisdom en batch, genera briefing diario dual (Telegram + email)."
scope: core
user-invocable: true
argument-hint: "<url> | digest | digest feeds | status | feeds | add-feed <url>"
---

# Intake — Pipeline de contenido inteligente

Sistema de captura asíncrona y procesamiento batch de contenido externo. El usuario envía URLs por cualquier canal; el sistema las procesa en batch, extrae wisdom y envía un briefing dual (Telegram + email).

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Modelo de dos velocidades

- **Items manuales** (Telegram, `/intake`, notas): se procesan automáticamente en el cron diario
- **Items de feeds** (RSS, YouTube, Substack): se listan en el briefing sin procesar. El usuario responde "procesa 1,3" para seleccionar cuáles extraer

## Comandos

### `/intake <url> [contexto]`
Añade una URL a la cola de procesamiento.

```bash
python3 .claude/skills/claudia-intake/intake_add.py --url "$URL" --source manual --context "$CONTEXT"
```

Confirma: "Encolado para el próximo briefing."

### `/intake digest`
Procesa la cola pendiente ahora y genera briefing inmediato.

```bash
cd .claude/skills/claudia-intake
python3 intake_process.py && python3 intake_briefing.py
```

### `/intake digest feeds`
Pollea feeds primero, luego procesa cola y genera briefing.

```bash
cd .claude/skills/claudia-intake
python3 intake_feeds.py && python3 intake_process.py && python3 intake_briefing.py
```

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
Captura → queue.jsonl → Procesamiento (claude -p) → vault/wisdom/ → Briefing (TG + email)
```

### Ficheros clave
- `user/vault/intake/queue.jsonl` — Cola JSONL
- `user/config/feeds.json` — Suscripciones a feeds
- `user/vault/wisdom/` — Output (mismo vault que wisdom manual)

### Cron (ejemplo)
- `0 */6 * * *` — Poll de feeds (cada 6h)
- `0 13 * * *` — Procesar cola + briefing diario (13:00)

Las horas son configurables en `user/config/settings.json` (key `skill_intake`).

### Env requerido (user/credentials/.env)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID` — Para briefing Telegram
- `CLAUDE_CODE_OAUTH_TOKEN` — Para `claude -p` en cron
- Gmail OAuth tokens — Para briefing email

## Setup

1. Los tokens de Telegram y Gmail ya deben estar configurados (ver skills `telegram-bot` y `claudia-gmail`)
2. Añadir feeds en `user/config/feeds.json` (o usar `/intake add-feed`)
3. Verificar crons: `crontab -l | grep intake`

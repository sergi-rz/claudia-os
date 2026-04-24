# Claudia Intake — Pipeline de contenido

Captura contenido de cualquier canal, lo procesa en batch extrayendo conocimiento, y te envía un briefing diario por Telegram y email.

## Qué hace

Encuentras un artículo interesante, un vídeo de YouTube, un tweet con insights... pero no tienes tiempo de procesarlo ahora. Lo mandas a la cola y Claudia se encarga:

1. **Captura** — Envía una URL por Telegram, usa `/intake <url>` en conversación, o suscríbete a feeds RSS/YouTube
2. **Procesamiento** — Un cron diario extrae el contenido, lanza Claude para generar una síntesis estructurada (ideas clave, insights, citas, acciones)
3. **Briefing dual** — Recibes un mensaje en Telegram (índice rápido) y un email con todo el contenido inline

## Dos velocidades

- **Items manuales** (lo que tú envías): se procesan automáticamente en el cron diario
- **Items de feeds** (suscripciones RSS/YouTube): se listan en el briefing como títulos. Tú decides cuáles procesar respondiendo `procesa 1,3` en Telegram

## Cómo usarlo

### Desde Telegram
- Envía una URL sola → se encola automáticamente
- Envía `encola https://...` → igual
- Responde `procesa 2,5` al briefing → promueve feeds seleccionados

### Desde conversación con Claudia
```
/intake https://simonwillison.net/2024/...
/intake digest                    # procesar cola ahora
/intake digest feeds              # poll feeds + procesar + briefing
/intake status                    # ver estadísticas de la cola
/intake feeds                     # ver feeds configurados
/intake add-feed https://...      # añadir suscripción
```

## Configuración

### 1. Feeds (`user/config/feeds.json`)

Añade tus suscripciones:

```json
{
  "feeds": [
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "type": "rss", "active": true},
    {"name": "3Blue1Brown", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYO_jab_esuFRV4b17AJtAw", "type": "youtube", "active": true},
    {"name": "Lenny's Newsletter", "url": "https://www.lennysnewsletter.com/feed", "type": "rss", "active": true}
  ],
  "state": {}
}
```

Para canales de YouTube, el feed RSS es:
```
https://www.youtube.com/feeds/videos.xml?channel_id=ID_DEL_CANAL
```
(El ID del canal está en la URL del canal o en "Acerca de" > "Compartir canal")

### 2. Horarios (`user/config/settings.json` → `skill_intake`)

```json
{
  "briefing_cron": "0 13 * * *",
  "feeds_cron": "0 */6 * * *",
  "expire_days": 14
}
```

Los crons se configuran manualmente en crontab. Los valores aquí son de referencia:
```bash
crontab -e
# Añadir:
0 */6 * * * .claude/skills/claudia-intake/intake_cron.sh feeds >> ~/.claude/logs/intake.log 2>&1
0 13 * * * .claude/skills/claudia-intake/intake_cron.sh process >> ~/.claude/logs/intake.log 2>&1
```

### 3. Requisitos

- **Telegram** configurado (token + user ID en `user/credentials/.env`)
- **Email** — solo necesita `EMAIL_TO` en `.env`. Para el envío usa automáticamente el OAuth de Gmail si ya está configurado en `claudia-gmail`. Si no, como fallback añade credenciales SMTP:
  ```
  EMAIL_TO=tu@email.com          # obligatorio

  # Fallback SMTP (solo si no tienes Gmail OAuth):
  # SMTP_HOST=smtp.proveedor.com
  # SMTP_PORT=587
  # SMTP_USER=remitente@ejemplo.com
  # SMTP_PASSWORD=contraseña
  ```
- **claude CLI** accesible desde cron (necesita `CLAUDE_CODE_OAUTH_TOKEN` en `.env`)

## Dónde se guarda todo

| Qué | Dónde |
|-----|-------|
| Cola de items | `user/vault/intake/queue.jsonl` |
| Extracciones wisdom | `user/vault/wisdom/` (mismo sitio que wisdom manual, con `origin: intake`) |
| Config de feeds | `user/config/feeds.json` |
| Config de horarios | `user/config/settings.json` → `skill_intake` |
| Logs del cron | `~/.claude/logs/intake.log` |

## Ejemplo de briefing

### Telegram (índice)
```
Briefing diario — 16 abr 2026

Procesados (2):
• "Why Context Windows Matter" (article)
  Los context windows grandes no sustituyen a RAG — complementan
• "Karpathy on Training" (tweet)
  5 reglas prácticas para fine-tuning eficiente

Nuevo de feeds (3):
1. [3Blue1Brown] "Attention Visualized" 
2. [Simon Willison] "sqlite-vec 0.3"
3. [Stratechery] "Apple Intelligence Review"
Responde "procesa 1,3" para extraer wisdom

Cola: 0 pendientes | 1 archivados
```

### Email
Un email HTML con cada extracción completa: ideas clave, insights, citas notables, conceptos y acciones recomendadas. Se lee como un newsletter personal.

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-intake/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "El briefing de Telegram debe ser muy compacto: solo título y takeaway de cada item"
- "Prioriza siempre los feeds de YouTube sobre los feeds RSS en el briefing"
- "Añade una sección 'Para esta semana' con los 3 items de feeds más interesantes"
- "Escribe el briefing en inglés aunque el contenido sea en español"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **El briefing no llega**: verificar `~/.claude/logs/intake.log`, comprobar tokens en `.env`
- **Email no llega**: verificar `SMTP_HOST`, `SMTP_USER` y `SMTP_PASSWORD` en `.env`. Para Gmail, asegúrate de usar un App Password, no la contraseña normal
- **Feeds no detectan nuevos items**: comprobar que la URL del feed es correcta (`curl -s URL | head`)
- **Claude timeout en procesamiento**: items muy largos (vídeos de >1h). Reducir contenido o procesar individualmente

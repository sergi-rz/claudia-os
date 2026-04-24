---
name: claudia-calendar
description: "Consulta y gestiona Google Calendar (lectura, creación, modificación y borrado de eventos). Usar cuando el usuario pregunte por su agenda, quiera crear/mover citas, o cualquier operación de calendario."
scope: core
user-invocable: true
argument-hint: "[hoy|semana|crear evento|...]"
---

# Calendar — Google Calendar

Acceso a Google Calendar via Google Apps Script desplegado como Web App (lectura + escritura).

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Lectura

```bash
python3 .claude/skills/claudia-calendar/fetch_calendar.py --days 1          # eventos de hoy
python3 .claude/skills/claudia-calendar/fetch_calendar.py --days 7 --raw    # próximos 7 días (JSON)
python3 .claude/skills/claudia-calendar/fetch_calendar.py --calendars        # listar calendarios disponibles
```

## Escritura

```bash
# Crear evento
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action create \
  --calendar "email@gmail.com" --title "Dentista" \
  --start "2026-03-25T10:00" --end "2026-03-25T11:00"

# Evento de día completo
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action create \
  --title "Vacaciones" --start "2026-04-01" --all-day

# Modificar
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action update \
  --event-id "ID" --calendar "email@gmail.com" --title "Nuevo título"

# Borrar
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action delete \
  --event-id "ID" --calendar "email@gmail.com"
```

## Aliases

Fichero compartido: `user/config/settings.json` (key `calendar_aliases`, el mismo que usa Gmail). Mapea identificadores (emails o IDs de calendario) a nombres cortos. Se usan tanto en la salida (mostrar alias en vez del ID) como en `--calendar` (resolver alias a ID).

En Google Calendar, una misma cuenta puede tener varios calendarios:
- **Calendario principal**: su ID es el email de la cuenta (ej: `usuario@gmail.com`)
- **Calendarios creados** (ej: "Familia", "Deporte"): tienen IDs opacos tipo `abc123@group.calendar.google.com`
- **Calendarios compartidos**: su ID es el email de quien lo comparte

```json
{
  "usuario@gmail.com": "Yo",
  "pareja@gmail.com": "Pareja",
  "abc123@group.calendar.google.com": "Familia"
}
```

### Configuración asistida de aliases

Tras completar el setup, ofrece al usuario configurar aliases:

1. Ejecuta `fetch_calendar.py --days 7 --raw` para obtener eventos con sus `calendarId`
2. Extrae los calendarIds únicos de los eventos
3. Muestra al usuario la lista: "He encontrado estos calendarios: [lista con ID y nombre]. ¿Qué alias quieres para cada uno?"
4. Con las respuestas, escribe la key `calendar_aliases` en `user/config/settings.json` (o actualiza si ya existe, respetando entradas previas de Gmail u otras skills)

## Setup (primera vez)

Esta skill conecta con Google Calendar via un Apps Script desplegado como Web App.

1. Ve a https://script.google.com y crea un nuevo proyecto
2. Copia el contenido de `apps-script.js` (incluido en esta skill) al editor
3. Despliega como Web App: Deploy → New deployment → Web app → Execute as "Me" → Anyone with link
4. Copia la URL del deployment
5. Añádela a `user/credentials/.env`:
   ```
   CALENDAR_WEBAPP_URL=https://script.google.com/macros/s/.../exec
   ```

## Apps Script

`apps-script.js` contiene el código desplegado en Google Apps Script. Tras modificarlo, copiar a script.google.com y redesplegar (nueva versión).

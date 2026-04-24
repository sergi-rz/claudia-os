# Claudia Calendar — Google Calendar integrado

Consulta y gestiona tu Google Calendar desde Claudia. Lee eventos, crea citas, modifica horarios y borra entradas, todo desde conversacion o linea de comandos.

## Que hace

Claudia se conecta a Google Calendar a traves de un Google Apps Script desplegado como Web App. Tiene acceso a todos tus calendarios (principal, compartidos, creados) y puede leer eventos futuros, crear nuevos, modificar existentes o borrarlos. Soporta tanto eventos con hora como eventos de dia completo.

## Como usarlo

### Desde conversacion con Claudia

Pide lo que necesites de forma natural:

- "Que tengo hoy en la agenda?"
- "Que eventos tengo esta semana?"
- "Crea una cita con el dentista el martes a las 10"
- "Mueve la reunion de las 16 al jueves"
- "Borra el evento de yoga del viernes"

### Comandos directos

```bash
# Eventos de hoy
python3 .claude/skills/claudia-calendar/fetch_calendar.py --days 1

# Proximos 7 dias (formato legible)
python3 .claude/skills/claudia-calendar/fetch_calendar.py --days 7

# Proximos 7 dias (JSON, para uso programatico)
python3 .claude/skills/claudia-calendar/fetch_calendar.py --days 7 --raw

# Listar calendarios disponibles
python3 .claude/skills/claudia-calendar/fetch_calendar.py --calendars

# Crear evento con hora
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action create \
  --calendar "email@gmail.com" --title "Dentista" \
  --start "2026-03-25T10:00" --end "2026-03-25T11:00"

# Crear evento de dia completo
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action create \
  --title "Vacaciones" --start "2026-04-01" --all-day

# Modificar un evento
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action update \
  --event-id "ID" --calendar "email@gmail.com" --title "Nuevo titulo"

# Borrar un evento
python3 .claude/skills/claudia-calendar/fetch_calendar.py --action delete \
  --event-id "ID" --calendar "email@gmail.com"
```

## Configuracion

### Paso 1 — Desplegar el Apps Script

1. Ve a https://script.google.com y crea un nuevo proyecto
2. Copia el contenido de `apps-script.js` (incluido en el directorio de esta skill) al editor
3. Despliega como Web App: Deploy > New deployment > Web app
   - Execute as: "Me"
   - Who has access: "Anyone with the link"
4. Copia la URL del deployment

### Paso 2 — Configurar la URL

Añade la URL a `user/credentials/.env`:

```
CALENDAR_WEBAPP_URL=https://script.google.com/macros/s/.../exec
```

### Nota sobre actualizaciones

Si modificas `apps-script.js`, tienes que copiar los cambios al editor de script.google.com y redesplegar con una nueva version para que surtan efecto.

## Aliases de calendarios

Calendar comparte la key `calendar_aliases` en `user/config/settings.json` con Gmail. Mapea IDs de calendario a nombres legibles. Los aliases funcionan en dos direcciones: al mostrar eventos se usa el nombre corto, y al crear/modificar puedes usar el alias en `--calendar`.

```json
{
  "usuario@gmail.com": "Yo",
  "pareja@gmail.com": "Pareja",
  "abc123@group.calendar.google.com": "Familia"
}
```

Los IDs de calendario en Google Calendar pueden ser:
- **Calendario principal**: el email de la cuenta (ej: `usuario@gmail.com`)
- **Calendarios creados** (Familia, Deporte...): IDs opacos tipo `abc123@group.calendar.google.com`
- **Calendarios compartidos**: el email de quien lo comparte

Tras el setup, Claudia ofrece configurar aliases revisando los calendarios que aparecen en tus eventos.

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| URL del Apps Script | `user/credentials/.env` (variable `CALENDAR_WEBAPP_URL`) |
| Codigo del Apps Script | `.claude/skills/claudia-calendar/apps-script.js` |
| Aliases compartidos | `user/config/settings.json` → `calendar_aliases` |

## Skills relacionadas

- **telegram-bot** — el briefing diario incluye la agenda del calendario; el comando `/agenda` tambien lo consulta
- **claudia-gmail** — comparte los aliases en `settings.json`
- **claudia-intake** — el briefing del intake pipeline puede incluir eventos del dia

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-calendar/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Muestra los eventos en formato compacto de una línea, sin descripción"
- "Al crear un evento, sugiere siempre una duración de 30 minutos por defecto"
- "Muestra solo los calendarios 'Personal' y 'Trabajo' al listar eventos"
- "Añade automáticamente un recordatorio de 15 minutos al crear cualquier evento"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **Error al conectar**: verifica que `CALENDAR_WEBAPP_URL` esta en `user/credentials/.env` y que la URL es correcta
- **No aparecen todos los calendarios**: el Apps Script accede a los calendarios visibles en la cuenta de Google con la que se desplego. Asegurate de que los calendarios compartidos estan aceptados
- **Cambios en apps-script.js no surten efecto**: hay que copiar el codigo al editor de script.google.com y redesplegar como nueva version
- **Aliases no resuelven**: comprueba que `calendar_aliases` en `user/config/settings.json` tiene formato valido y que el ID del calendario coincide exactamente

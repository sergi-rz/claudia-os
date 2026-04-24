# Notes — Tareas, recordatorios e ideas

Captura cualquier cosa que necesites recordar: tareas, recordatorios con hora, ideas sueltas. Funciona desde conversacion directa, Telegram o Siri. Claudia detecta la intencion automaticamente y guarda en el fichero correcto con el formato adecuado.

## Que hace

Dile a Claudia "anota que...", "recuerdame el lunes que..." o "tengo una idea para..." y se encarga del resto. Detecta si es una tarea, un recordatorio con fecha/hora, o una idea, y lo guarda en el fichero correspondiente. Tambien puedes consultar tus pendientes ("que tengo pendiente?") o marcar tareas como completadas.

## Como usarlo

### Capturar tareas

```
anota que tengo que llamar al seguro
que no se me olvide enviar la factura a Pedro
un cliente me ha pedido presupuesto para el rediseno
```

Se guardan en `tasks.md` bajo `## Pendientes`.

### Recordatorios con hora

```
recuerdame manana a las 10 que tengo reunion con Ana
avisame el viernes que cierra el plazo de inscripcion
recuerdame el 20 de abril a las 9 que renuevo el dominio
```

Se guardan en `tasks.md` bajo `## Con recordatorio` con formato:
```
- [ ] 2026-04-20 09:00 [ctx=no] -- Renovar el dominio
```

Si no especificas hora, usa la hora por defecto configurada en `user/config/settings.json` (campo `default_reminder_hour`, fallback: 9:00).

El flag `[ctx=]` se asigna automaticamente:
- `ctx=no` -- Accion externa simple (llamar, comprar, cita). Notificacion directa.
- `ctx=yes` -- Requiere cruzar informacion interna (proyectos, tareas relacionadas). Claudia enriquece la notificacion antes de enviarla.

### Ideas

```
anota esta idea: hacer un dashboard con metricas del newsletter
apunta como idea usar IA para generar thumbnails
```

Se guardan en `ideas.md` con formato `- YYYY-MM-DD -- descripcion`.

### Consultar y completar

```
que tengo pendiente?
muestrame las tareas
marca como hecha la tarea de llamar al seguro
```

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Tareas y recordatorios | `user/workspaces/_me/notes/tasks.md` |
| Ideas | `user/workspaces/_me/notes/ideas.md` |
| Config hora por defecto | `user/config/settings.json` (`default_reminder_hour`) |

## Configuracion

### Tareas e ideas -- sin configuracion

Funcionan siempre, sin setup adicional.

### Recordatorios automaticos -- requieren Telegram

Para que los recordatorios con hora se **disparen automaticamente** (te llegue un mensaje a la hora indicada), necesitas:

1. **Telegram configurado** -- Token del bot y user ID en `user/credentials/.env` (ver skill telegram-bot)
2. **Notificaciones activadas** -- Dos opciones:
   - **Modo local:** ejecutar `bash .claude/skills/telegram-bot/setup-local-reminders.sh`. Funciona mientras el ordenador este encendido.
   - **Modo servidor (VPS):** cron job en un servidor siempre encendido (ver skill telegram-bot).

**Sin esto**, los recordatorios se guardan igualmente en `tasks.md` y puedes consultarlos manualmente, pero no recibiras alertas automaticas.

## Skills relacionadas

- **telegram-bot** -- Necesario para que los recordatorios se disparen automaticamente por Telegram
- **claudia-intake** -- El briefing diario puede incluir un resumen de tus tareas pendientes
- **claudia-calendar** -- Las tareas con fecha pueden cruzarse con tu agenda

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/notes/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "La hora por defecto para recordatorios sin hora especificada debe ser las 8:30, no las 9:00"
- "Las tareas que mencionan 'cliente' deben guardarse con la etiqueta [trabajo] en el texto"
- "Al confirmar una tarea anotada, di el texto completo de lo guardado, no solo 'Anotado'"
- "Las ideas sobre el newsletter guárdalas en user/workspaces/mi-workspace/ideas.md en vez de en _me"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **El recordatorio no llega**: comprueba que Telegram esta configurado (`user/credentials/.env`) y que el modo de notificaciones esta activo (local o VPS)
- **La hora del recordatorio es incorrecta**: verifica tu zona horaria en `user/config/settings.json` (campo `timezone`)
- **No detecta la intencion correcta**: se mas explicito. "Anota como tarea..." o "Apunta como idea..." ayuda a Claudia a clasificar bien

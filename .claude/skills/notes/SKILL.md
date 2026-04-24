---
name: notes
description: Captura tareas, recordatorios e ideas desde cualquier canal (Telegram, Siri, conversación directa). Detecta la intención del usuario y guarda en el fichero correspondiente de user/workspaces/_me/notes/ con el formato adecuado. Úsala cuando el usuario diga "anota", "apunta", "recuérdame", "que no se me olvide", "un cliente me ha pedido", "tengo una idea", o cuando consulte sus tareas/ideas pendientes.
scope: core
---

# Notas, tareas y recordatorios

Los ficheros viven en `user/workspaces/_me/notes/`:

- `tasks.md` — tareas pendientes y recordatorios
- `ideas.md` — ideas sueltas

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Intents — actúa sin pedir confirmación

**Tarea sin fecha** → añade a `## Pendientes` de `tasks.md`
> "anota que tengo que...", "que no se me olvide...", "un cliente me ha pedido..."

**Tarea dentro de un proyecto** → añade bajo la sección `## Proyecto: <nombre>` correspondiente
> "anota en el proyecto X que hay que...", "añade al proyecto X..."
> Si el usuario menciona un proyecto que no existe, créalo (ver sección Proyectos).
> Si no queda claro a qué proyecto pertenece, añádelo a `## Pendientes`.

**Tarea con recordatorio** → añade a `## Con recordatorio` de `tasks.md`
> "recuérdame el [fecha/hora] que...", "avísame el [día]..."
>
> Formato: `- [ ] YYYY-MM-DD HH:MM [ctx=no] — descripción`
> Si no especifica hora, usa la hora por defecto de `user/config/settings.json` (`default_reminder_hour`, fallback 9).
>
> **Flag `[ctx=]`** — analiza la intención al guardar y decide:
> - `ctx=no` → acción externa simple (llamar a alguien, comprar algo, cita) — notificación directa
> - `ctx=yes` → requiere cruzar información interna (proyectos, personas, tareas relacionadas, estado de algo) — Claude enriquece la notificación antes de enviarla

**Idea** → añade a `ideas.md`
> "anota esta idea", "apunta esto como idea"
> Formato: `- YYYY-MM-DD — descripción`

**Consulta** → lee y resume el fichero correspondiente
> "¿qué tengo pendiente?", "muéstrame las tareas"

**Completar** → mueve el item a `## Completadas` en `tasks.md`
> "marca como hecha la tarea de X"

Confirma con un mensaje corto ("Anotado.", "Guardado en ideas.").

## Proyectos

Un proyecto agrupa tareas relacionadas bajo un objetivo. Viven como secciones en `tasks.md`:

```markdown
## Proyecto: Lanzar podcast
objetivo: publicar el primer episodio antes del 15 de mayo
- [ ] elegir plataforma de hosting
- [ ] grabar episodio piloto
- [x] definir formato y duración
```

**Crear proyecto:** cuando el usuario diga "crea un proyecto para...", "quiero organizar las tareas de...", o cuando al capturar una tarea quede claro que pertenece a un grupo que aún no existe. Pide confirmación antes de crear uno nuevo si no es explícito.

**Estructura:** la línea `objetivo:` es opcional pero recomendada — conecta el proyecto con los goals del usuario (`user/context/goals.md`). Las tareas dentro usan el mismo formato `- [ ]` / `- [x]` que el resto.

**Completar proyecto:** cuando todas las tareas de un proyecto estén completadas, pregunta al usuario si quiere cerrarlo. Al cerrar, mueve la sección entera a `## Completadas` con la fecha.

**Consulta:** cuando el usuario pregunte por un proyecto específico ("¿cómo va el proyecto X?"), muestra el estado: tareas hechas vs pendientes, y el objetivo si tiene uno.

## Recordatorios con hora — requisitos

Las tareas y notas funcionan siempre. Pero para que los recordatorios con hora se **disparen automáticamente**, se necesita:

1. **Telegram configurado** — token del bot y user ID en `user/credentials/.env` (ver skill telegram-bot)
2. **Notificaciones activadas** — hay dos opciones:
   - **Modo local (macOS):** ejecutar `bash .claude/skills/telegram-bot/setup-local-reminders.sh`. Funciona mientras el Mac esté encendido, no necesita VPS.
   - **Modo completo (VPS):** cron job en un servidor siempre encendido (ver skill telegram-bot).

**Sin esto**, los recordatorios se guardan igualmente en `tasks.md` y puedes consultarlos manualmente ("¿qué tengo pendiente?"), pero no se envían alertas automáticas.

Si el usuario pide un recordatorio con hora y no tiene notificaciones configuradas, avísale: *"Lo he guardado como tarea con fecha, pero sin notificaciones activadas no recibirás la alerta automática. ¿Quieres que te ayude a configurarlo? Solo necesitas Telegram y un minuto."*

## Auto-archivo de completadas

Las tareas en `## Completadas` con más de 30 días se archivan automáticamente a `user/vault/done/YYYY-MM.md` para mantener `tasks.md` ligero. Esto lo hace el dream cycle nocturno (si está configurado) o manualmente al inicio de sesión si se detectan completadas antiguas.

El archivo en vault mantiene el historial completo — nada se pierde, solo se mueve fuera de la vista activa.

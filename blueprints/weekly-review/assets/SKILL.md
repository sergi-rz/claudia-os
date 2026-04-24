---
name: weekly-review
description: "Genera un fichero de revisión semanal leyendo la actividad de los últimos 7 días: tareas completadas y pendientes, ideas capturadas y aprendizajes episódicos. Usar los viernes o cuando el usuario pida cierre de semana."
user-invocable: true
---

# weekly-review

## Qué hace

Lee la actividad de los últimos 7 días del usuario y genera `user/vault/weekly-reviews/YYYY-WW.md`, donde `WW` es el número de semana ISO.

## Fuentes

<!-- ADAPTAR: lista real de fuentes detectadas en Discovery. Solo las que existen en esta
     instancia. No dejes esta línea sin sustituir. Ejemplo:

- user/workspaces/_me/notes/tasks.md — tareas en `## Completadas` (últimos 7 días) y secciones abiertas.
- user/workspaces/_me/notes/ideas.md — ideas capturadas esta semana.
- user/memory/episodes/AGENT_LEARNINGS.jsonl — aprendizajes con timestamp en la ventana.
- user/context/identity.md — solo como guía de tono.
-->

## Flujo

1. Calcula el rango de fechas: `hoy − 7 días → hoy`. Calcula el número de semana ISO (`date +%V` en bash).
2. Lee cada fuente listada arriba. Si alguna no existe o está vacía en el rango, **sáltala sin fallar** y menciónalo en el output bajo "Fuentes no disponibles esta semana".
3. Sintetiza en cuatro bloques:
   - **Hecho** — qué se completó
   - **Pendiente** — qué queda abierto
   - **Patrones / aprendizajes** — qué se repite, dónde hubo fricción, qué sorprendió
   - **Para la semana que viene** — 3 prioridades concretas, justificadas
4. Escribe a `user/vault/weekly-reviews/YYYY-WW.md`. Si el fichero ya existe (re-ejecución en la misma semana ISO), avisa al usuario y pide confirmación antes de sobreescribir.
5. Muestra un resumen del output por pantalla al usuario (mínimo las 3 prioridades de la semana siguiente).

## Tono

Directa, sin florituras. Respeta el estilo definido en `user/context/identity.md`. Nada de corporativismo ni "¡gran semana!".

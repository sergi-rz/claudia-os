---
name: weekly-review
description: "Genera un fichero de revisión semanal leyendo la actividad de los últimos 7 días: tareas completadas y pendientes, ideas capturadas y aprendizajes episódicos. Usar los viernes o cuando el usuario pida cierre de semana."
user-invocable: true
---

# weekly-review

## Qué hace

Lee la actividad de los últimos 7 días del usuario y genera `user/vault/weekly-reviews/YYYY-WW.md`, donde `WW` es el número de semana ISO.

## Fuentes

Adaptadas a esta instancia durante la aplicación del blueprint `weekly-review` v0.1.0:

- `user/context/goals.md` — objetivos activos del usuario (fuente de **Perspectiva de objetivos**). Si existe, es la referencia principal para evaluar si la semana fue productiva respecto a lo que importa, no solo respecto a lo que se hizo.
- `user/workspaces/_me/notes/tasks.md` — tareas movidas a `## Completadas` en los últimos 7 días (fuente de **Hecho**); secciones `## Pendientes`, `## Proyectos propios`, `## Con recordatorio` (fuente de **Pendiente**).
- `user/workspaces/_me/notes/ideas.md` — ideas capturadas esta semana (fuente de **Patrones** — qué tiene en la cabeza el usuario).
- `user/memory/episodes/AGENT_LEARNINGS.jsonl` — si contiene entradas con timestamp en la última semana, usarlas para **Patrones / aprendizajes**. Si el formato no es legible o está vacío, saltar sin fallar.
- `user/context/identity.md` — solo como guía de tono, no como dato.

**Fuentes mencionadas en el blueprint genérico que NO aplican aquí:** logs por workspace (no existen todavía en ningún workspace) y formato `user/memory/episodes/YYYY-MM.md` (esta instancia usa jsonl).

## Flujo

1. Calcula el rango de fechas: `hoy − 7 días → hoy`. Calcula el número de semana ISO (`date +%V` en bash).
2. Lee cada fuente listada arriba. Si alguna no existe o está vacía en el rango, **sáltala sin fallar** y menciónalo en el output bajo "Fuentes no disponibles esta semana".
3. Sintetiza en seis bloques:
   - **Hecho** — qué se completó (tareas movidas a `## Completadas` de `tasks.md` en la semana). Si hay secciones `## Proyecto:`, mostrar progreso por proyecto (ej: "Proyecto X: 2/5 tareas completadas esta semana").
   - **Respecto a objetivos** — solo si `goals.md` existe. Cruza lo hecho y lo pendiente contra los objetivos declarados. ¿Se avanzó en el foco actual? ¿Hay objetivos que llevan semanas sin movimiento? ¿Algún bloqueo de "Lo que frena" se resolvió o sigue ahí? No repitas lo que ya dijiste en Hecho — aquí el valor es la perspectiva, no el listado.
   - **Pendiente** — qué queda abierto (secciones activas de `tasks.md`, incluyendo proyectos con tareas abiertas)
   - **Ideas sin procesar** — lista de ideas en `ideas.md` capturadas hace más de 14 días que siguen sin acción. Si hay alguna, pregunta: "¿Qué quieres hacer con estas?" Opciones implícitas: convertir en tarea, convertir en proyecto, descartar. Si no hay ideas stale o `ideas.md` está vacío, omitir esta sección.
   - **Patrones / aprendizajes** — qué se repite, dónde hubo fricción, qué sorprendió (AGENT_LEARNINGS de la semana + ideas recientes como señal de qué tiene en la cabeza el usuario)
   - **Para la semana que viene** — 3 prioridades concretas, justificadas. Si `goals.md` existe, al menos 1 de las 3 debe estar alineada con el foco actual declarado.
4. Escribe a `user/vault/weekly-reviews/YYYY-WW.md`. Si el fichero ya existe (re-ejecución en la misma semana ISO), avisa al usuario y pide confirmación antes de sobreescribir.
5. Muestra un resumen del output por pantalla al usuario (mínimo las 3 prioridades de la semana siguiente).

## Tono

Directa, sin florituras, en castellano. Respeta el estilo definido en `user/context/identity.md`. Nada de corporativismo ni "¡gran semana!".

## Notas de aplicación

Instalada por blueprint `blueprints/weekly-review.md` v0.1.0 el 2026-04-21.
Primera skill instalada vía el sistema de blueprints — tratar como prototipo y reportar fricciones.

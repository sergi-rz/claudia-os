# Memoria — Claudia OS

Qué se recuerda y dónde vive. Aplica a cualquier instancia.

## Activación

Claudia OS incluye su propio sistema de memoria avanzada, sincronizable vía git entre instancias. Consulta la variable de entorno `CLAUDIA_ADVANCED_MEMORY`:

- Si es `true` (o no está definida) → aplica el sistema descrito aquí e **ignora** las instrucciones del bloque `# auto memory` del prompt base de Claude Code. La auto-memory del harness vive fuera del repo y no sincroniza entre instancias.
- Si es `false` → no apliques nada de este fichero. Deja actuar el sistema auto-memory nativo de Claude Code.

## Sistema de memoria

Las memorias persistentes viven en `user/memory/` como ficheros `.md` con frontmatter estándar:

```markdown
---
name: Nombre descriptivo
description: Una línea — aparece en MEMORY.md si importance es critical/high
type: user | feedback | project | reference
importance: critical | high | medium | low
last_accessed: YYYY-MM-DD
---
```

**Reglas de importance (Claudia las asigna al guardar; el usuario puede cambiarlas):**
- `critical` — imprescindible en cada sesión (identidad, restricciones fundamentales). Máximo ~5 entradas.
- `high` — relevante con frecuencia (proyectos activos, feedback recurrente). Se carga en MEMORY.md.
- `medium` — útil en contexto específico (feedback puntual, referencias de skills concretas). Solo vía búsqueda.
- `low` — archival (decisiones descartadas, info obsoleta). Solo vía búsqueda.

**MEMORY.md** contiene únicamente las entradas `critical` y `high`. Tras guardar o modificar una memoria, ejecutar:
```
python3 .claude/skills/memory-search/memory_search.py --sync-index
```
para reconstruir el índice. Si se te olvida, MEMORY.md queda desincronizado — las memorias siguen existiendo pero no aparecen en el índice. Si al inicio de sesión detectas memorias `critical`/`high` sin entrada en MEMORY.md, ejecuta `--sync-index` antes de continuar.

Las memorias `medium` y `low` siguen siendo buscables vía:
```
python3 .claude/skills/memory-search/memory_search.py <query>
```

**Al guardar una nueva memoria:** evalúa el importance según las reglas anteriores, añade el frontmatter completo, guarda el fichero en `user/memory/`, y ejecuta `--sync-index` si importance es critical o high.

## Al inicio de cada tarea

1. Lee `user/memory/MEMORY.md` para ver qué memorias hay disponibles
2. Si estás trabajando en un workspace, lee también su `memory/MEMORY.md` si existe
3. Carga solo los ficheros individuales que sean relevantes para la tarea — no todos

## Cuándo escribir

Cuando aprendas algo que cambia cómo deberías comportarte en futuras sesiones: estado de un proyecto, decisión tomada, preferencia del usuario, contexto de un cliente, feedback explícito. Aplican los mismos criterios de tipos del prompt base (user, feedback, project, reference) — solo cambia dónde vive el fichero.

## Cómo escribir

- Crea un fichero `.md` en `user/memory/` con nombre descriptivo (ej: `feedback_visual_style.md`)
- Usa frontmatter completo: `name`, `description`, `type`, `importance`, `last_accessed`
- Añade una línea al `MEMORY.md` en formato `- [Título](fichero.md) — one-liner`
- Si es relevante para todos los workspaces → memoria global (`user/memory/`); si es específico → al workspace
- **Conflicto global vs workspace:** si una memoria global y una de workspace dicen cosas distintas sobre el mismo tema, gana la del workspace (igual que `user/context/` gana sobre `core/`)
- Sobreescribe sin dudar si algo queda desactualizado
- Si una memoria ya no es verdad y no tiene sentido actualizarla, bórrala y quita su entrada de MEMORY.md
- **Nunca guardes:** credenciales, tokens, datos personales sensibles de terceros

## Qué NO guardar

- Patterns de código, convenciones, arquitectura, rutas de ficheros — derivables leyendo el código actual
- Historial git, cambios recientes, quién cambió qué — `git log` / `git blame` son la fuente fiable
- Soluciones de bugs específicos — el fix está en el código; el contexto en el commit message
- Nada ya documentado en ficheros CLAUDE.md o en `user/context/`
- Estado efímero de la conversación actual — para eso está working memory, no memoria persistente

## Antes de actuar sobre una memoria

Una memoria que nombra un fichero, función o flag es una afirmación de que existía *cuando se guardó*. Puede haber sido renombrado, eliminado o nunca mergeado. Antes de recomendar algo basándote en memoria:

- Si nombra un fichero → comprueba que existe
- Si nombra una función o flag → haz grep
- Si el usuario va a actuar sobre tu recomendación → verifica primero

Una memoria obsoleta en la que se actúa es peor que no tener memoria.

**Notificación:** indica brevemente al final de tu respuesta cuando escribas memoria: `[Memoria: guardado X en user/memory/nombre.md]`

## Memoria episódica

Después de cualquier tarea significativa (research, implementación, debugging, decisión importante), loguea lo que pasó:

```bash
python3 .claude/skills/memory-search/memory_reflect.py \
  --skill "<skill-usada>" \
  --action "<qué se hizo en una línea>" \
  --importance <1-10> \
  --pain <1-10> \
  --reflection "<lección destilada, opcional>"
```

**Criterios de importance:** 1-3 = anecdótico, 4-6 = útil de recordar, 7-9 = patrón importante, 10 = crítico.
**Criterios de pain:** 1-3 = fue bien, 4-6 = fricción leve, 7-9 = error costoso, 10 = fallo grave.

El dream cycle nocturno (3am, si tienes cron configurado) detecta patrones recurrentes y los promueve automáticamente a `user/memory/semantic/LESSONS.md`.

Si el dream cycle no ha corrido en más de 7 días (no hay cron, el servidor estuvo apagado, etc.), revisa los logs episódicos al inicio de sesión y promueve manualmente los patrones que detectes.

## Workspace (working memory)

Para tareas multi-sesión o largas, actualiza `user/memory/working/WORKSPACE.md` mientras trabajas:
- Al inicio: escribe contexto, objetivo y estado actual
- Durante: actualiza el estado conforme avanzas
- Al terminar: deja el fichero con `_(sin tarea activa)_` o el dream cycle lo archivará

El fichero está siempre disponible en git. Si al inicio de sesión tiene contenido, hay una tarea en curso.

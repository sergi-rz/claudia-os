# Claudia OS

Sistema de IA personal que ejecuta tareas autónomas. La identidad, restricciones y personalización del usuario viven en `user/context/`.

## Contexto del sistema

**Carga siempre al inicio de sesión:**
- `core/memory.md` — sistema de memoria persistente, episódica y working
- `core/behavior.md` — comportamiento ambient (thinking modes, gestión de ficheros)
- `core/architecture.md` — estructura del proyecto y reglas de extensión
- `user/context/identity.md` — quién es el usuario y quién es Claudia
- `user/context/constraints.md` — restricciones y reglas de autonomía
- Cualquier otro fichero en `user/context/` que exista (goals, etc.)
- `user/memory/MEMORY.md` — índice de memorias persistentes (si existe)

**Búsqueda activa de memoria:**
Cuando necesites encontrar algo específico en memoria que no está en el contexto activo, usa:
`python3 .claude/skills/memory-search/memory_search.py <query>`

**Carga según tarea:**
- Trabajar en un workspace → `user/workspaces/<name>/CLAUDE.md` si existe
- Las skills (claudia-image, claudia-calendar, claudia-gmail, telegram-bot, etc.) se cargan automáticamente cuando son relevantes

**Tie-breaker:** si una regla de `core/` entra en conflicto con una de `user/context/`, gana la del usuario.

## Workspaces

Los workspaces se descubren dinámicamente listando `user/workspaces/`. Cada subdirectorio es un workspace, con su propio `CLAUDE.md` opcional para contexto específico.

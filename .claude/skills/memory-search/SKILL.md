---
name: memory-search
description: Busca en las memorias persistentes del usuario usando SQLite FTS5 (o grep como fallback). Usar cuando Claude necesite encontrar una memoria específica que no está cargada en el contexto activo, o cuando el usuario pregunte por algo que podría estar en memoria.
scope: core
---

# Memory Search

Búsqueda activa sobre `user/memory/` con SQLite FTS5. Los ficheros `.md` son siempre el source of truth; el índice SQLite es un derivado reconstruible automáticamente.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Cuándo usar esta skill

- El usuario pregunta por algo que podría estar en memoria pero no aparece en contexto
- MEMORY.md tiene muchas entradas y hay riesgo de que memorias relevantes no se carguen
- El usuario quiere buscar explícitamente: "¿recuerdas algo sobre X?"

## Modos de operación (auto-detectados, sin configuración)

| Modo | Condición | Comportamiento |
|------|-----------|----------------|
| **Pleno** | Python + SQLite FTS5 | Búsqueda BM25 con ranking por relevancia |
| **Básico** | Python sin FTS5 (edge case) | Búsqueda grep sobre los `.md` |

FTS5 está disponible en prácticamente todas las instalaciones modernas de Python.
Claude Code ya requiere Python, por lo que no hay dependencias adicionales.

## Uso

```bash
# Buscar
python3 .claude/skills/memory-search/memory_search.py <query>

# Ver estado del índice
python3 .claude/skills/memory-search/memory_search.py --status

# Reconstruir índice manualmente
python3 .claude/skills/memory-search/memory_search.py --rebuild
```

## Sin setup

No requiere instalación adicional. `sqlite3` es parte de la stdlib de Python.

El índice vive en `user/memory/.index/memory.db` (gitignored, no se sincroniza).
Si se borra o corrompe, se reconstruye automáticamente en la siguiente búsqueda.
Si algún `.md` es más reciente que el índice, se reconstruye automáticamente.

## Estructura de memoria compatible

Los ficheros `.md` en `user/memory/` aceptan frontmatter opcional:

```markdown
---
type: user | feedback | project | reference
importance: critical | high | medium | low
created: YYYY-MM-DD
last_accessed: YYYY-MM-DD
---
```

Sin frontmatter también funciona — el índice incluye todo el contenido del fichero.

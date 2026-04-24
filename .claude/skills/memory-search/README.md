# Memory Search — Busqueda en memorias persistentes

Busca en todas las memorias de Claudia OS usando SQLite FTS5 con ranking por relevancia. Si FTS5 no esta disponible, cae a grep automaticamente. Forma parte del sistema de memoria junto con el log episodico y el dream cycle.

## Que hace

Las memorias de Claudia viven en ficheros `.md` dentro de `user/memory/`. El indice MEMORY.md solo carga las memorias mas importantes al inicio de sesion. Memory Search permite buscar en **todas** las memorias, incluidas las de baja prioridad que no aparecen en el contexto activo.

Ademas del buscador, esta skill incluye dos componentes adicionales:

- **Memory Reflect** -- Registra aprendizajes del agente (exitos, errores, lecciones) en un log episodico (`AGENT_LEARNINGS.jsonl`). Se llama automaticamente despues de acciones significativas.
- **Dream Cycle** -- Proceso nocturno (cron a las 3am) que comprime la memoria episodica: detecta patrones recurrentes, promueve lecciones importantes a `semantic/LESSONS.md`, y archiva entradas antiguas de baja relevancia.

## Como usarlo

### Buscar memorias

```bash
python3 .claude/skills/memory-search/memory_search.py "nombre del proyecto"
python3 .claude/skills/memory-search/memory_search.py "preferencias de diseno"
```

Devuelve resultados rankeados por relevancia (BM25) con snippets que muestran el contexto de cada match.

### Ver estado del indice

```bash
python3 .claude/skills/memory-search/memory_search.py --status
```

Muestra el modo activo (FTS5 o grep), numero de memorias indexadas, y tamano del indice.

### Reconstruir indice manualmente

```bash
python3 .claude/skills/memory-search/memory_search.py --rebuild
```

Normalmente no necesitas esto -- el indice se reconstruye automaticamente cuando detecta que algun fichero `.md` ha cambiado.

### Sincronizar MEMORY.md

```bash
python3 .claude/skills/memory-search/memory_search.py --sync-index
```

Regenera `MEMORY.md` a partir del frontmatter de los ficheros. Solo incluye memorias con `importance: critical` o `importance: high`.

### Registrar un aprendizaje (Memory Reflect)

```bash
python3 .claude/skills/memory-search/memory_reflect.py \
  --skill "claudia-research" \
  --action "Web search timeout con queries muy largas" \
  --importance 7 \
  --pain 5 \
  --reflection "Partir queries largas en sub-queries de 3-4 palabras"
```

### Ejecutar Dream Cycle manualmente

```bash
python3 .claude/skills/memory-search/dream_cycle.py
```

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Memorias (source of truth) | `user/memory/*.md` |
| Indice MEMORY.md (cargado al inicio) | `user/memory/MEMORY.md` |
| Indice SQLite (derivado, reconstruible) | `user/memory/.index/memory.db` |
| Log episodico | `user/memory/episodes/AGENT_LEARNINGS.jsonl` |
| Lecciones promovidas | `user/memory/semantic/LESSONS.md` |
| Snapshots archivados | `user/memory/episodes/snapshots/` |
| Workspace activo | `user/memory/working/WORKSPACE.md` |

## Configuracion

### Sin setup

No requiere instalacion adicional. `sqlite3` es parte de la stdlib de Python, y FTS5 esta disponible en practicamente todas las instalaciones modernas.

El indice SQLite es un derivado -- si se borra o corrompe, se reconstruye automaticamente en la siguiente busqueda. Esta en `.gitignore` y no se sincroniza entre dispositivos.

### Dream Cycle (cron)

Para activar la compresion nocturna automatica, anade a crontab:

```bash
crontab -e
# Anadir:
0 3 * * * cd /ruta/a/claudia-os && python3 .claude/skills/memory-search/dream_cycle.py >> ~/.claude/logs/dream_cycle.log 2>&1
```

### Frontmatter opcional en memorias

Los ficheros `.md` en `user/memory/` aceptan frontmatter para mejorar el indexado:

```markdown
---
type: user | feedback | project | reference
importance: critical | high | medium | low
created: 2026-04-15
last_accessed: 2026-04-16
---
```

Sin frontmatter tambien funciona -- el indice incluye todo el contenido del fichero.

## Como funciona el Dream Cycle

1. Carga `AGENT_LEARNINGS.jsonl`
2. Detecta patrones recurrentes (misma skill + accion similar, 2+ veces)
3. Calcula "salience" de cada patron: `recency * (pain/10) * (importance/10) * min(recurrence, 3)`
4. Promueve patrones con salience >= 7.0 a `semantic/LESSONS.md`
5. Archiva entradas con >90 dias y salience < 2.0 a `episodes/snapshots/`
6. Resetea `WORKSPACE.md` si tenia contenido activo
7. Hace git commit con el resultado

## Skills relacionadas

- **Todas las skills** -- Claudia usa memory-search internamente cuando necesita encontrar informacion que no esta en el contexto activo
- **claudia-onboarding** -- Genera los primeros ficheros de memoria
- **telegram-bot / claudia-intake** -- Pueden registrar aprendizajes via Memory Reflect

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/memory-search/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Las búsquedas deben devolver como máximo 5 resultados, no el default"
- "El umbral de salience del Dream Cycle para promover lecciones debe ser 5.0 en vez de 7.0"
- "El Dream Cycle debe ejecutarse a las 2am en vez de a las 3am"
- "Al registrar un aprendizaje con memory_reflect, añade siempre el campo 'context' con la fecha del día"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **"Sin resultados" cuando deberia encontrar algo**: prueba con menos palabras o terminos mas genericos. FTS5 usa tokenizacion porter, asi que busca raices de palabras
- **El indice no se actualiza**: ejecuta `--rebuild` manualmente. Normalmente se reconstruye solo cuando detecta ficheros `.md` mas recientes que el indice
- **Dream Cycle no hace commit**: verifica que git esta configurado y que hay cambios reales que commitear

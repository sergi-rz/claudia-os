# Attribution

Claudia OS incorpora ideas y código adaptado de los siguientes proyectos open-source.

---

## agentic-stack

**Repositorio:** https://github.com/codejunkie99/agentic-stack  
**Autor:** Avid (@Av1dlive)  
**Licencia:** MIT License, Copyright (c) 2026 Avid

**Qué se tomó prestado:**
- Arquitectura de memoria episódica con log JSONL (`AGENT_LEARNINGS.jsonl`)
- Dream cycle: compresión nocturna de episódico → semántico (`dream_cycle.py`)
- Salience scoring: `recency × pain × importance × recurrence` (`salience.py`)
- Concepto de WORKSPACE.md como working memory por tarea
- Filosofía "destinos y vallas" para escribir skills (documentada en DESIGN.md)

**Ficheros afectados:**
- `.claude/skills/memory-search/dream_cycle.py`
- `.claude/skills/memory-search/salience.py`
- `.claude/skills/memory-search/memory_reflect.py`

Los ficheros incluyen el aviso de copyright de Avid en su cabecera.

---

## Personal AI Infrastructure (PAI)

**Repositorio:** https://github.com/danielmiessler/Personal_AI_Infrastructure  
**Autor:** Daniel Miessler  
**Licencia:** MIT License

**Qué se tomó prestado (inspiración de patrones, no código directo):**
- Research multi-nivel (quick/standard/deep) con vaults persistentes → skill `claudia-research`
- Content analysis / wisdom extraction → skill `claudia-wisdom`
- Estructura de vaults por dominio (`user/vault/claudia-research/`, `user/vault/claudia-wisdom/`)
- Skills como directorios autocontenidos con `SKILL.md` propio
- Concepto de niveles de profundidad progresivos según necesidad
- Thinking Modes (Council, RedTeam, FirstPrinciples) → skill `claudia-thinking`

---

## pensamiento-critico

**Repositorio:** https://github.com/omixam/pensamiento-critico  
**Autor:** Máximo Gavete (@omixam)  
**Licencia:** MIT License

**Qué se tomó prestado:**
- Skill completa de análisis crítico de textos argumentativos usando el framework de Richard Paul y Linda Elder (8 elementos del pensamiento + 9 estándares intelectuales universales)
- Catálogo curado de falacias lógicas graves (15 tipos en 5 categorías)
- Catálogo de sesgos cognitivos frecuentes en textos argumentativos
- Tests de validación: sustitución de términos cargados y simetría ideológica
- Bibliografía sobre falacias y argumentación informal
- Reportes de ejemplo calibrados en tono y profundidad

**Adaptaciones para Claudia OS:**
- Renombrada a `claudia-critique` para coherencia con el ecosistema
- Obtención de contenido vía `claudia-scrape` y `claudia-yt-transcript` en lugar de WebFetch directo
- Modo auto-critique para revisar borradores propios antes de publicar
- Tabla de diferenciación con otras skills (wisdom, research, thinking)
- Fichero `user/behavior.md` para personalización por usuario

**Ficheros afectados:**
- `.claude/skills/claudia-critique/SKILL.md` (adaptado)
- `.claude/skills/claudia-critique/references/elementos-estandares.md` (verbatim)
- `.claude/skills/claudia-critique/references/falacias-graves.md` (verbatim)
- `.claude/skills/claudia-critique/references/sesgos-cognitivos.md` (verbatim)
- `.claude/skills/claudia-critique/references/ejemplos-reportes.md` (verbatim)
- `.claude/skills/claudia-critique/doc/falacias-bibliografia.md` (verbatim)


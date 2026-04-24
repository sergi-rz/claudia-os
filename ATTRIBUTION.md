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


---
name: vault-search
description: "Busca en el vault de conocimiento (wisdom, research) usando SQLite FTS5 + metadatos estructurados. Queries por texto, autor, topic, quality, stance, etc."
scope: core
user-invocable: false
---

# Vault Search — Índice SQLite del vault de conocimiento

Indexa `user/vault/` (wisdom, research, weekly-reviews) con SQLite FTS5 para búsqueda full-text y tablas relacionales para queries estructuradas por metadatos del frontmatter.

## Uso como librería (desde otras skills)

```bash
# Buscar contexto previo antes de crear wisdom/research
python3 .claude/skills/vault-search/vault_search.py --context "tema" --max-tokens 1500

# Reindexar un fichero recién creado
python3 .claude/skills/vault-search/vault_search.py --reindex-file "wisdom/2026-05-01_slug.md"

# Regenerar INDEX.md automáticamente
python3 .claude/skills/vault-search/vault_search.py --generate-index
```

## Uso CLI directo

```bash
# Full-text search
python3 vault_search.py "agentes autónomos memoria"

# Filtros estructurados
python3 vault_search.py --author "Miessler"
python3 vault_search.py --topic agentes-ia --quality alta
python3 vault_search.py --type video --depth deep
python3 vault_search.py --stance esceptico --topic scaling
python3 vault_search.py --since 2026-04-01

# Stats y listados
python3 vault_search.py --stats
python3 vault_search.py --list-topics
python3 vault_search.py --list-authors

# Gestión del índice
python3 vault_search.py --rebuild
python3 vault_search.py --status
```

## Arquitectura

- **Source of truth:** ficheros .md con frontmatter YAML en `user/vault/`
- **Índice derivado:** `user/vault/.index/vault.db` (SQLite, gitignored, regenerable)
- **Auto-rebuild:** detecta cambios por mtime, reconstruye transparentemente
- **Fallback:** grep si FTS5 no disponible

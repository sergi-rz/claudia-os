# Vault — Base de conocimiento de Claudia OS

El vault es el repositorio centralizado de conocimiento extraído y generado. No es un workspace de trabajo — es una biblioteca de referencia que crece con el tiempo y permite cruzar fuentes, contrastar posturas y detectar patrones entre autores y temas.

## Estructura

```
user/vault/
  wisdom/    → extracciones de piezas concretas (artículos, newsletters, vídeos, podcasts)
  research/  → investigaciones multi-fuente sintetizadas por Claudia
```

La búsqueda y navegación se hace via `vault-search` (SQLite FTS5). No hay INDEX.md global — el índice es la base de datos.

## Búsqueda (vault-search)

El vault tiene un índice SQLite FTS5 en `user/vault/.index/vault.db` (gitignored, regenerable). Permite búsqueda full-text y queries estructuradas por metadatos del frontmatter.

```bash
# Buscar por texto
python3 .claude/skills/vault-search/vault_search.py "agentes autónomos"

# Buscar por metadatos
python3 .claude/skills/vault-search/vault_search.py --topic agentes-ia --quality alta
python3 .claude/skills/vault-search/vault_search.py --author "Miessler"

# Context-pack (formato compacto para inyectar en prompts)
python3 .claude/skills/vault-search/vault_search.py --context "tema" --max-tokens 2000

# Reindexar un fichero nuevo
python3 .claude/skills/vault-search/vault_search.py --reindex-file "wisdom/filename.md"

# Regenerar INDEX.md desde la base de datos
python3 .claude/skills/vault-search/vault_search.py --generate-index
```

El índice se reconstruye automáticamente si detecta ficheros más nuevos que el índice.

## user/vault/wisdom/

Cada fichero es la extracción de **una pieza concreta de contenido**. El objetivo no es resumir sino capturar lo que hace pensar: ideas, insights, citas, conceptos, y cómo conecta con lo que ya sabemos.

### Frontmatter obligatorio

```yaml
---
source: "URL o referencia"
type: video | article | podcast | newsletter | text
author: "nombre del autor"
title: "título del contenido"
date: YYYY-MM-DD            # fecha de publicación del contenido original
topics: [tema1, tema2]      # usar topics reutilizables (ver taxonomía abajo)
quality: alta | media | baja
stance: esceptico | bullish | neutral | mixto  # postura del autor respecto al tema principal
depth: normal | deep                           # profundidad de la extracción
origin: user | research/nombre-del-fichero.md  # quién solicitó esta extracción
---
```

### Campo `stance`

Indica la postura del autor respecto al **tema principal** del contenido. Permite contrastar autores con posturas opuestas sobre el mismo topic.

- `esceptico` — crítico o cauteloso respecto al tema (ej: LeCun sobre LLMs, Marcus sobre scaling)
- `bullish` — entusiasta o favorable (ej: Altman sobre AGI)
- `neutral` — analítico sin postura clara
- `mixto` — matizado, defiende y critica a la vez

### Campo `depth`

Indica la profundidad de la extracción:

- `normal` — síntesis estándar (5-15 ideas, 3-7 insights, 3-10 citas)
- `deep` — extracción profunda con secciones adicionales (resumen narrativo, argumentos y evidencia) y rangos ampliados (15-30 ideas, 7-15 insights, 10-20 citas)

Se auto-selecciona en función de la longitud y densidad del contenido, o se fuerza con el argumento `deep`/`normal` al invocar `/claudia-wisdom`. Intake siempre usa `normal`.

### Campo `origin`

- `user` — extracción solicitada directamente por el usuario
- `research/nombre.md` — generada automáticamente durante un research como fuente clave

### Taxonomía de topics

Usar siempre términos de esta lista cuando apliquen. Añadir nuevos solo si no hay ninguno que encaje:

```
ia-razonamiento       llm-limites           ia-neurosimbolica
agentes-ia            scaling               agi
marca-personal        creacion-contenido    newsletter
youtube               productividad         finanzas
negocio               freelancing           proyectos-propios
filosofia             psicologia            tecnologia
seo                   marketing             paternidad
startups              personal-ai
```

## user/vault/research/

Cada fichero (o carpeta para deep research) es una investigación sintetizada por Claudia. Las investigaciones quick no se guardan — solo standard y deep.

La investigación puede referenciar ficheros de `user/vault/wisdom/` como fuentes cuando corresponda.

### Frontmatter obligatorio

```yaml
---
title: "Título de la investigación o sección"
date: YYYY-MM-DD
level: standard | deep
topics: [tema1, tema2]       # misma taxonomía que wisdom
role: summary | landscape | entities | entity-profile | analysis  # solo en deep research
parent: "nombre-carpeta"     # solo en ficheros dentro de una carpeta de deep research
---
```

- `level` — standard (fichero único) o deep (carpeta con múltiples ficheros)
- `role` — función del fichero dentro de un deep research:
  - `summary` — síntesis final con recomendaciones
  - `landscape` — panorama general del dominio
  - `entities` — catálogo de entidades con scoring
  - `entity-profile` — perfil detallado de una entidad
  - `analysis` — análisis temático transversal
- `parent` — nombre de la carpeta padre (para vincular ficheros de un deep research)

No llevan `quality`, `stance`, `author` ni `source` porque son producción propia de Claudia, no extracciones de contenido externo.

## Cómo se conectan wisdom y research

- Un research puede delegar wisdom-extraction en 1-2 fuentes especialmente valiosas que encuentre. Esos ficheros van a `user/vault/wisdom/` con `origin: research/nombre.md`.
- Un research puede referenciar wisdom files existentes como contexto de partida.
- La búsqueda transversal se hace con vault-search. Los INDEX.md locales dentro de carpetas de deep research son navegación interna de ese research concreto.

## Reglas

- Los ficheros de wisdom reflejan el contenido original, no la opinión de Claudia. Las conexiones y valoraciones van en secciones explícitas.
- No duplicar extracciones: antes de crear un wisdom nuevo, buscar en vault-search para verificar que no existe ya.
- Los topics deben ser reutilizables entre extracciones. Si en 3 ficheros aparece el mismo tema pero con nombres distintos, unificarlos.

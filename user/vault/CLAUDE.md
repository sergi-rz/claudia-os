# Vault — Base de conocimiento de Claudia OS

El vault es el repositorio centralizado de conocimiento extraído y generado. No es un workspace de trabajo — es una biblioteca de referencia que crece con el tiempo y permite cruzar fuentes, contrastar posturas y detectar patrones entre autores y temas.

## Estructura

```
user/vault/
  wisdom/    → extracciones de piezas concretas (artículos, newsletters, vídeos, podcasts)
  research/  → investigaciones multi-fuente sintetizadas por Claudia
```

Ambos directorios tienen su propio `INDEX.md` como punto de entrada.

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
startups
```

## user/vault/research/

Cada fichero (o carpeta para deep research) es una investigación sintetizada por Claudia. Las investigaciones quick no se guardan — solo standard y deep.

La investigación puede referenciar ficheros de `user/vault/wisdom/` como fuentes cuando corresponda.

## Cómo se conectan wisdom y research

- Un research puede delegar wisdom-extraction en 1-2 fuentes especialmente valiosas que encuentre. Esos ficheros van a `user/vault/wisdom/` con `origin: research/nombre.md`.
- Un research puede referenciar wisdom files existentes como contexto de partida.
- El INDEX.md de cada directorio es el punto de entrada para navegar por tema.

## Reglas

- Los ficheros de wisdom reflejan el contenido original, no la opinión de Claudia. Las conexiones y valoraciones van en secciones explícitas.
- No duplicar extracciones: antes de crear un wisdom nuevo, verificar que no existe ya en `user/vault/wisdom/INDEX.md`.
- Los topics deben ser reutilizables entre extracciones. Si en 3 ficheros aparece el mismo tema pero con nombres distintos, unificarlos.

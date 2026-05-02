# Claudia Wisdom — Extraccion de conocimiento

Extrae lo valioso de cualquier contenido (video de YouTube, articulo, tweet, podcast, newsletter) y lo guarda como conocimiento estructurado en el vault.

## Que hace

Encuentras un video interesante, un hilo en X con insights, un articulo denso que no quieres perder. Le pasas la URL a Claudia y ella extrae el conocimiento destilado: ideas clave, insights refinados, citas textuales, conceptos y acciones concretas. Todo queda guardado en el vault con frontmatter, clasificado por temas, y conectado con wisdom previo.

No es un resumen — es una extraccion de lo que merece recordarse. Claudia distingue entre "de que va" y "que aprendi y por que importa".

## Como usarlo

### Desde conversacion con Claudia

```
/claudia-wisdom https://www.youtube.com/watch?v=dQw4w9WgXcQ
/claudia-wisdom https://x.com/karpathy/status/1234567890
/claudia-wisdom https://www.paulgraham.com/writes.html
/claudia-wisdom https://newsletter.example.com/post/the-future-of-x
```

Tambien acepta texto directo (sin URL) si pegas el contenido en la conversacion.

### Profundidad de extraccion

Puedes forzar el modo de profundidad añadiendo `deep` o `normal` al final:

```
/claudia-wisdom https://www.youtube.com/watch?v=dQw4w9WgXcQ deep
/claudia-wisdom https://www.paulgraham.com/writes.html normal
```

Si no especificas modo, Claudia evalua el contenido y decide automaticamente:
- **deep**: contenido largo (>3000 palabras o video >30 min), denso en ideas o con multiples argumentos entrelazados
- **normal**: contenido corto, monotema o de baja densidad

El modo deep genera dos secciones adicionales (**Resumen narrativo** y **Argumentos y evidencia**) y amplia los rangos de ideas, insights y citas para capturar matices que la sintesis normal descarta.

### Desde intake

Si envias una URL al pipeline de intake (Telegram o `/intake`), el procesamiento batch usa wisdom automaticamente para cada item. Intake siempre usa el modo normal.

## Formatos soportados

| Tipo | Ejemplo | Metodo de extraccion |
|------|---------|---------------------|
| Video YouTube | `youtube.com/watch?v=...` | Extrae subtitulos via `claudia-yt-transcript` |
| Tweet/Thread | `x.com/.../status/...` | FxTwitter API via `claudia-scrape` |
| Articulo web | Cualquier URL de blog/medio | WebFetch via `claudia-scrape` |
| Newsletter | Substack, Revue, etc. | WebFetch via `claudia-scrape` |
| Podcast | Spotify, Apple, iVoox | Transcripcion si disponible; si no, avisa |
| Texto directo | Texto pegado sin URL | Lo usa tal cual |
| PDF/documento | Ruta local a fichero | Lee el fichero directamente |

## Que extrae

Cada pieza de wisdom incluye:

- **Ideas clave** (5-15, o 15-30 en deep) — Lo mas interesante, sorprendente o contraintuitivo
- **Insights refinados** (3-7, o 7-15 en deep) — Ideas elevadas a principio: mas abstractos, mas aplicables
- **Citas textuales** (3-10, o 10-20 en deep) — Frases exactas del autor que merezca la pena recordar
- **Conceptos clave** — Frameworks, modelos mentales, terminologia con definicion breve
- **Acciones recomendadas** (0-5) — Cosas concretas que podrias hacer. Solo si aplica
- **Meta** — Takeaway en 1 frase, para quien es util, valoracion honesta de calidad

En modo deep, ademas:
- **Resumen narrativo** (500-800 palabras) — El arco argumental completo, reconstruido para que el lector pueda seguir la logica sin volver al original
- **Argumentos y evidencia** — Datos, estudios y ejemplos concretos que sostienen los puntos principales

## Conexion con conocimiento previo

Despues de extraer, Claudia busca en el vault existente:
- Wisdom previo relacionado por tema o conceptos
- Research previo sobre temas afines
- Patrones emergentes (si el mismo tema aparece en 3+ extracciones)

Si encuentra conexiones reales, las incluye. Si no, no inventa.

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Ficheros de wisdom | `user/vault/wisdom/{YYYY-MM-DD}_{slug}.md` |
| Busqueda e indice | SQLite FTS5 via `vault-search` (auto-generado en `user/vault/.index/`) |
| Taxonomia de topics | `user/vault/CLAUDE.md` |

### Naming de ficheros

`{YYYY-MM-DD}_{slug-descriptivo}.md`

Ejemplo: `2026-04-11_gary-marcus-biggest-advance-ai-llm.md`

### Formato del fichero

Cada fichero incluye frontmatter YAML con metadatos:

```yaml
---
source: "URL"
type: video | article | podcast | newsletter | text | tweet | thread
author: "nombre"
title: "titulo"
date: YYYY-MM-DD
topics: [tema1, tema2]
quality: alta | media | baja
stance: esceptico | bullish | neutral | mixto
depth: normal | deep
origin: user | research/nombre-del-fichero.md
---
```

Seguido del contenido estructurado (ideas, insights, citas, conceptos, acciones, conexiones).

### Indexación

Cada nuevo wisdom se indexa automáticamente en la base de datos SQLite via `vault-search`. No hay INDEX.md global — la búsqueda y navegación se hace con queries a vault-search.

## Requisitos

- Acceso a internet (para extraer contenido de URLs)
- Skill `claudia-scrape` disponible (para tweets, articulos web)
- Skill `claudia-yt-transcript` disponible (para videos de YouTube)
- Taxonomia de topics en `user/vault/CLAUDE.md` (para clasificacion consistente)

## Skills relacionadas

- **claudia-scrape** — Wisdom la usa para extraer contenido de tweets, threads y articulos web
- **claudia-yt-transcript** — Wisdom la usa para obtener subtitulos de videos de YouTube
- **claudia-research** — Research invoca wisdom sobre fuentes valiosas encontradas durante investigacion (con `origin: research/...`)
- **claudia-intake** — El pipeline de intake usa wisdom para procesar cada item de la cola

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-wisdom/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Extrae siempre entre 10 y 15 ideas clave, nunca menos de 10"
- "Añade una sección '## Para mi newsletter' con 2-3 angles que podría usar"
- "El takeaway escríbelo en inglés aunque el contenido sea en español"
- "No guardes wisdom de calidad baja, avísame y pregunta si quiero continuar"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **No puede extraer contenido (paywall, contenido dinamico)**: Claudia te avisa y sugiere pegar el texto manualmente
- **Citas no son exactas**: si la fuente son subtitulos automaticos de YouTube, Claudia indica que las citas son aproximadas
- **Duplicado detectado**: antes de crear un fichero, se consulta vault-search. Si la fuente ya fue extraida, avisa en lugar de duplicar
- **Topic nuevo no aparece en taxonomia**: consultar `user/vault/CLAUDE.md` y anadir el topic si es reutilizable, o usar uno existente
- **Calidad marcada como baja**: es intencionado. Si el contenido no aporta nada nuevo, Claudia lo dice honestamente. Mejor un wisdom marcado como baja calidad que inflar todo

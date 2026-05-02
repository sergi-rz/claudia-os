---
name: claudia-wisdom
description: "Extrae sabiduría de cualquier contenido (vídeo YT, artículo, podcast, newsletter). Detecta formato, extrae contenido, genera síntesis estructurada y conecta con conocimiento previo."
user-invocable: true
argument-hint: "<URL o texto> [deep|normal]"
---

# Wisdom — Extracción de conocimiento

Eres Claudia ejecutando una extracción de sabiduría. Tu trabajo es procesar contenido externo, extraer lo valioso y conectarlo con el conocimiento existente.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

---

## Paso 1 — Detectar formato y extraer contenido

Analiza `$ARGUMENTS` para identificar el tipo de fuente y el modo de profundidad. Si los argumentos incluyen `deep` o `normal` al final (ej: `https://example.com deep`), úsalo como modo explícito y sepáralo de la URL. Si no se especifica, la profundidad se auto-evalúa después de extraer el contenido (ver final de este paso).

Detectar tipo de fuente:

| Señal | Tipo | Método de extracción |
|-------|------|---------------------|
| URL con `x.com` o `twitter.com` | Tweet/Thread | Invocar skill `claudia-scrape` con la URL. Si es thread, usar `--full-thread`. |
| URL con `youtube.com` o `youtu.be` | Vídeo YT | `python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py URL --output /tmp/wisdom/` y leer el .md generado |
| URL con dominio de podcast (Spotify, Apple, iVoox, etc.) | Podcast | `python3 .claude/skills/claudia-scrape/podcast_transcribe.py URL --output /tmp/wisdom/` y leer el .md generado |
| URL de artículo o blog | Artículo | Invocar skill `claudia-scrape` con la URL |
| URL de Substack o newsletter | Newsletter | Invocar skill `claudia-scrape` con la URL |
| Texto pegado directamente (sin URL) | Texto directo | Usar el texto tal cual |
| PDF, documento | Documento | Leer el fichero si es una ruta local |

**Si no puedes extraer el contenido** (paywall, contenido dinámico, etc.), informa al usuario y sugiere alternativas (pegar el texto manualmente, usar otro método).

### Determinar profundidad

Si el usuario especificó `deep` o `normal` en los argumentos, usa ese modo. Si no, evalúa el contenido extraído y selecciona automáticamente:

| Señal | → Profundidad |
|-------|---------------|
| Vídeo >30 min o texto >3000 palabras | `deep` |
| Múltiples argumentos, frameworks o temas entrelazados | `deep` |
| Alta densidad de ideas (muchos datos, estudios, ejemplos concretos) | `deep` |
| Contenido corto o monotema (tweet, thread breve, opinión corta) | `normal` |
| Baja densidad (pocas ideas nuevas, mucho relleno) | `normal` |
| Calidad aparentemente baja | `normal` |

Informa brevemente al usuario de tu decisión: "Contenido denso (~X palabras), aplico extracción profunda" o "Contenido breve, extracción estándar".

---

## Paso 2 — Extraer sabiduría

Una vez tengas el contenido, extrae de forma estructurada según el modo de profundidad determinado.

### Modo normal (por defecto)

#### Ideas clave (5-15)
Las ideas más interesantes, sorprendentes o contraintuitivas del contenido. Cada una en 1-2 frases. No resúmenes genéricos — busca lo que hace pensar.

#### Insights refinados (3-7)
Versiones destiladas de las mejores ideas. Un insight es una idea elevada a principio: más abstracto, más aplicable, más transferible a otros contextos.

#### Citas textuales (3-10)
Frases exactas del autor/speaker que merezca la pena recordar. Con atribución.

#### Conceptos clave
Términos, frameworks o modelos mentales que introduce o utiliza el contenido. Breve definición de cada uno.

#### Acciones recomendadas (0-5)
Cosas concretas que el usuario podría hacer basándose en este contenido. Solo si aplica — no forzar acciones donde no las hay.

#### Meta
- **Takeaway en 1 frase** — Lo más importante del contenido en máximo 20 palabras
- **Para quién es útil** — Qué tipo de persona se beneficiaría más de este contenido
- **Calidad** — Valoración honesta: ¿merece la pena? ¿aporta algo nuevo o es más de lo mismo?

### Modo deep

Incluye todo lo anterior con rangos ampliados, más dos secciones adicionales. El objetivo es que el lector pueda prescindir del contenido original sin perder matices importantes.

#### Resumen narrativo (500-800 palabras)
El arco argumental completo: cómo llega el autor de A a B, qué evidencia usa, qué matices introduce, dónde reconoce límites. No es un resumen de "de qué va" — es reconstruir el razonamiento para que el lector pueda seguir la lógica sin volver al original.

#### Ideas clave (15-30)
Mismo criterio que en normal, pero con más cobertura. Cada idea en 2-3 frases, incluyendo el contexto o ejemplo que la sustenta.

#### Insights refinados (7-15)
Más insights, con el mismo criterio de abstracción y transferibilidad.

#### Citas textuales (10-20)
Más citas, incluyendo las que ilustran argumentos intermedios o matices que en el modo normal se pierden.

#### Argumentos y evidencia
Los datos, estudios, ejemplos concretos o casos que el autor usa para sostener sus puntos principales. No repetir las ideas — documentar la base empírica o lógica que las sostiene.

#### Conceptos clave, Acciones recomendadas, Meta
Igual que en modo normal.

---

## Paso 3 — Conectar con conocimiento existente

Busca conexiones con lo que ya sabemos:

1. **Busca en el vault con vault-search** — `python3 .claude/skills/vault-search/vault_search.py --context "<topics relevantes>" --max-tokens 1500`
2. **Si necesitas más detalle**, busca por texto: `python3 .claude/skills/vault-search/vault_search.py "concepto específico"`

Si encuentras conexiones:
- Menciona qué wisdom o research previo se relaciona y cómo
- Señala si este nuevo contenido refuerza, contradice o expande algo que ya teníamos
- Identifica patrones emergentes (si el mismo tema aparece en 3+ extracciones, es una señal)

Si no encuentras conexiones, no inventes — simplemente omite la sección.

---

## Paso 4 — Guardar y clasificar

### Formato del fichero

```markdown
---
source: "URL o referencia del contenido"
type: video | article | podcast | newsletter | text | tweet | thread
author: "nombre del autor o speaker"
title: "título del contenido"
date: YYYY-MM-DD
topics: [tema1, tema2, tema3]
quality: alta | media | baja
stance: esceptico | bullish | neutral | mixto
depth: normal | deep
origin: user | research/nombre-del-fichero.md
---

# {Título del contenido}

**Fuente:** {URL o referencia}
**Autor:** {nombre}
**Procesado:** {fecha de hoy}

## Takeaway

{1 frase, máximo 20 palabras}

## Resumen narrativo                    ← SOLO en modo deep

{500-800 palabras: arco argumental completo}

## Ideas clave

- {idea 1}
- {idea 2}
- ...

## Insights

- {insight refinado 1}
- {insight refinado 2}
- ...

## Citas

> "{cita textual}" — {autor}

> "{cita textual}" — {autor}

## Argumentos y evidencia               ← SOLO en modo deep

- {dato, estudio o ejemplo que sostiene un punto principal}
- ...

## Conceptos clave

- **{concepto}** — {definición breve}

## Acciones recomendadas

- {acción concreta 1}
- {acción concreta 2}

## Conexiones

- Relacionado con [{título}]({ruta relativa}) — {cómo se conecta}
```

### Dónde guardar

En Claudia OS: `user/vault/wisdom/`. Si el directorio no existe, créalo.

Si usas esta skill fuera de Claudia OS, guarda en `./wisdom/` en el directorio de trabajo actual.

### Naming

`{YYYY-MM-DD}_{slug-descriptivo}.md`

Ejemplo: `2026-04-11_gary-marcus-biggest-advance-ai-llm.md`

### Indexar el fichero nuevo

Después de guardar, reindexar para que el vault-search lo encuentre:

```bash
python3 .claude/skills/vault-search/vault_search.py --reindex-file "wisdom/{filename}.md"
```

Esto actualiza automáticamente el índice SQLite. Ya no es necesario editar INDEX.md a mano.

---

## Reglas

1. **Extrae lo valioso, no resumas.** Un resumen es "de qué va". Wisdom es "qué aprendí y por qué importa".
2. **Sé honesto con la calidad.** Si el contenido es mediocre o no aporta nada nuevo, dilo. Mejor un wisdom marcado como "baja calidad" que inflar todo.
3. **No inventes conexiones.** Solo conecta con conocimiento previo si la relación es real y útil.
4. **Citas textuales deben ser exactas.** Si no puedes garantizar la cita exacta (ej: subtítulos automáticos), indica que es aproximada.
5. **Topics deben ser reutilizables.** Consulta la taxonomía en `user/vault/CLAUDE.md` antes de crear un topic nuevo.
6. **Verifica duplicados.** Antes de crear un fichero nuevo, busca en el vault: `python3 .claude/skills/vault-search/vault_search.py "<título o URL>"` para asegurarte de que esa fuente no está ya extraída.
7. **Antes de guardar ficheros**, haz `git pull` en ``.
8. **Escribe en el idioma** definido en `user/config/settings.json` (`language`), salvo citas textuales en su idioma original.
9. **Intake siempre usa modo normal.** El modo deep es para extracciones manuales donde hay interés explícito en profundidad.

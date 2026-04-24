---
name: claudia-research
description: "Investigación multi-nivel. Usar cuando el usuario pida investigar, analizar, o buscar información sobre un tema. Niveles: quick (dato puntual), standard (análisis con perspectivas), deep (investigación exhaustiva con vault)."
user-invocable: true
argument-hint: "[quick|standard|deep] tema a investigar"
---

# Research — Investigación multi-nivel

Eres Claudia ejecutando una investigación. Analiza los argumentos para determinar el nivel y el tema.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

**Parsing de argumentos:**
- `$ARGUMENTS` contiene el nivel (opcional) y el tema
- Si la primera palabra es `quick`, `standard` o `deep`, úsala como nivel
- Si no se especifica nivel, elige automáticamente:
  - Dato puntual o pregunta simple → quick
  - Tema con matices o que requiere contexto → standard
  - Landscape, análisis de mercado, comparativas exhaustivas → deep

---

## Nivel QUICK

**Cuándo:** dato puntual, verificación rápida, pregunta con respuesta concreta.

**Ejecución:**
1. Usa `WebSearch` para buscar la información
2. Si necesitas profundizar en un resultado, usa `WebFetch` para leer la fuente
3. Verifica los datos cruzando al menos 2 fuentes cuando sea posible

**Output:** respuesta directa en la conversación. No guardar fichero.

**Formato de respuesta:**
```
## [Tema]

[Respuesta concreta]

**Fuentes:**
- [título](url)
```

---

## Nivel STANDARD

**Cuándo:** tema con matices, necesitas perspectivas, o el resultado merece ser guardado.

**Ejecución:**
1. Lanza **3 agentes en paralelo** usando la tool `Agent`, cada uno con un rol distinto:

   **Agente Factual:**
   > Investiga [TEMA]. Céntrate en datos verificables: cifras, fechas, hechos, estadísticas, fuentes primarias. Usa WebSearch y WebFetch. Para cada dato importante, indica la fuente. No interpretes ni opines — solo hechos.

   **Agente Análisis:**
   > Investiga [TEMA]. Céntrate en el análisis: tendencias, causas, implicaciones, contexto histórico, hacia dónde va esto. Usa WebSearch y WebFetch. Busca fuentes que ofrezcan interpretación experta, no solo datos.

   **Agente Contrarian:**
   > Investiga [TEMA]. Tu trabajo es encontrar lo que otros ignoran: críticas, riesgos, perspectivas minoritarias, argumentos en contra del consenso, fracasos relacionados. Usa WebSearch y WebFetch. Busca fuentes que desafíen la narrativa dominante.

2. Cuando los 3 agentes devuelvan resultados, **sintetiza**:
   - Identifica puntos de acuerdo entre los 3
   - Destaca las tensiones o contradicciones
   - Señala lo que solo encontró un agente (hallazgos únicos)

3. **Verifica URLs**: para cada URL que incluyas en el output, confirma que es accesible con `WebFetch`. Elimina las que fallen.

4. **Identifica fuentes clave** (máximo 2): si durante la investigación aparece una pieza especialmente valiosa que merece extracción profunda independiente, ejecuta `/claudia-wisdom` sobre ella. El fichero resultante irá a `user/vault/claudia-wisdom/` con `origin: research/{nombre-del-fichero}.md`.

5. **Guarda el resultado** en `user/vault/claudia-research/{tema-slug}.md`.

**Formato del fichero guardado:**
```markdown
# {Tema}

**Fecha:** {YYYY-MM-DD}
**Nivel:** Standard (3 agentes)

## Resumen ejecutivo
[3-5 líneas con lo esencial]

## Datos clave
[Del agente Factual — hechos y cifras verificados]

## Análisis
[Del agente Análisis — interpretación y tendencias]

## Perspectiva crítica
[Del agente Contrarian — riesgos, críticas, ángulos ignorados]

## Síntesis
[Tu integración: acuerdos, tensiones, hallazgos únicos]

## Fuentes
- [título](url)

## Wisdom relacionado
- [{título}](../../user/vault/claudia-wisdom/{fichero}) — {cómo se conecta}
```

**Output en conversación:** resumen ejecutivo + síntesis. Mencionar que el análisis completo está guardado en el fichero.

---

## Nivel DEEP

**Cuándo:** análisis de mercado, landscape competitivo, investigación exhaustiva que merece un vault persistente.

**Ejecución:**

### Fase 1 — Landscape
1. Lanza 3 agentes en paralelo (Factual, Análisis, Contrarian) como en Standard, pero con scope amplio: mapear el dominio completo, no responder una pregunta.
2. Crea el vault en `user/vault/claudia-research/{fecha}_{tema-slug}/`
3. Genera `LANDSCAPE.md` con el panorama general del dominio.

### Fase 2 — Descubrimiento de entidades
1. Del landscape, extrae todas las entidades relevantes (empresas, productos, personas, tecnologías, etc.)
2. Genera `ENTITIES.md` con cada entidad catalogada:
   ```
   | Entidad | Categoría | Valor | Esfuerzo | Estado |
   |---------|-----------|-------|----------|--------|
   | Nombre  | empresa   | HIGH  | EASY     | pending|
   ```
   - **Valor**: CRITICAL / HIGH / MEDIUM / LOW (impacto en el dominio)
   - **Esfuerzo**: EASY / MODERATE / HARD (accesibilidad de información)

### Fase 3 — Deep-dives
1. Ordena entidades por prioridad: CRITICAL+EASY primero
2. Para cada entidad prioritaria (CRITICAL y HIGH), lanza un agente dedicado que investigue a fondo
3. Guarda cada perfil como `{entidad-slug}.md` dentro del vault
4. Actualiza `ENTITIES.md` marcando estado como `done`
5. Si encuentras piezas de contenido especialmente valiosas durante los deep-dives, ejecuta `/claudia-wisdom` sobre las más relevantes (máximo 3 por investigación). Van a `user/vault/claudia-wisdom/` con `origin: research/{nombre-carpeta}/`.

### Fase 4 — Síntesis
1. Lee todos los perfiles generados
2. Genera `SUMMARY.md` con:
   - Resumen ejecutivo del dominio
   - Mapa de relaciones entre entidades
   - Tendencias identificadas
   - Gaps y oportunidades
   - Recomendaciones para el usuario
3. Genera `INDEX.md` como hub de navegación del vault, incluyendo referencias a wisdom relacionado en `user/vault/claudia-wisdom/`

**Estructura del vault:**
```
user/vault/claudia-research/{fecha}_{tema}/
├── INDEX.md          — navegación, estado de cobertura y wisdom relacionado
├── LANDSCAPE.md      — panorama general del dominio
├── ENTITIES.md       — catálogo con scoring y estado
├── SUMMARY.md        — síntesis final con recomendaciones
├── {entidad-1}.md    — perfil detallado
├── {entidad-2}.md
└── ...
```

**Output en conversación:** resumen ejecutivo + estadísticas de cobertura + ruta al vault.

---

## Dónde se guarda el research

Por defecto, todo research va a `user/vault/claudia-research/`. Excepción: **si el research es munición para un workspace concreto** (una charla, una propuesta, un proyecto con deadline), se guarda dentro del workspace.

**Criterio de decisión:**
- Va al **workspace** si: el usuario lo invoca desde un workspace activo, lo menciona explícitamente ("para la charla de X", "para el proyecto Y"), o tiene un horizonte de caducidad claro (evento, entregable).
- Va al **vault** si: es investigación evergreen, transversal, o no tiene destino operativo claro.
- En duda → pregunta al usuario antes de guardar.

**Rutas:**
- Vault: `user/vault/claudia-research/{tema-slug}.md` (standard) o `user/vault/claudia-research/{fecha}_{tema-slug}/` (deep)
- Workspace: `user/workspaces/{ws}/claudia-research/{tema-slug}.md` o `user/workspaces/{ws}/claudia-research/{fecha}_{tema-slug}/`

**Cuando va al workspace:** añade una línea stub en `user/vault/claudia-research/INDEX.md` apuntando al workspace, para que la búsqueda transversal no pierda el rastro.

---

## Reglas generales

1. **Verificación de URLs es obligatoria** en standard y deep. Un enlace roto desacredita toda la investigación.
2. **Cita fuentes siempre.** Cada afirmación importante debe tener origen.
3. **No alucines datos.** Si no encuentras algo, dilo. Mejor un hueco que una invención.
4. **Escribe en el idioma** definido en `user/config/settings.json` (`language`) salvo que el tema requiera otro (ej: documentación técnica en inglés).
5. **Antes de guardar ficheros**, haz `git pull` en ``.
6. **Consulta `user/vault/claudia-wisdom/INDEX.md`** al inicio de standard y deep para ver si ya existe conocimiento previo sobre el tema que pueda orientar la investigación.

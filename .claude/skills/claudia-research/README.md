# Claudia Research — Investigacion multi-nivel

Investiga cualquier tema con el nivel de profundidad que necesites: desde una respuesta rapida hasta un vault exhaustivo con perfiles de entidades y recomendaciones.

## Que hace

Tienes una pregunta, un tema que explorar, o necesitas un analisis de mercado completo. En lugar de buscar tu mismo en 20 pestanas, le dices a Claudia que investigue y ella lanza agentes en paralelo con roles diferenciados (factual, analitico, contrarian) para cubrir todos los angulos. El resultado queda guardado en el vault para consulta futura.

Tres niveles de profundidad:

- **Quick** — Dato puntual o verificacion rapida. Sin fichero, respuesta directa.
- **Standard** — Analisis con 3 agentes en paralelo. Genera un fichero con datos, analisis y perspectiva critica.
- **Deep** — Investigacion exhaustiva: landscape del dominio, catalogo de entidades con scoring, deep-dives individuales y sintesis final. Genera un vault completo con multiples ficheros.

## Como usarlo

### Desde conversacion con Claudia

```
/claudia-research quick cuanto cuesta GPT-4o por millon de tokens
/claudia-research standard estado actual de los agentes de IA en produccion
/claudia-research deep landscape de herramientas de AI coding 2026
```

Si no especificas nivel, Claudia elige automaticamente segun la complejidad del tema:
- Pregunta con respuesta concreta → quick
- Tema con matices o que requiere contexto → standard
- Landscape, comparativas exhaustivas, analisis de mercado → deep

### Desde Telegram o intake

Tambien puedes encolar un tema de investigacion via intake, o pedirlo directamente en conversacion.

## Niveles en detalle

### Quick

Busca la informacion, cruza fuentes, responde en la conversacion. No guarda fichero.

```
## [Tema]

[Respuesta concreta]

**Fuentes:**
- [titulo](url)
```

### Standard

Lanza 3 agentes en paralelo:
- **Factual**: datos, cifras, estadisticas, fuentes primarias
- **Analisis**: tendencias, causas, implicaciones, contexto historico
- **Contrarian**: criticas, riesgos, perspectivas minoritarias, argumentos en contra

Despues sintetiza los resultados identificando acuerdos, tensiones y hallazgos unicos. Verifica todas las URLs. Si encuentra piezas de contenido especialmente valiosas (maximo 2), lanza `/claudia-wisdom` sobre ellas.

### Deep

Cuatro fases:

1. **Landscape** — Mapea el dominio completo con 3 agentes en paralelo
2. **Entidades** — Cataloga empresas, productos, tecnologias con scoring de valor/esfuerzo
3. **Deep-dives** — Investiga a fondo cada entidad prioritaria (CRITICAL + HIGH)
4. **Sintesis** — Mapa de relaciones, tendencias, gaps, oportunidades y recomendaciones

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Research standard | `user/vault/claudia-research/{tema-slug}.md` |
| Research deep (vault) | `user/vault/claudia-research/{fecha}_{tema-slug}/` |
| Wisdom extraido durante research | `user/vault/wisdom/` (con `origin: research/...`) |
| Research para un workspace | `user/workspaces/{ws}/claudia-research/` (con stub en vault) |

### Estructura de un vault deep

```
user/vault/claudia-research/{fecha}_{tema}/
├── INDEX.md          — navegacion y estado de cobertura
├── LANDSCAPE.md      — panorama general del dominio
├── ENTITIES.md       — catalogo con scoring y estado
├── SUMMARY.md        — sintesis final con recomendaciones
├── {entidad-1}.md    — perfil detallado
├── {entidad-2}.md
└── ...
```

### Vault vs. workspace

- Va al **vault** si es investigacion evergreen o transversal
- Va al **workspace** si es para un proyecto concreto (charla, propuesta, deadline)
- En duda, Claudia pregunta antes de guardar

## Requisitos

- Acceso a internet (WebSearch + WebFetch)
- `claude` CLI con permisos de agentes (para standard y deep, que lanzan sub-agentes)
- Skill `claudia-wisdom` disponible (para extraer wisdom de fuentes clave)

## Skills relacionadas

- **claudia-wisdom** — Research standard y deep pueden invocar wisdom sobre fuentes valiosas encontradas durante la investigacion
- **claudia-scrape** — Usada internamente cuando research necesita extraer contenido de URLs especificas
- **claudia-intake** — Puedes encolar temas de investigacion via el pipeline de intake

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-research/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Escribe siempre el output en inglés aunque el tema sea en español"
- "Añade una sección '## Implicaciones para mi negocio' al final de cada research standard"
- "Usa siempre nivel standard como mínimo aunque la pregunta parezca quick"
- "Incluye siempre fuentes en español cuando estén disponibles, priorizándolas sobre fuentes en inglés"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **Los agentes no se lanzan en paralelo**: verificar que la tool `Agent` esta disponible en la sesion
- **URLs rotas en el output**: standard y deep verifican URLs antes de guardar, pero las fuentes pueden caer despues. Re-ejecutar el research actualiza los enlaces
- **Research se guarda en vault pero era para un workspace**: mover manualmente el fichero y actualizar el stub en `user/vault/claudia-research/INDEX.md`
- **Deep research tarda mucho**: es normal — lanza multiples agentes en varias fases. Para temas acotados, usar standard

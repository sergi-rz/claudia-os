# Claudia Image — Generacion de imagenes

Genera imagenes con Google AI Studio usando estilos predefinidos o personalizados. Desde diagramas tecnicos para presentaciones hasta headers para newsletters o thumbnails de YouTube.

## Que hace

Le describes lo que quieres y Claudia elige automaticamente el modelo, estilo y tamanho adecuados segun el contexto. Puedes ser especifico ("diagrama dark-mode de la arquitectura de un transformer, 16:9") o vago ("una imagen para el articulo sobre microservicios") y Claudia decide la configuracion optima.

Las imagenes se guardan en `user/images/` por defecto, o en el directorio del workspace si estas trabajando en uno concreto.

## Como usarlo

### Desde conversacion con Claudia

```
/image un diagrama de como funciona un transformer
/image header para newsletter sobre productividad, estilo charcoal
/image thumbnail de YouTube sobre IA generativa, 16:9
```

Claudia interpreta tu peticion, elige estilo/modelo/tamanho, genera la imagen y te la muestra.

### Llamada directa al script

```bash
# Basico (1:1, modelo automatico)
python3 .claude/skills/claudia-image/generate.py "technical diagram of microservices" \
  --output user/images/microservices.png

# Con estilo y tamanho
python3 .claude/skills/claudia-image/generate.py "brain neural network" \
  --style charcoal --size 16:9 --output brain.png

# Modelo especifico
python3 .claude/skills/claudia-image/generate.py "retrato artistico" \
  --model imagen-ultra --size 3:2 --output retrato.png
```

## Estilos disponibles

### Incluidos

| Estilo | Descripcion | Ideal para |
|--------|-------------|------------|
| `charcoal` | Sketch a carboncillo en papel texturizado, tonos calidos | Headers de blog, portadas |
| `dark-diagram` | Infografia dark-mode, line-art cyan/purpura | Presentaciones tecnicas, slides |
| `clean` | Minimalista sobre blanco, lineas finas | Blog generico, documentacion |
| `woodcut` | Grabado xilografico B&N, contraste dramatico | Articulos editoriales |
| `blueprint` | Plano tecnico, lineas blancas sobre azul marino | Arquitectura, sistemas |
| `scientific` | Ilustracion cientifica vintage, plumilla con acuarela | Contenido educativo |

### Estilos personalizados

Puedes crear tus propios estilos en `user/styles.json` (dentro del directorio de la skill). Se cargan automaticamente y estan disponibles con `--style`.

## Modelos

| Modelo | Precio | Aspect ratios | Notas |
|--------|--------|---------------|-------|
| `flash` | Gratis | Solo 1:1 | Gemini 2.5 Flash |
| `nano2` | ~$0.045/img | Solo 1:1 | Default para imagenes cuadradas |
| `pro` | ~$0.045/img | Solo 1:1 | Mayor calidad en 1:1 |
| `imagen-fast` | $0.02/img | Todos | Default para ratios no cuadrados |
| `imagen` | $0.04/img | Todos | Calidad intermedia |
| `imagen-ultra` | $0.06/img | Todos | Maxima calidad |

Regla automatica: si el tamanho es 1:1, usa `nano2`. Si no, usa `imagen-fast`. Tu puedes forzar cualquier modelo con `--model`.

## Tamanhos (aspect ratios)

`1:1` (default), `16:9`, `3:2`, `4:3`, `3:4`, `2:3`, `9:16`

Los modelos Gemini (flash, nano2, pro) solo generan 1:1. Para otros ratios se usa automaticamente un modelo Imagen.

## Configuracion

### 1. API key de Google AI Studio (gratuita)

1. Ve a https://aistudio.google.com/apikey
2. Crea una API key (boton "Create API key")
3. Anadela a `user/credentials/.env`:
   ```
   GOOGLE_AI_API_KEY=tu_key_aqui
   ```

Sin la key, el script muestra instrucciones al ejecutarse.

## Donde se guardan las imagenes

| Contexto | Ruta |
|----------|------|
| Sin workspace activo | `user/images/` |
| Dentro de un workspace | `user/workspaces/<nombre>/images/` |

Los nombres son descriptivos: `transformer-architecture.png`, no `output.png`.

## Skills relacionadas

- **claudia-intake** — las extracciones de contenido pueden necesitar imagenes de portada
- **claudia-research** — los informes de investigacion pueden incluir diagramas generados
- **claudia-wisdom** — las fichas de wisdom no usan imagenes, pero el contenido que procesan puede inspirar una

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-image/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Para headers de newsletter usa siempre el estilo 'charcoal' con ratio 16:9"
- "Para thumbnails de YouTube usa siempre modelo imagen-fast con ratio 16:9"
- "Cuando no se especifica destino, pregunta antes de generar en vez de usar el default"
- "Incluye siempre la fecha en el nombre del fichero: YYYY-MM-DD_nombre.png"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **"GOOGLE_AI_API_KEY no configurada"**: verificar que `user/credentials/.env` existe y contiene la key
- **HTTP 400 con modelo Gemini y size distinto de 1:1**: los modelos Gemini solo generan 1:1. Usa un modelo Imagen o cambia a `--size 1:1`
- **HTTP 429**: has superado la cuota de la API. Espera o revisa tu plan en Google AI Studio
- **Imagen generada pero no se ve**: Claudia deberia mostrarla con Read tras generarla. Si no, busca el fichero en la ruta indicada en el output
- **Estilo personalizado no aparece**: verificar que `user/styles.json` existe en el directorio de la skill y tiene formato JSON valido

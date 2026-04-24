---
name: claudia-image
description: "Genera imágenes con estilos predefinidos o personalizados. Usar cuando el usuario pida crear una imagen, diagrama, header, thumbnail o ilustración."
user-invocable: true
argument-hint: "descripción de la imagen [para newsletter|youtube|twitter|diagrama]"
---

# Image — Generación de imágenes

Analiza `$ARGUMENTS` para decidir qué generar, con qué estilo y configuración.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

---

## Catálogo de estilos

### Estilos incluidos (core)

El core incluye dos estilos genéricos como punto de partida. Son funcionales, pero la idea es que cada usuario cree los suyos propios.

| Estilo | Descripción |
|--------|------------|
| `dark-diagram` | Infografía sobre negro puro. Line-art blanco fino con acentos cyan y violeta. Técnico, cerebral. |
| `woodcut` | Grabado xilográfico en B&N. Trazos tallados con textura de veta de madera. Alto contraste. |

### Estilos del usuario

Los estilos personalizados viven en `user/styles.json` (dentro de esta skill). Se cargan automáticamente y tienen prioridad sobre los core si coincide el nombre. Consulta ese fichero para ver los disponibles y sus descripciones.

Cada estilo de usuario es un prompt ultra-detallado que define fondo, paleta de color exacta, calidad de trazo, tipografía, iluminación y exclusiones. Este nivel de detalle es lo que garantiza consistencia visual entre imágenes generadas en momentos distintos.

### Sin estilo
Si el usuario da un prompt muy específico o pide algo fotorrealista, no aplicar estilo. Pasar el prompt directo.

### Primera vez sin estilos propios

Si `user/styles.json` no existe o está vacío, **antes de generar la primera imagen**, ofrece al usuario crear su propio estilo:

> *Todavía no tienes estilos propios definidos. Los estilos son prompts detallados que mantienen la coherencia visual de todas tus imágenes. Puedo ayudarte a crear uno ahora: descríbeme qué estética te gustaría (materiales, colores, sensación) y lo convertimos juntos en un estilo consistente. Si prefieres avanzar rápido, puedo usar uno de los estilos genéricos incluidos (`dark-diagram`, `woodcut`).*

El flujo para crear un estilo:
1. El usuario describe la estética que busca (puede ser vago: "algo tipo libreta moleskine", "estilo retro de los 70")
2. Claudia genera un prompt detallado especificando: soporte/fondo, paleta de color con códigos hex, calidad de trazo, tipografía, iluminación, y una lista explícita de exclusiones (qué NO debe aparecer)
3. Se genera una imagen de prueba con ese prompt
4. Se itera hasta que el usuario esté satisfecho
5. Se guarda en `user/styles.json` con nombre, descripción y el prompt final

---

## Lógica de decisión

### 1. Detectar contexto de uso

Analiza los argumentos y la conversación para inferir el destino. Si el usuario tiene estilos personalizados definidos en `user/styles.json`, priorízalos cuando encajen con el contexto.

**Si el usuario especifica estilo, modelo o tamaño explícitamente, su elección siempre prevalece.**

### 2. Elegir modelo

| Caso | Modelo |
|------|--------|
| Cualquier tamaño ≠ 1:1 | `imagen-fast` (único que soporta aspect ratios nativos) |
| El usuario pide calidad máxima | `imagen-ultra` para ratios ≠ 1:1, `pro` para 1:1 |
| El usuario pide ahorrar | `flash` (gratis, solo 1:1) |
| Default 1:1 | `nano2` |

Si un estilo de usuario en `styles.json` incluye `recommended_model`, usar ese modelo por defecto para ese estilo.

**Nota sobre aspect ratios:** Los modelos Gemini (flash, nano2, pro) solo generan 1:1. Si el tamaño elegido no es 1:1, usar modelo Imagen (imagen-fast/imagen/imagen-ultra).

### 3. Construir el prompt

El prompt que pasas al tool debe describir el **sujeto** de la imagen, no el estilo. El flag `--style` del tool ya inyecta el prompt de estilo completo.

- Escribe el prompt en **inglés** (los modelos rinden mejor)
- Sé específico y descriptivo sobre el contenido
- No repitas instrucciones de estilo que ya están en el flag `--style`

Ejemplo:
- El usuario dice: "diagrama de cómo funciona un transformer"
- Prompt: `"technical diagram showing transformer architecture: attention mechanism, encoder-decoder blocks, positional encoding, with labeled arrows showing data flow"`

### 4. Decidir nombre y ruta del fichero

**Si estás trabajando en un workspace concreto**, guarda la imagen en el directorio apropiado de ese workspace (ej: `user/workspaces/<nombre>/images/`).

**Si no hay workspace claro**, guarda en `user/images/`.

El nombre debe ser descriptivo: `transformer-architecture.png`, no `output.png`.

---

## Ejecución

Una vez decidido estilo, modelo, tamaño y ruta:

```bash
python3 .claude/skills/claudia-image/generate.py "PROMPT EN INGLÉS" \
  --style ESTILO \
  --model MODELO \
  --size RATIO \
  --output RUTA
```

Omite `--style` si no aplica estilo. Omite `--model` para usar el default automático del tool.

---

## Después de generar

1. **Muestra la imagen** al usuario (usa Read para que la vea)
2. **Informa la ruta exacta** donde se guardó, el estilo, modelo y coste usado
3. **Pregunta si quiere ajustes** — variaciones comunes:
   - Cambiar estilo manteniendo el mismo sujeto
   - Ajustar el prompt (más detalle, menos elementos, otro enfoque)
   - Cambiar modelo (más calidad, más barato)
   - Regenerar (mismo prompt, resultado diferente)

---

## Setup (primera vez)

Esta skill necesita una API key de Google AI Studio (gratuita).

1. Ve a https://aistudio.google.com/apikey
2. Crea una API key (botón "Create API key")
3. Añádela a `user/credentials/.env`:
   ```
   GOOGLE_AI_API_KEY=tu_key_aqui
   ```

Si usas esta skill fuera de Claudia OS, exporta la variable directamente: `export GOOGLE_AI_API_KEY=...`

El modelo `flash` es gratuito. Los modelos Imagen 4 cuestan entre $0.02 y $0.06 por imagen.

Sin la key, el script mostrará instrucciones al ejecutarse.

---

## Reglas

1. **No mezclar estilos** dentro de la misma pieza de contenido (si un artículo usa un estilo, todas las imágenes del artículo deben usar el mismo)
2. **Escribir prompts en inglés** — los modelos generan mejor
3. **Antes de generar**, confirma la configuración si hay ambigüedad (ej: no está claro si es para newsletter o para redes)

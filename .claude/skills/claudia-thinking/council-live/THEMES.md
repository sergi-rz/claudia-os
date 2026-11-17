# Temas de La Sala del Consejo

La Sala (el panel visual del Council) separa la lógica del aspecto. La lógica es común a todos los
temas: el orden de las voces, las réplicas, los modos Escena / Rápido / Acta, los mensajes
paginados, la entrada de los miembros y el modo grabación. Un tema solo decide cómo se ve.

## Dónde viven

| Qué | Dónde | Lo actualiza `/claudia-update` |
|---|---|---|
| Temas que trae la skill (`arturo`, `minimal` y `retro`, que se muestra como *16 bits*) | `.claude/skills/claudia-thinking/council-live/themes/<nombre>/` | Sí |
| Tus temas | `.claude/skills/claudia-thinking/user/council-themes/<nombre>/` | **No, nunca** |

Si un tema tuyo se llama igual que uno de la skill, manda el tuyo. Así puedes retocar el de por
defecto copiándolo a `user/council-themes/arturo/` sin perder los cambios al actualizar.

## Cómo se elige

En La Sala hay un selector de tema; lo que eliges se recuerda en el navegador. El tema por defecto
sale de `user/config/settings.json`:

```json
{ "skill_council": { "theme": "arturo" } }
```

Sin esa clave, `arturo`. También se puede forzar por URL: `http://localhost:8787/?theme=minimal`.

## Qué lleva un tema

```
<nombre>/
├── theme.css    obligatorio: el aspecto
├── theme.json   opcional: nombre visible, fuentes, textos, escena y ajustes
└── scene.webp   opcional: la ilustración de la sala (16:9)
```

### theme.json

```json
{
  "label": "Mesa del Rey Arturo",
  "fonts": ["https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&display=swap"],
  "pixelate": false,
  "label_case": "normal",
  "strings": { "brand": "La Mesa Redonda", "enter": "{name} toma asiento" }
}
```

- **`label`**: el nombre en el selector.
- **`fonts`**: hojas de estilo de fuentes que cargar.
- **`pixelate`**: `false` (fotos tal cual), `true` (pixeladas a 28 px) o un número (el tamaño en px al
  que se pixelan; 48 se reconoce bien y sigue pareciendo pixel art).
- **`scene`**: una ilustración de fondo que trae la sala y la mesa dibujadas.

  ```json
  "scene": { "image": "scene.webp", "seats": { "cx": 47.7, "cy": 53, "rx": 35, "ry": 31 } }
  ```

  `cx` y `cy` son el centro de la mesa dentro de la imagen, en % de su ancho y su alto; `rx` y `ry`, a
  qué distancia del centro se sientan los miembros (también en %). El pergamino, el tablero de opciones
  y los carteles se colocan sobre ese centro. Con escena, la mesa dibujada con CSS desaparece. La imagen
  tiene que ser 16:9; para medir el centro, abre la imagen y divide las coordenadas de la mesa entre su
  ancho y su alto. Si un asiento se sale del marco, baja `ry`.
- **`sounds`**: el perfil de sonido. `"medieval"` (campanas, tambor, pluma y fanfarria), `"8bit"`
  (pitidos de consola), `"soft"` (tonos suaves, por defecto) o `"none"`. Se sintetizan en el navegador,
  sin ficheros. El usuario los silencia con el botón *Sonido* o la tecla M.
- **`label_case`**: `"upper-plain"` pone en mayúsculas y sin tildes los rótulos cortos (nombres en el
  diálogo, rótulos de la mesa, títulos del veredicto). Sirve para fuentes que no tienen mayúsculas con
  tilde, como las pixeladas. Si no, `"normal"`.
- **`strings`**: los textos que dice La Sala. Los que no pongas salen por defecto:

| Clave | Por defecto | Dónde sale |
|---|---|---|
| `brand` | La Sala del Consejo | Rótulo de arriba |
| `host` | Claudia | Quien presenta las réplicas y el veredicto |
| `enter` | {name} toma asiento | Cartel de la entrada de cada miembro |
| `tableIdle` / `tableLive` / `tableReplies` / `tableDone` | El consejo se reúne / delibera / Réplicas / Veredicto | Rótulo en el centro de la mesa |
| `replies` / `repliesLine` | Ronda de réplicas / … | Separador y frase de la anfitriona al abrir las réplicas |
| `verdict` / `verdict2` | Veredicto del consejo / Veredicto tras las réplicas | Títulos de las síntesis |
| `hint` | espacio para seguir | Ayuda junto al ▼ del diálogo |
| `convoked` / `openLine` | Se convoca el consejo / Os he reunido para pensar esto: {q} | Apertura: título sobre la mesa y frase de la anfitriona ({q} es la pregunta) |
| `options` / `optionsLine` | Opciones sobre la mesa / … | Tablero de opciones |
| `backs` / `objects` | la defienden / le ponen pegas | Opciones en el modo Rápido y el Acta |
| `rebate` / `completa` / `matiza` / `replyTo` | rebate a / completa a / matiza a / responde a | Tipo de cada réplica |
| `sources` | Fuentes | Lista de piezas citadas bajo cada voz |
| `empty` | Todavía no hay ningún consejo… | Sin sesiones |

### theme.css: lo que puedes vestir

La estructura (posiciones, qué se ve en cada modo, grabación) está en `base.css` y no hace falta
tocarla. Escribe tus reglas con el prefijo `.theme-<nombre>` para no pisar a otros temas.

| Elemento | Clase | Notas |
|---|---|---|
| Página | `body.theme-<nombre>` | Fondo, fuente y color base. Modos: `body.mode-scene` / `mode-quick` / `mode-log`; grabación: `body.rec` |
| Cabecera | `.title`, `.question`, `.status` (`.status b` = estado en directo) | |
| Controles | `.controls button`, `.controls select`, `.tabs button`, `button.active`, `.quick-actions button` | |
| Sala | `.stage`, `.hall` | `.hall` es una capa vacía para decorar (estandartes, ventanas…) con `::before` y `::after` |
| Mesa | `.table`, `.table-label`, `.emblem`, `.label-text` | `.emblem` es un hueco vacío para un adorno |
| Asientos | `.seat`, `.seat .portrait`, `.portrait .pic`, `.tile`, `.plate .name`, `.plate .kind`, `.bubble` | Tipos: `.kind-real`, `.kind-rol`, `.kind-inferida`. Estados: `.state-waiting`, `.state-thinking`, `.state-speaking`, `.state-spoken` |
| Réplica | `.beam .glow`, `.beam .ray` | Líneas SVG entre quien replica y a quién. No uses filtros SVG: desaparecen en líneas verticales |
| Entrada | `.toast span` | Cartel «X toma asiento» |
| Veredicto | `.decree`, `.decree h3` | Se muestra sobre la mesa |
| Diálogo | `.dialog`, `.dialog .portrait` (`.kind-host` para la anfitriona), `.speaker .who`, `.speaker .to`, `.line`, `.next`, `.hint`, `.caret` | |
| Texto | `.cite` (citas «…»), `.date` (fechas), `.verdict .row`, `.verdict .label` | |
| Rápido | `.card`, `.card summary`, `.card .name`, `.card .headline`, `.card .chev`, `.card .text`, `.card.synth`, `.card.reply`, `.quick-divider` | |
| Acta | `.entry`, `.entry h4`, `.entry .to`, `.entry.reply`, `.entry.synth`, `.entry.divider` | |
| Apertura | `.decree.opening` | El pergamino con la pregunta, antes de la entrada |
| Opciones | `.board`, `.option`, `.opt-title`, `.opt-detail`, `.opt-people`, `.mini.pro`, `.mini.con` | Tablero sobre la mesa; `.mini` son las caras de quien defiende (`.pro`) o pone pegas (`.con`) |
| Relaciones | `.beam .type-rebate`, `.type-completa`, `.type-matiza`, `.type-responde`, `.beam .map`, `.legend`, `.legend-item i` | Color del rayo según el tipo de réplica; `.map` es el mapa final con todas |
| Tipo de réplica en texto | `.to.type-…`, `.card.reply.type-…`, `.entry.reply.type-…` | |
| Fuentes | `a.cite`, `.sources`, `.sources a`, `.options-list`, `.pro-txt`, `.con-txt` | |
| Ficha | `.sheet`, `.sheet-card`, `.sheet-portrait`, `.sheet-name`, `.sheet-kind`, `.sheet-desc`, `.sheet-h`, `.sheet-close` | Al pulsar un miembro |
| Vacío | `.empty` | |

Las iniciales y los iconos de los roles tienen un color de fondo calculado por nombre; ajusta su
saturación y luminosidad con `--tile-s` y `--tile-l` en `body.theme-<nombre>`.

## Crear un tema nuevo

1. Copia el que más se parezca a lo que quieres a `user/council-themes/<nombre>/`.
2. Cambia `label` en `theme.json` y el prefijo `.theme-<viejo>` por `.theme-<nombre>` en `theme.css`.
3. Abre La Sala y elígelo en el selector. No hace falta reiniciar el servidor.

Si se lo pides a Claudia («hazme un tema de La Sala tipo tertulia de radio»), lo crea ella siguiendo
estos pasos, siempre en `user/council-themes/`.

# Claudia YT Transcript — Subtitulos y clips de YouTube

Descarga subtitulos automaticos de videos de YouTube y los convierte en ficheros Markdown limpios, listos para procesar. Tambien recorta clips de video (b-roll) a partir de timestamps.

Es una skill-libreria: la usan internamente claudia-wisdom, claudia-intake, claudia-corpus-sync y claudia-research, pero tambien se puede invocar directamente desde la linea de comandos.

## Que hace

### Subtitulos
Dado un enlace de YouTube, descarga los subtitulos automaticos (VTT), elimina duplicados y etiquetas de formato, y genera un `.md` con titulo, fecha, enlace al video y la transcripcion formateada en parrafos legibles.

### Clips (b-roll)
Descarga fragmentos de video recortados a partir de timestamps. Util para preparar b-roll de charlas, entrevistas o tutoriales. Soporta descarga individual o en batch desde un fichero de clips.

## Como usarlo

### Descargar subtitulos

```bash
# Un video, subtitulos en castellano (idioma por defecto)
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py \
  https://www.youtube.com/watch?v=VIDEO_ID \
  --output /ruta/destino/

# Varios videos a la vez
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py \
  https://www.youtube.com/watch?v=AAA \
  https://www.youtube.com/watch?v=BBB \
  --output /ruta/destino/

# Subtitulos en ingles
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py \
  https://www.youtube.com/watch?v=VIDEO_ID \
  --output /ruta/destino/ --lang en

# Con cookies (para videos que requieren sesion)
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py \
  https://www.youtube.com/watch?v=VIDEO_ID \
  --output /ruta/destino/ --cookies /ruta/cookies.txt

# Con cookies del navegador directamente
python3 .claude/skills/claudia-yt-transcript/extract_subtitles.py \
  https://www.youtube.com/watch?v=VIDEO_ID \
  --output /ruta/destino/ --cookies-from-browser chrome
```

El fichero generado se nombra automaticamente como `YYYY-MM-DD-titulo-del-video.md`.

### Descargar clips

```bash
# Clip suelto (sin audio por defecto)
python3 .claude/skills/claudia-yt-transcript/download_clips.py \
  --url https://www.youtube.com/watch?v=VIDEO_ID \
  --start 14:30 --end 14:45 --name nombre-del-clip \
  --output /ruta/destino/

# Batch desde fichero
python3 .claude/skills/claudia-yt-transcript/download_clips.py \
  clips.txt --output /ruta/destino/

# Con audio incluido
python3 .claude/skills/claudia-yt-transcript/download_clips.py \
  clips.txt --output /ruta/destino/ --with-audio

# Limitar resolucion (default: 1080p)
python3 .claude/skills/claudia-yt-transcript/download_clips.py \
  clips.txt --output /ruta/destino/ --max-height 720
```

Formato del fichero de clips (una linea por clip, separado por `|`):
```
nombre | URL | inicio | fin | notas opcionales
hinton-nobel | https://youtube.com/watch?v=xxx | 2:15 | 2:30 | Charla Nobel 2024
altman-congress | https://youtube.com/watch?v=yyy | 45:10 | 45:25 |
```
Las lineas vacias y los comentarios (`#`) se ignoran. Los clips que ya existen en el directorio de salida se saltan automaticamente.

## Requisitos

Se necesitan dos herramientas externas:

```bash
# Linux (Debian/Ubuntu)
pip install yt-dlp && sudo apt install ffmpeg

# macOS
brew install yt-dlp ffmpeg
```

- `yt-dlp` es obligatorio para ambas funciones (subtitulos y clips)
- `ffmpeg` es obligatorio para clips (se usa como fallback para el recorte)

Si alguna falta, los scripts muestran un error indicando que instalar.

No se necesitan credenciales ni API keys. Para videos con restriccion de edad o region, se pueden usar cookies del navegador con `--cookies` o `--cookies-from-browser`.

## Donde se guardan los datos

Esta skill no tiene almacenamiento propio. Los ficheros se generan donde indique `--output`:

| Que | Donde tipico |
|-----|------|
| Transcripciones (wisdom) | `user/vault/wisdom/` |
| Transcripciones (corpus) | `user/workspaces/{ws}/{canal}/corpus/` |
| Clips de video | Directorio que elija el usuario |

## Formato del Markdown generado

```markdown
2026-01-15

# Titulo del video

**Enlace al video:** https://www.youtube.com/watch?v=VIDEO_ID

## Descripcion:

Primeras lineas de la descripcion del video (sin enlaces ni hashtags).

## Transcripcion del video:

Parrafos de 5 frases cada uno, limpios y sin timestamps.
El texto se agrupa automaticamente para facilitar la lectura.
```

## Skills relacionadas

- **claudia-wisdom** — Usa yt-transcript para extraer subtitulos y luego genera una sintesis estructurada (ideas clave, insights, citas)
- **claudia-intake** — Cuando encolas una URL de YouTube, intake usa yt-transcript para obtener el contenido
- **claudia-corpus-sync** — Sincroniza el corpus de un canal de YouTube descargando subtitulos de los videos nuevos via yt-transcript
- **claudia-research** — En investigaciones que incluyen videos de YouTube, usa yt-transcript como fuente

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-yt-transcript/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "El idioma por defecto de los subtítulos debe ser inglés (en), no español"
- "Genera párrafos de 3 frases en el Markdown, no de 5"
- "Añade al frontmatter del fichero generado el campo 'channel' con el nombre del canal"
- "Cuando descargues subtítulos directamente (no desde wisdom), guárdalos en ~/Downloads/ por defecto"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **"yt-dlp: command not found"**: Instalar con `pip install yt-dlp`
- **"ffmpeg: command not found"**: Instalar con `apt install ffmpeg` (Linux) o `brew install ffmpeg` (macOS)
- **Subtitulos vacios**: El video puede no tener subtitulos automaticos en el idioma pedido. Probar con `--lang en`
- **Error 403 / Sign in to confirm**: El video requiere sesion. Usar `--cookies /ruta/cookies.txt` o `--cookies-from-browser chrome`
- **Clips imprecisos en el corte**: yt-dlp a veces recorta con imprecision en los keyframes. El script reintenta automaticamente con ffmpeg como fallback
- **Timeout en clips largos**: Los clips de mas de 60 segundos tardan mas. El timeout es de 120s para yt-dlp y 300s para el fallback con ffmpeg

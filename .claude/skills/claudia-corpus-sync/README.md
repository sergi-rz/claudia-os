# Claudia Corpus Sync — Archivo local de contenido publicado

Mantiene sincronizado un archivo local de tu contenido publicado (YouTube, Substack) con lo que hay en la plataforma. Detecta piezas nuevas y las descarga como ficheros Markdown limpios.

## Para que sirve

Si eres creador de contenido, tu corpus es el archivo de todo lo que has publicado. Tenerlo en local permite que Claudia conozca tu voz, estilo y temas ya tratados, que pueda detectar autocitas o duplicados cuando preparas contenido nuevo, y que puedas analizar tu propia trayectoria.

Corpus-sync se encarga de que ese archivo este siempre al dia: consulta el feed RSS de tu canal de YouTube o el sitemap de tu Substack, compara con lo que ya tienes en local, y descarga lo que falta.

## Como usarlo

### Dry run (ver que falta sin descargar)

```bash
# Todas las fuentes del workspace
python3 .claude/skills/claudia-corpus-sync/sync.py miworkspace

# Solo una fuente concreta
python3 .claude/skills/claudia-corpus-sync/sync.py miworkspace --source yt
```

El dry run muestra cuantos videos/posts faltan y cuales son, sin descargar nada.

### Sincronizar (descargar lo nuevo)

```bash
# Todo
python3 .claude/skills/claudia-corpus-sync/sync.py miworkspace --sync

# Solo YouTube
python3 .claude/skills/claudia-corpus-sync/sync.py miworkspace --source yt --sync

# Solo Substack
python3 .claude/skills/claudia-corpus-sync/sync.py miworkspace --source nl --sync
```

### Desde conversacion con Claudia

```
/claudia-corpus-sync miworkspace
/claudia-corpus-sync miworkspace --source yt --sync
```

## Configuracion

### 1. Tener un workspace

Debe existir `user/workspaces/{nombre}/`. Si no lo tienes, crealo o usa `/claudia-onboarding`.

### 2. Crear `corpus.json` en la raiz del workspace

Fichero `user/workspaces/{nombre}/corpus.json`:

```json
{
  "sources": {
    "yt": {
      "type": "youtube",
      "channel_id": "UC8KraRubGUZAaG4TT7pku5w",
      "corpus_dir": "yt/corpus",
      "cookies_file": "yt/scripts/youtube_cookies.txt",
      "ignore_shorts": true,
      "lang": "es"
    },
    "nl": {
      "type": "substack",
      "url": "https://tu-publicacion.substack.com",
      "corpus_dir": "nl/corpus",
      "excluded_slugs": ["archive", "about", "mis-fuentes"]
    }
  }
}
```

Las claves (`yt`, `nl`, ...) son nombres libres que usaras con `--source`. Puedes tener tantas fuentes como quieras.

### Opciones por tipo de fuente

**YouTube:**
| Opcion | Obligatorio | Descripcion |
|--------|:-----------:|-------------|
| `channel_id` | Si | ID del canal (formato `UC...`) |
| `corpus_dir` | Si | Carpeta destino, relativa al workspace |
| `cookies_file` | No | Path a `cookies.txt` para videos con restriccion |
| `ignore_shorts` | No | Ignorar Shorts (default: `true`) |
| `lang` | No | Idioma de subtitulos (default: `es`) |

**Substack:**
| Opcion | Obligatorio | Descripcion |
|--------|:-----------:|-------------|
| `url` | Si | Dominio de la publicacion |
| `corpus_dir` | Si | Carpeta destino, relativa al workspace |
| `excluded_slugs` | No | Slugs a ignorar (ej: `archive`, `about`) |

### 3. (Opcional) Automatizar con cron

Para mantener el corpus al dia sin intervencion:

```bash
crontab -e
# Anadir (ejemplo: cada 6 horas):
0 */6 * * * .claude/skills/claudia-corpus-sync/cron_sync.sh miworkspace >> ~/.claude/logs/corpus-sync.log 2>&1
```

El script `cron_sync.sh` hace todo el ciclo: `git pull`, sincronizacion, `git commit` y `git push`. Necesita que el repo tenga remote configurado con permisos de push. Los logs se guardan en `user/workspaces/{ws}/logs/YYYY-MM-DD.md`.

## Requisitos

- **Python 3** con `beautifulsoup4` (para Substack): `pip install beautifulsoup4`
- **yt-dlp** (para YouTube): `pip install yt-dlp`
- **ffmpeg** (para YouTube, usado por yt-transcript): `apt install ffmpeg` o `brew install ffmpeg`
- Para el cron: acceso a git push en el repo

No se necesitan API keys. Las fuentes se consultan via RSS (YouTube) y sitemap (Substack), que son publicos.

## Donde se guardan los datos

| Que | Donde |
|-----|-------|
| Config del corpus | `user/workspaces/{ws}/corpus.json` |
| Corpus YouTube | `user/workspaces/{ws}/{corpus_dir}/` (ej: `yt/corpus/`) |
| Corpus Substack | `user/workspaces/{ws}/{corpus_dir}/` (ej: `nl/corpus/`) |
| Logs del cron | `user/workspaces/{ws}/logs/YYYY-MM-DD.md` |

Cada pieza se guarda como un `.md` con el formato `YYYY-MM-DD-titulo-slugificado.md`. El contenido incluye fecha, titulo, enlace y cuerpo (transcripcion para YouTube, texto completo para Substack).

## Ejemplo de ejecucion

```
$ python3 sync.py mi-workspace --sync

=== yt (youtube) ===
[youtube] Canal: UC8KraRubGUZAaG4TT7pku5w
[youtube] Feed: 12 videos (+ 3 shorts ignorados)
[youtube] En corpus: 10
[youtube] Nuevos: 2
  - Como uso IA para editar video (2026-04-10)
  - Mi setup de grabacion 2026 (2026-04-08)
Procesando: https://www.youtube.com/watch?v=...
  -> /ruta/corpus/2026-04-10-como-uso-ia-para-editar-video.md
Procesando: https://www.youtube.com/watch?v=...
  -> /ruta/corpus/2026-04-08-mi-setup-de-grabacion-2026.md

=== nl (substack) ===
[substack] Publicacion: https://tu-publicacion.substack.com
[substack] Posts en sitemap: 45
[substack] En corpus: 45
[substack] Al dia.

--- Total ---
Procesados: 2
Errores: 0
```

## Anadir nuevos tipos de fuente

Si necesitas sincronizar desde otra plataforma (RSS generico, WordPress, podcast...), crea un modulo en `sources/` siguiendo el patron de `youtube.py` o `substack.py`. El modulo debe exportar una funcion `sync(config, workspace_root, do_sync)` que devuelva `{"processed": N, "errors": N}`.

## Skills relacionadas

- **claudia-yt-transcript** — Corpus-sync usa yt-transcript para descargar los subtitulos de los videos de YouTube
- **claudia-wisdom** — Puedes lanzar wisdom sobre piezas del corpus para extraer insights estructurados
- **claudia-intake** — Intake gestiona contenido externo (de otros); corpus-sync gestiona tu propio contenido publicado

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-corpus-sync/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Añade al frontmatter de cada pieza el campo 'canal' con el nombre de la fuente"
- "Ignora posts de Substack de menos de 300 palabras"
- "Envíame un mensaje por Telegram cuando detectes piezas nuevas en cualquier fuente"
- "Guarda las transcripciones de YouTube con párrafos de 3 frases en vez de 5"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **"ERROR: no existe corpus.json"**: Crear el fichero `corpus.json` en la raiz del workspace (ver seccion Configuracion)
- **"tipo 'xxx' no soportado"**: Solo se soportan `youtube` y `substack`. Para otros tipos, crear un modulo en `sources/`
- **YouTube no detecta videos nuevos**: El feed RSS de YouTube solo muestra los ultimos 15 videos. Los mas antiguos no aparecen en el feed
- **Substack ERROR descargando**: Algunos posts pueden estar detras de paywall. Se saltan automaticamente
- **"beautifulsoup4 no esta instalado"**: `pip install beautifulsoup4`
- **El cron no hace push**: Verificar que el repo tiene remote configurado y el usuario tiene permisos. Revisar `user/workspaces/{ws}/logs/` para ver el log del dia

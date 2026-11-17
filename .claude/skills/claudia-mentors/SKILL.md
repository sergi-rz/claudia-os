---
name: claudia-mentors
description: "Corpus de autores de referencia: ingesta automática de newsletters, feeds y APIs de mentores, almacenamiento en vault con autor etiquetado, modos de consulta (consult, crossref) y voces reales para el Council de claudia-thinking."
scope: core
user-invocable: true
argument-hint: "[consult <autor> <tema>|crossref <tema>|add|backfill [<mentor-id>]|status]"
---

# Mentors — Corpus de autores de referencia

Gestiona un corpus con el contenido de los autores que el usuario sigue: lo ingiere a diario, lo
guarda en el vault con el metadato `author` y permite consultarlo por autor, cruzar autores entre sí
y darles voz en el Council de `claudia-thinking`.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio, si existe. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill. Si el usuario pide un ajuste permanente de la skill, guárdalo ahí: crea el fichero si no existe (`behavior.example.md` tiene ideas).

## Requisitos

- **`claudia-intake`** — la ingesta normal encola cada pieza en la intake, que extrae el wisdom y
  lo guarda en el vault cuando procesa su cola.
- **`vault-search`** — consultas, `status` y voces del Council.
- **`claudia-gmail`** — solo si algún mentor tiene fuentes de tipo `gmail`.

## Primera configuración

Si no existe `user/config/mentors.json`, cópialo de `mentors.example.json` (en este directorio) y
da de alta los mentores con el usuario (ver *Añadir un mentor*). Hazlo tú: el usuario no tiene por
qué editar JSON ni abrir una terminal.

Después, con el OK del usuario, programa la ingesta. El cómo (crontab, tarea de la app de
escritorio o programador del sistema) depende de dónde vive la instalación: ver *Tareas
programadas* en `core/architecture.md`.

- **Qué:** `python3 .claude/skills/claudia-mentors/mentor_ingest.py`, una o dos veces al día. Solo
  encola: lo que llega al vault depende del procesado diario de la intake, que también tiene que
  estar programado (ver `claudia-intake`).
- **En un servidor:** una línea de crontab, con el log en `.claude/logs/mentors.log`:
  `50 12 * * * cd <ruta-de-claudia> && python3 .claude/skills/claudia-mentors/mentor_ingest.py >> .claude/logs/mentors.log 2>&1`
- **En la app de escritorio:** puede ser una sola tarea diaria que lance la ingesta y, justo
  después, procese la cola como explica *Procesar la cola desde el agente* en `claudia-intake` (el
  agente de la tarea sintetiza el wisdom; nunca `claude -p`). Así lo nuevo de los mentores entra en
  el vault el mismo día.
- **Si el ordenador pasa días apagado:** la ingesta no duplica nada al ponerse al día, y Gmail
  conserva el histórico. Los feeds RSS no: solo muestran las últimas piezas (10-20 según el sitio),
  así que de un autor que publica a diario se pueden perder piezas tras una o dos semanas sin
  ejecutar. Para recuperarlas, `--backfill` solo sirve con fuentes `gmail`.

## Comandos

### `/claudia-mentors consult <autor> <tema>`
Qué dice un autor sobre un tema. Busca con 2-3 términos clave del tema:

```bash
python3 .claude/skills/vault-search/vault_search.py "<términos>" --author "<nombre>"
```

Lee las entradas más pertinentes y responde con su postura, citas textuales y la fecha de cada
pieza. Si no hay resultados, prueba sinónimos antes de concluir que el autor no ha tratado el tema.

### `/claudia-mentors crossref <tema>`
Compara lo que dicen varios autores sobre un mismo tema. Primero, quién ha escrito sobre ello:

```bash
python3 .claude/skills/vault-search/vault_search.py "<términos>" --count-by-author
```

Después, para cada autor con material, `"<términos>" --author "<nombre>"`. Presenta las posiciones
agrupadas por autor y cierra con convergencias, divergencias y tensiones.

### Council con mentores
No es un comando de esta skill: vive en el modo Council de `claudia-thinking`. Antes de deliberar,
el Council propone el reparto y ofrece como voces reales a los autores del vault con entradas sobre
el tema. El usuario valida quién participa: roles, mentores o una mezcla. Esta skill aporta el
corpus del que salen esas voces.

### `/claudia-mentors add`
Da de alta un mentor con el usuario: ver *Añadir un mentor*.

### `/claudia-mentors backfill [<mentor-id>]`
Ingesta histórica de las fuentes `gmail` (todos los correos aún no procesados):

```bash
python3 .claude/skills/claudia-mentors/mentor_ingest.py --backfill [--mentor <id>] [--gmail-max 50]
```

Variantes para backfills grandes:
- `--direct` — escribe cada correo tal cual en el vault, sin intake ni síntesis (0 tokens).
  Calidad `baja`: sin extracción de ideas y con topics por palabras clave.
- `--collect` — guarda los correos en `user/vault/.index/mentor_collect_queue.json` para procesarlos
  en el chat. Para cada item: extrae el wisdom con el formato de `claudia-wisdom`, guárdalo en
  `user/vault/wisdom/` con `author` y `origin: mentor`, reindexa con
  `vault_search.py --reindex-file wisdom/<fichero>` y añade su `id` a `processed_ids` del mentor en
  `user/config/mentors_state.json`. Borra el JSON al terminar.

Para probar sin escribir nada: `--dry-run`.

### `/claudia-mentors status`
```bash
python3 .claude/skills/claudia-mentors/mentor_ingest.py --status
```
Mentores configurados, entradas en el vault por autor e IDs procesados.

## Fuentes

Cada mentor tiene una o más fuentes en `user/config/mentors.json`:

| Tipo | Campos | Cuándo se lee |
|---|---|---|
| `rss` | `url` del feed (RSS 2.0 o Atom; Substack, Ghost, WordPress, YouTube…) | Cada pasada diaria. Solo trae título y enlace: la intake descarga el contenido |
| `gmail` | `account` (cuenta de `claudia-gmail`), `query` (búsqueda de Gmail) | En `--backfill`. Con `"daily": true`, también en cada pasada diaria (para quien solo publica por email) |
| `api` | `url` de un endpoint JSON que devuelve la pieza del día; `credentials_key` (variable de `user/credentials/.env` con el token Bearer); `fields` opcional | Cada pasada diaria |

- **YouTube:** el feed de un canal es
  `https://www.youtube.com/feeds/videos.xml?channel_id=<id>`, como fuente `rss`. Los shorts se
  omiten siempre; para incluirlos, `"include_shorts": true` en la fuente.
- **Filtros de una fuente `rss` (opcionales):**
  - `exclude_title`: expresiones regulares; se omite la pieza cuyo título encaje (recopilaciones,
    secciones fijas que no son opinión del autor).
  - `min_content_chars`: se omite la pieza cuyo cuerpo en el feed sea más corto. Sirve para las
    piezas de pago de Substack, que llegan al feed con solo unas líneas.
  - `use_feed_content: true`: usa el texto del propio feed (limpio de HTML y cortado en el pie) en
    vez de que la intake descargue la página. Para newsletters cuya web trae mucho ruido, como las
    de Mailchimp.
- **Fecha:** cada pieza llega al vault con su fecha de publicación, no la del día en que se procesa.
- **`fields` (api):** por defecto se esperan los campos `id`, `title`, `date`, `content` y `url`. Si el
  endpoint usa otros nombres, mapéalos: `"fields": {"id": "post_id", "title": "titulo"}`.
- **`footer_patterns` (por mentor, opcional):** expresiones regulares que marcan dónde empieza el pie
  de sus correos o newsletters. Se usan en `--direct` y con `use_feed_content`. Las genéricas
  («darse de baja», «unsubscribe», «© 20xx») ya vienen incluidas.
- **`topic_keywords` (raíz del fichero, opcional):** mapa `topic → palabras clave` para clasificar
  en `--direct`. Si no está, se usa uno genérico.

Un tipo de fuente que no sea uno de estos tres se ignora, con un aviso en el log.

## Añadir un mentor

1. Pregunta al usuario por dónde publica el autor: newsletter con web (casi siempre tiene RSS:
   prueba `<web>/feed`), solo por email o canal de YouTube.
2. Comprueba que la fuente funciona antes de darla de alta: que el feed responda y tenga piezas
   recientes, o que la búsqueda de Gmail devuelva sus correos. Un feed puede responder bien y
   llevar años congelado.
   Mira también si escribe desde su opinión o sobre todo resume a otros: en el Council, un autor
   que solo divulga suena igual que el resto. Lee dos o tres piezas recientes antes de decidir.
3. Añade la entrada a `user/config/mentors.json` (`id`, `name`, `description`, `tags`, `sources`).
   El `name` es el que aparecerá como `author` en el vault: úsalo igual siempre.
4. Si es una fuente `api`, guarda el token en `user/credentials/.env`, nunca en el JSON.
5. Prueba con `--dry-run --mentor <id>` y, si hay histórico en Gmail, lanza el backfill.
6. **Foto** (para el panel del Council): `mentor_ingest.py --fetch-photos --mentor <id>` la baja de
   la imagen de su feed, si la hay, a `user/config/mentor-photos/<id>.<ext>`. Es la imagen de la
   publicación: mírala, y si es un logo bórrala (mejor sus iniciales que un logo) o pide al usuario
   una foto. Los que solo publican por email no tienen imagen: la pone el usuario.

## Arquitectura

```
user/config/mentors.json (config) + mentors_state.json (estado)
        ↓
  mentor_ingest.py
        ↓
  rss / gmail / api → normaliza → intake (cola) → wisdom (agente o cron) → user/vault/wisdom/ (author: X)
                              └── --direct ──────────────────────────→ user/vault/wisdom/
                                                                              ↓
                                                                     vault-search (SQLite)
```

**Dedup:** `processed_ids` por mentor en `mentors_state.json`, más una comprobación por
`{fecha}_{slug(título)}` en el vault. Así no se duplica una pieza que llega por dos fuentes (la API
y el correo del mismo día, por ejemplo).

## Notas de la instancia

Si existe `user/ESTADO.md` en este directorio, léelo antes de dar de alta, quitar o depurar
mentores: recoge qué hay montado en esta instalación y qué se decidió no hacer, y por qué.
Mantenlo al día cuando cambie algo.

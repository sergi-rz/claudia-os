---
name: claudia-corpus-sync
description: Sincroniza el corpus de contenido publicado de un workspace (YouTube, Substack) con lo que hay en local. Útil para creadores que mantienen un archivo local de sus propias piezas publicadas.
user-invocable: true
argument-hint: "<workspace> [--source <nombre>] [--sync]"
---

# Corpus Sync

Sincroniza el corpus local de un workspace con las piezas publicadas en sus fuentes (canal de YouTube, newsletter de Substack, etc.). Detecta qué falta y lo descarga.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Qué es un "corpus"

Un corpus es el archivo local de tu propio contenido publicado. Cada pieza (un vídeo, un post) se guarda como `.md` dentro de `user/workspaces/{ws}/{canal}/corpus/`. Sirve para:

- Darle a Claudia el contexto de tu voz, estilo y temas ya tratados
- Detectar duplicados o autocitas cuando preparas contenido nuevo
- Analizar tu propia trayectoria (temas, evolución, frecuencia)

---

## Cómo configurarlo (setup)

### 1. Tener un workspace

Debe existir `user/workspaces/{nombre-del-workspace}/`. Si no lo tienes, créalo o usa `/claudia-onboarding` para generar uno. Por convención el workspace representa una marca personal, un canal, un proyecto.

### 2. Crear `corpus.json` en la raíz del workspace

En `user/workspaces/{ws}/corpus.json`:

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

- Las claves (`yt`, `nl`, ...) son nombres libres que usarás con `--source`.
- `corpus_dir` es relativo a la raíz del workspace. El directorio se crea si no existe.

### 3. (Opcional) Automatizar con cron

Si quieres que el corpus se mantenga al día sin intervención, añade el cron apuntando al script de la skill. Ejemplo (cada 6 horas):

```cron
0 */6 * * * .claude/skills/claudia-corpus-sync/cron_sync.sh <workspace>
```

`cron_sync.sh` hace `git pull` → sync → `git commit` + `git push` con log en `user/workspaces/{ws}/logs/YYYY-MM-DD.md`. Necesita que el repo esté configurado con remote y permisos de push.

Sin cron, simplemente invoca la sincronización manualmente cuando quieras actualizar el corpus (ver siguiente sección).

---

## Tipos de fuente soportados

### youtube
Feed RSS público del canal. Usa `yt-transcript` para bajar subtítulos.

- `channel_id` (obligatorio) — ID del canal, formato `UC...`
- `corpus_dir` (obligatorio) — carpeta destino
- `cookies_file` (opcional) — path a `youtube_cookies.txt` si los vídeos requieren sesión
- `ignore_shorts` (opcional, default `true`)
- `lang` (opcional, default `es`)

### substack
Sitemap.xml de una publicación de Substack.

- `url` (obligatorio) — dominio de la publicación (ej: `https://tu-publicacion.substack.com`)
- `corpus_dir` (obligatorio) — carpeta destino
- `excluded_slugs` (opcional) — slugs de páginas estáticas a ignorar (ej: `archive`, `about`)

Si necesitas otro tipo de fuente (RSS genérico, WordPress, etc.), añade un módulo en `sources/` siguiendo el patrón de `youtube.py` o `substack.py`.

---

## Invocación

```bash
# Dry run — ver qué falta sin descargar (todas las fuentes del workspace)
python3 .claude/skills/claudia-corpus-sync/sync.py <workspace>

# Sincronizar todo
python3 .claude/skills/claudia-corpus-sync/sync.py <workspace> --sync

# Solo una fuente
python3 .claude/skills/claudia-corpus-sync/sync.py <workspace> --source yt --sync
```

## Cuándo usar esta skill

- El usuario pide sincronizar/actualizar el corpus de su workspace.
- Se detectan piezas nuevas publicadas que no están en local.

## Después de sincronizar

1. Verificar 1-2 de los nuevos `.md` (fecha, título, cuerpo limpio).
2. Commit en `user/workspaces/{ws}/{canal}/corpus/` con mensaje descriptivo (si no usas el cron, que ya lo hace).

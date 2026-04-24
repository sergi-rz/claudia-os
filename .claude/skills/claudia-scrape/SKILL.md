---
name: claudia-scrape
description: "Extrae contenido de URLs (tweets, threads, Articles de X, artículos web). Skill-librería usada por claudia-wisdom, claudia-research y directamente por el usuario."
scope: core
user-invocable: true
argument-hint: "<URL> [--full-thread]"
---

# Scrape — Extracción de contenido web

Skill-librería que extrae contenido de URLs. Usada por `/claudia-wisdom` y `/claudia-research`, y también invocable directamente.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

---

## Paso 1 — Detectar tipo de URL y extraer

Analiza `$ARGUMENTS` para identificar el tipo de fuente y aplicar el handler apropiado:

| Señal | Tipo | Handler |
|-------|------|---------|
| URL con `x.com` o `twitter.com` | Tweet/Thread | **Handler Twitter** (ver abajo) |
| URL con `youtube.com` o `youtu.be` | Vídeo YT | Delegar a skill `claudia-yt-transcript` |
| URL de plataforma de podcast (ver lista) | Podcast | **Handler Podcast** (ver abajo) |
| Cualquier otra URL | Web genérica | **Escalación web** (ver abajo) |
| Texto sin URL | — | Devolver error: esta skill requiere una URL |

**Dominios de podcast reconocidos:** `spotify.com`, `podcasts.apple.com`, `ivoox.com`, `player.fm`, `podbean.com`, `transistor.fm`, `buzzsprout.com`, `anchor.fm`, `podcasters.spotify.com`, `spreaker.com`, `soundcloud.com`, `overcast.fm`, `pocketcasts.com`, `castbox.fm`

---

## Handler Twitter (FxTwitter API)

### Tweet individual

1. Extraer `{screen_name}` y `{tweet_id}` de la URL
   - Formatos soportados: `x.com/{user}/status/{id}`, `twitter.com/{user}/status/{id}`, `fxtwitter.com/...`, `vxtwitter.com/...`
   - Ignorar parámetros query (`?s=20`, `?t=...`, etc.)

2. Fetch via FxTwitter API:
   ```
   https://api.fxtwitter.com/{screen_name}/status/{tweet_id}
   ```

3. Del JSON de respuesta (`response.tweet`), extraer:
   - `text` — contenido del tweet
   - `author.name` y `author.screen_name` — autor
   - `created_at` — fecha
   - `likes`, `retweets`, `replies`, `views` — métricas
   - `is_note_tweet` — indica si es un tweet largo (Note)
   - `replying_to_status` — ID del tweet al que responde (para threads)
   - `media` — URLs de imágenes/vídeos si existen

4. Formatear output:

```markdown
**@{screen_name}** ({name}) — {fecha}

{texto del tweet}

[Likes: {n} | RTs: {n} | Replies: {n} | Views: {n}]
Fuente: {url original}
```

### Thread completo

Si el usuario pasa `--full-thread` O si durante la extracción se detecta que `replying_to_status` apunta al mismo autor (self-reply = thread):

1. Desde el tweet dado, caminar hacia atrás via `replying_to_status` hasta encontrar el tweet raíz (donde `replying_to_status` es `null` o el autor cambia)
2. Recopilar todos los IDs del thread
3. Fetch cada tweet y concatenar en orden cronológico
4. **Límite de seguridad:** máximo 50 tweets por thread. Si se supera, avisar al usuario.

Formato thread:

```markdown
**Thread de @{screen_name}** ({name}) — {fecha del primer tweet}
{n} tweets | Likes: {total} | RTs: {total}

---

**1/{n}**
{texto tweet 1}

**2/{n}**
{texto tweet 2}

...

---
Fuente: {url original}
```

### Articles de X

Los Articles son contenido largo nativo de X (publicados vía articles.x.com). Usan URLs con el formato estándar `x.com/{user}/status/{id}`, igual que tweets normales.

FxTwitter **sí soporta Articles** — devuelve el contenido completo del artículo en el campo `text` de la respuesta. No requiere lógica especial: el mismo flujo de tweet individual funciona.

Si el contenido extraído es significativamente más largo que un tweet normal (>1000 caracteres) y no tiene `replying_to_status`, trátalo como un Article. En el output, usar el formato:

```markdown
**Article de @{screen_name}** ({name}) — {fecha}

{contenido completo del artículo}

[Likes: {n} | RTs: {n} | Replies: {n} | Views: {n}]
Fuente: {url original}
```

### Fallback Twitter

Si FxTwitter falla (404, 500, rate limit):
1. Intentar syndication API: `https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=1`
   - Extraer `text`, `user.name`, `user.screen_name`, `favorite_count`, `created_at`
2. Si también falla, intentar oEmbed: `https://publish.twitter.com/oembed?url={url_original}`
   - Parsear el texto del blockquote en el campo `html`
3. Si todo falla, informar al usuario

---

## Handler Podcast (transcripción de audio)

Para URLs de plataformas de podcast, delegar al script de transcripción:

```bash
python3 .claude/skills/claudia-scrape/podcast_transcribe.py <URL> --output /ruta/destino/ [--lang auto]
```

El script intenta extraer el audio con una cadena de estrategias:
1. **yt-dlp** — funciona directamente con muchas plataformas (iVoox, Podbean, SoundCloud...)
2. **Scrape de página** — busca etiquetas `<audio>`, links a ficheros de audio, o enlaces RSS en la página
3. **Parse de RSS** — si encuentra un feed RSS, extrae la URL del `<enclosure>` del episodio más reciente

Una vez obtenido el audio: ffmpeg lo convierte a WAV 16kHz mono → whisper-cli transcribe → genera un `.md` con la transcripción formateada en párrafos.

### Limitaciones conocidas

- **Spotify**: usa DRM, yt-dlp no puede extraer audio. Si la URL es de Spotify, intentar igualmente (por si hay un RSS asociado), pero avisar al usuario si falla de que Spotify protege el audio con DRM.
- **Duración**: episodios muy largos (>2h) pueden tardar varios minutos en transcribir. El script ajusta el timeout automáticamente.
- **Precisión**: Whisper con el modelo base es razonable pero no perfecto, especialmente con nombres propios o jerga técnica.

### Output

El script genera un fichero `.md` con el mismo formato que `claudia-yt-transcript`:

```markdown
{fecha}

# {título} — {nombre del show}

**Fuente:** {url original}

## Transcripción:

{texto formateado en párrafos}
```

---

## Escalación web (URLs genéricas)

Para URLs que no son Twitter ni YouTube, escalación progresiva:

### Tier 1 — WebFetch (por defecto)
```
WebFetch(url, "Extrae el contenido principal del artículo en markdown limpio. Ignora navegación, sidebars, ads y footers.")
```

Si WebFetch devuelve contenido útil → done.

### Tier 2 — curl con headers de navegador
Si WebFetch falla (403, contenido vacío, bot detection):

```bash
curl -s -L \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9,es;q=0.8" \
  -H "Sec-Fetch-Dest: document" \
  -H "Sec-Fetch-Mode: navigate" \
  -H "Sec-Fetch-Site: none" \
  -H "Sec-Fetch-User: ?1" \
  "{url}"
```

Procesar el HTML resultante extrayendo el contenido principal.

### Si ambos fallan
Informar al usuario y sugerir: pegar el contenido manualmente, o usar un servicio de archivo (archive.org, 12ft.io).

---

## Output

Esta skill devuelve el contenido extraído como texto/markdown. No guarda ficheros — eso es responsabilidad de la skill que la invoque (claudia-wisdom, claudia-research) o del usuario.

Cuando se invoca directamente (`/claudia-scrape URL`), mostrar el contenido extraído al usuario en la conversación.

---

## Reglas

1. **No inventar contenido.** Si no puedes extraer algo, dilo. Nunca fabricar texto que no está en la fuente.
2. **Respetar límites.** No hacer más de 50 requests encadenados (threads largos).
3. **Informar del método usado.** Si hubo fallback, mencionarlo brevemente.
4. **URLs privadas/protegidas.** Si la cuenta es privada o el contenido requiere auth, informar al usuario inmediatamente sin intentar múltiples métodos.
5. **Para YouTube, delegar.** No reinventar lo que `yt-transcript` ya hace bien.
6. **Para podcasts, delegar al script.** `podcast_transcribe.py` gestiona toda la cadena (descarga, conversión, transcripción). Claudia solo necesita invocar el script y presentar el resultado.

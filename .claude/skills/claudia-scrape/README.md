# Claudia Scrape — Extraccion de contenido web

Libreria de extraccion de contenido desde URLs. Soporta tweets y threads de X, videos de YouTube (delegando a yt-transcript), y articulos web genericos con escalacion progresiva.

## Que hace

Es la skill de fontaneria que usan wisdom y research para obtener contenido de internet. Tambien se puede usar directamente cuando solo necesitas extraer el texto de una URL sin procesamiento adicional.

Le das una URL y te devuelve el contenido en markdown limpio. Detecta automaticamente el tipo de fuente (tweet, video, articulo) y aplica el handler mas adecuado. No guarda ficheros — solo extrae y devuelve.

## Como usarlo

### Desde conversacion con Claudia

```
/claudia-scrape https://x.com/karpathy/status/1234567890
/claudia-scrape https://x.com/naval/status/9876543210 --full-thread
/claudia-scrape https://www.paulgraham.com/writes.html
/claudia-scrape https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Como libreria (desde otras skills)

Wisdom y research invocan scrape internamente cuando necesitan extraer contenido de una URL. No necesitas hacer nada — la invocacion es automatica.

## Handlers por tipo de URL

### Twitter/X

Usa la API de FxTwitter para extraer tweets, threads y Articles de X.

**Tweet individual:**
```
/claudia-scrape https://x.com/user/status/123456
```
Devuelve: autor, texto, fecha, metricas (likes, RTs, replies, views).

**Thread completo:**
```
/claudia-scrape https://x.com/user/status/123456 --full-thread
```
Camina hacia atras desde el tweet dado hasta encontrar el tweet raiz, recopila todos los tweets del thread y los muestra en orden cronologico. Limite de seguridad: maximo 50 tweets.

Scrape tambien detecta threads automaticamente si el tweet es una self-reply (responde a si mismo).

**Articles de X:**
Contenido largo nativo de X. Se extrae con el mismo flujo que un tweet normal — FxTwitter devuelve el contenido completo.

**Formatos de URL soportados:**
- `x.com/{user}/status/{id}`
- `twitter.com/{user}/status/{id}`
- `fxtwitter.com/{user}/status/{id}`
- `vxtwitter.com/{user}/status/{id}`

**Fallback si FxTwitter falla:**
1. Syndication API (`cdn.syndication.twimg.com`)
2. oEmbed (`publish.twitter.com/oembed`)
3. Si todo falla, informa al usuario

### YouTube

Delega completamente a la skill `claudia-yt-transcript`, que extrae subtitulos del video.

### Web generica (articulos, blogs, newsletters)

Escalacion progresiva en dos tiers:

1. **Tier 1 — WebFetch**: pide el contenido como markdown limpio, ignorando navegacion, sidebars y ads
2. **Tier 2 — curl con headers de navegador**: si WebFetch falla (403, bot detection, contenido vacio), hace curl con User-Agent y headers realistas

Si ambos fallan, sugiere alternativas: pegar el contenido manualmente o usar archive.org / 12ft.io.

## Donde se guarda

En ningun sitio. Scrape es una skill de extraccion pura — devuelve el contenido en la conversacion o a la skill que la invoco. El almacenamiento es responsabilidad de wisdom, research, intake o del usuario.

## Requisitos

- Acceso a internet
- Skill `claudia-yt-transcript` disponible (para URLs de YouTube)
- `curl` instalado (para el fallback Tier 2 de web generica)

## Skills relacionadas

- **claudia-wisdom** — Usa scrape para extraer contenido antes de procesarlo
- **claudia-research** — Usa scrape cuando necesita obtener contenido de URLs especificas durante la investigacion
- **claudia-intake** — El pipeline de intake usa scrape indirectamente (via wisdom) para procesar items de la cola
- **claudia-yt-transcript** — Scrape le delega la extraccion de subtitulos de YouTube

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-scrape/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Al extraer tweets, no muestres las métricas (likes, RTs, views) — solo autor, texto y fecha"
- "Cuando extraigas una URL de X, intenta siempre el thread completo sin necesitar --full-thread"
- "Limita los artículos web a los primeros 3000 caracteres cuando scrape se usa desde wisdom"
- "Añade el idioma detectado del contenido al encabezado del resultado"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **Tweet devuelve 404**: la cuenta puede ser privada o el tweet fue borrado. Scrape prueba los 3 metodos de fallback antes de rendirse
- **FxTwitter rate limit**: si se hacen muchas peticiones seguidas (thread largo), puede saltar rate limit. Esperar unos minutos y reintentar
- **Articulo web devuelve contenido vacio**: algunos sitios bloquean scraping agresivamente. Probar con el Tier 2 (curl) ocurre automaticamente, pero si tambien falla, la alternativa es pegar el texto manualmente
- **Contenido detras de paywall**: scrape no puede saltarse paywalls. Informara de la situacion y sugerira alternativas
- **Thread con mas de 50 tweets**: limite de seguridad. Se extraen los primeros 50 y se avisa al usuario

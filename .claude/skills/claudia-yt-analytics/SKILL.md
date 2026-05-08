---
name: claudia-yt-analytics
description: "Conecta con YouTube Data API + Analytics API, extrae métricas del canal y vídeos, y analiza rendimiento cruzado con el corpus de transcripciones. Usar cuando el usuario pregunte por analíticas de YouTube, rendimiento de vídeos, ideas de contenido basadas en datos, o comparativas."
scope: core
user-invocable: true
argument-hint: "[setup|sync|report|ideas|compare|search ...]"
---

# YouTube Analytics

Skill para extraer, almacenar y analizar métricas de YouTube cruzadas con el corpus de transcripciones del usuario.

## Prerequisitos — comprobar ANTES de cualquier comando

Antes de ejecutar cualquier acción, verifica que el entorno está listo:

1. **Venv existe:**
   ```bash
   test -f .claude/skills/claudia-yt-analytics/venv/bin/activate
   ```
   Si NO existe, créalo:
   ```bash
   python3 -m venv .claude/skills/claudia-yt-analytics/venv
   source .claude/skills/claudia-yt-analytics/venv/bin/activate
   pip install google-auth google-auth-oauthlib google-api-python-client isodate
   ```

2. **Configuración existe:** comprobar que `user/config/settings.json` tiene sección `skill_yt_analytics` con al menos un canal.

3. **Token OAuth existe:** comprobar que `user/credentials/youtube/tokens/<token>.json` existe para el canal configurado.

Si falta el paso 2 o 3, redirigir al usuario a `/yt-analytics setup`. Si solo falta el venv, crearlo silenciosamente e informar al usuario.

## Scripts

Todos en `.claude/skills/claudia-yt-analytics/`:

```bash
# Activar venv primero
source .claude/skills/claudia-yt-analytics/venv/bin/activate

# Auth
python3 .claude/skills/claudia-yt-analytics/auth.py <canal> [--port N] [--no-browser]

# CLI principal
python3 .claude/skills/claudia-yt-analytics/yt_analytics.py --action <action> --channel <canal> [opciones]
```

## Comandos

### `/yt-analytics setup`
Guía al usuario por la configuración completa. Ejecutar los pasos en orden, saltando los que ya estén hechos:

1. **Venv:** comprobar si existe `.claude/skills/claudia-yt-analytics/venv/bin/activate`. Si no:
   ```bash
   python3 -m venv .claude/skills/claudia-yt-analytics/venv
   source .claude/skills/claudia-yt-analytics/venv/bin/activate
   pip install google-auth google-auth-oauthlib google-api-python-client isodate
   ```
2. **Credentials OAuth:** comprobar si existe `user/credentials/youtube/credentials.json`.
   - Si no existe, comprobar `user/credentials/gmail/credentials.json` (se puede reutilizar el mismo proyecto de Google Cloud).
   - Si no hay ninguno, mostrar instrucciones de setup de Google Cloud Console (crear proyecto, habilitar YouTube Data API v3 y YouTube Analytics API, crear credenciales OAuth Desktop app, descargar JSON).
3. **Autorizar canal:** ejecutar `auth.py <canal>` con los flags adecuados según el entorno (headless: `--no-browser --port <puerto>`).
4. **Configuración:** añadir/verificar sección `skill_yt_analytics` en `user/config/settings.json` con `channel_id`, `token` y opcionalmente `workspace`.
5. **Primer sync:** sugerir ejecutar `/yt-analytics sync --full` para poblar la base de datos.

### `/yt-analytics sync`
Sincroniza datos del canal.

1. Si el canal tiene un workspace configurado con corpus.json que incluya fuente YouTube, ejecutar primero:
   ```bash
   python3 .claude/skills/claudia-corpus-sync/sync.py <workspace> --source yt --sync
   ```
2. Ejecutar sync de analytics:
   ```bash
   python3 yt_analytics.py --action sync --channel <canal>
   ```
   Usar `--full` para sync completo o `--since YYYY-MM-DD` para rango específico.
3. Ejecutar corpus-link si hay workspace:
   ```bash
   python3 yt_analytics.py --action corpus-link --channel <canal> --workspace <ws>
   ```
4. Reportar resumen al usuario.

### `/yt-analytics report`
Análisis de rendimiento. Sigue este workflow:

1. Ejecutar `--action overview` para snapshot del canal.
2. Ejecutar `--action trends --period 30d` para momentum reciente.
3. Ejecutar `--action video-stats --top 5 --sort views` para top performers por vistas.
4. Ejecutar `--action video-stats --top 5 --sort ctr` para mejor CTR.
5. Ejecutar `--action video-stats --top 5 --sort subs` para mejor conversión a suscriptores.
6. Ejecutar `--action traffic` para fuentes de tráfico globales.
7. Si hay vídeos con corpus linkeado (`has_corpus: true`):
   - Leer las transcripciones de los 3 mejores y 3 peores vídeos (por vistas relativas al canal).
   - Analizar patrones: estilo de apertura, longitud, tema, estructura.
8. Generar informe estructurado:
   - **Salud del canal**: crecimiento, tendencia, comparativa 7d vs 30d.
   - **Qué funciona**: patrones comunes en los vídeos top, con datos.
   - **Qué no funciona**: patrones en los vídeos de bajo rendimiento.
   - **Recomendaciones**: 3-5 acciones concretas respaldadas por datos.

Si el canal tiene menos de 10 vídeos, simplificar: saltar análisis comparativo y centrarse en métricas absolutas y tendencia.

### `/yt-analytics ideas`
Generación de ideas de contenido basadas en datos.

1. Completar el workflow de report (o usar datos recientes si se ejecutó hace poco).
2. Identificar huecos temáticos:
   - Temas en el corpus/vault que no se han cubierto en vídeo.
   - Temas de vídeos exitosos que se pueden expandir o actualizar.
3. Identificar huecos de formato:
   - Si vídeos largos superan a cortos o viceversa, sugerir el formato infrautilizado.
4. Para cada idea:
   - Título sugerido (basado en CTR de títulos anteriores).
   - Por qué esta idea (dato que la respalda).
   - Formato y duración recomendados.
   - Sugerencia de apertura (basada en qué aperturas correlacionan con retención).
5. Rankear ideas por impacto estimado.

### `/yt-analytics compare`
Comparar vídeos específicos.

```bash
python3 yt_analytics.py --action compare --channel <canal> --videos "id1,id2,id3"
```

### `/yt-analytics search`
Buscar en el catálogo de vídeos por texto.

```bash
python3 yt_analytics.py --action search --channel <canal> --query "texto"
```

## Configuración

En `user/config/settings.json`:

```json
{
  "skill_yt_analytics": {
    "channels": {
      "<nombre>": {
        "channel_id": "<ID del canal>",
        "token": "<nombre del token>",
        "workspace": "<workspace con corpus>"
      }
    },
    "default_channel": "<nombre>",
    "sync_days_back": 90,
    "ignore_shorts": true
  }
}
```

## Datos

- DB SQLite: `user/data/yt-analytics/<channel_id>.db` (una por canal)
- Tokens: `user/credentials/youtube/tokens/<nombre>.json`
- La DB se puede regenerar ejecutando `--action sync --full`

## Personalización

Editar `.claude/skills/claudia-yt-analytics/user/behavior.md` para ajustar:
- Métricas prioritarias en los informes
- Formato de las recomendaciones
- Idioma de los informes
- Criterios para clasificar vídeos como "exitosos" o "bajo rendimiento"

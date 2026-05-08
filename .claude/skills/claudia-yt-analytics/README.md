# Claudia YT Analytics

Conecta con YouTube Data API + Analytics API para extraer métricas del canal y vídeos, almacenarlas localmente en SQLite, y permitir a Claude analizar rendimiento cruzado con el corpus de transcripciones.

## Qué hace

- Descarga metadata de vídeos (título, descripción, tags, duración, fecha)
- Descarga analíticas (vistas, watch time, CTR, retención media, fuentes de tráfico, demografía, suscriptores ganados/perdidos)
- Almacena todo en SQLite local (regenerable, no necesita backup)
- Claude analiza patrones, genera informes y sugiere ideas de contenido
- Opcionalmente cruza métricas con transcripciones del corpus para análisis más profundo

## Setup

Si ya tienes Claudia OS instalada y recibes esta skill vía `/claudia-update`, empieza directamente por el Paso 0 (dependencias) y luego sigue desde el Paso 1. También puedes ejecutar `/yt-analytics setup` y Claude te guiará por todo el proceso.

### Paso 0 — Dependencias

Crea el entorno virtual e instala las dependencias (desde la raíz de tu instalación de Claudia OS):

```bash
python3 -m venv .claude/skills/claudia-yt-analytics/venv
source .claude/skills/claudia-yt-analytics/venv/bin/activate
pip install google-auth google-auth-oauthlib google-api-python-client isodate
```

### Paso 1 — Proyecto de Google Cloud

**Si ya tienes uno (p.ej. para claudia-gmail):**
1. Ve a https://console.cloud.google.com/apis/library
2. Habilita **YouTube Data API v3**
3. Habilita **YouTube Analytics API**
4. Copia tu credentials.json:
   ```bash
   mkdir -p user/credentials/youtube
   cp user/credentials/gmail/credentials.json user/credentials/youtube/
   ```

**Si no tienes proyecto:**
1. Ve a https://console.cloud.google.com/
2. Crea un proyecto nuevo
3. Ve a **APIs & Services > Library** y habilita:
   - YouTube Data API v3
   - YouTube Analytics API
4. Ve a **APIs & Services > OAuth consent screen**:
   - User Type: External
   - Añade scopes: `youtube.readonly`, `yt-analytics.readonly`
   - Añade tu email como usuario de prueba
5. Ve a **APIs & Services > Credentials**:
   - Create Credentials > OAuth client ID
   - Application type: **Desktop app**
   - Descarga el JSON
6. Guárdalo:
   ```bash
   mkdir -p user/credentials/youtube
   mv ~/Downloads/client_secret_*.json user/credentials/youtube/credentials.json
   ```

### Paso 2 — Autorizar tu canal

Desde la raíz de tu instalación de Claudia OS:

**En una máquina con navegador:**
```bash
source .claude/skills/claudia-yt-analytics/venv/bin/activate
python3 .claude/skills/claudia-yt-analytics/auth.py mi-canal
```

**En un servidor headless (VPS):**

Elige un puerto libre (por ejemplo 8766) y abre un túnel SSH desde tu máquina local:
```bash
# En tu máquina local:
ssh -L <puerto>:127.0.0.1:<puerto> usuario@tu-servidor

# En el servidor, desde la raíz de claudia-os:
source .claude/skills/claudia-yt-analytics/venv/bin/activate
python3 .claude/skills/claudia-yt-analytics/auth.py mi-canal --port <puerto> --no-browser
```
Copia la URL que aparece, ábrela en tu navegador local. La redirección llegará al servidor por el túnel.

### Paso 3 — Configurar settings.json

Añade a `user/config/settings.json`:

```json
{
  "skill_yt_analytics": {
    "channels": {
      "mi-canal": {
        "channel_id": "UCxxxxxxxxxxxxxxxxxx",
        "token": "mi-canal",
        "workspace": "mi-workspace"
      }
    },
    "default_channel": "mi-canal",
    "sync_days_back": 90,
    "ignore_shorts": true
  }
}
```

- `channel_id`: lo encuentras en YouTube Studio > Settings > Channel > Advanced, o en la URL de tu canal
- `token`: nombre del fichero de token (sin .json)
- `workspace`: nombre del workspace que tiene tu corpus de transcripciones (opcional)

### Paso 4 — Primer sync

```
/yt-analytics sync --full
```

### Paso 5 — Vincular corpus (opcional)

Si tienes transcripciones en `user/workspaces/<ws>/yt/corpus/`:
```
/yt-analytics sync
```
El sync vincula automáticamente las transcripciones con los datos de analíticas.

## Dónde se guardan los datos

| Qué | Dónde |
|-----|-------|
| OAuth client secrets | `user/credentials/youtube/credentials.json` |
| OAuth tokens | `user/credentials/youtube/tokens/<nombre>.json` |
| Base de datos | `user/data/yt-analytics/<channel_id>.db` |
| Configuración | `user/config/settings.json` > `skill_yt_analytics` |

## Personalización

Edita `.claude/skills/claudia-yt-analytics/user/behavior.md` para ajustar el comportamiento de los informes y análisis.

## Troubleshooting

**"No hay token para X"**: Ejecuta `python3 auth.py <nombre>` para autorizar.

**"Token expirado"**: El token se auto-refresca. Si falla, re-autoriza con `auth.py`.

**Datos vacíos en analytics**: YouTube Analytics API tiene un desfase de ~48h. Los datos del día actual y ayer no están disponibles. Canales muy pequeños pueden no tener datos demográficos o de tráfico.

**Cuota API**: YouTube Data API tiene 10.000 unidades/día. Un sync completo de 100 vídeos gasta ~10 unidades. YouTube Analytics API tiene cuota separada y más generosa.

**La DB se ha corrompido**: Borra el fichero `.db` y ejecuta `--action sync --full` para regenerarla.

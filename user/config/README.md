# settings.json — Referencia de keys

Toda la configuracion de Claudia OS vive en `settings.json`. Cada skill lee su propia seccion. Puedes editar el fichero directamente o pedirle a Claudia que lo haga por ti.

## Keys del sistema

| Key | Tipo | Descripcion |
|-----|------|-------------|
| `timezone` | string | Zona horaria en formato IANA (ej: `Europe/Madrid`). Usada por calendario, briefings y recordatorios |
| `language` | string | Idioma principal (codigo ISO: `es`, `en`, `gl`...) |
| `runtime` | `local` \| `server` | Donde corre Claudia. `local` = ordenador personal, `server` = VPS/nube. Determina como se instalan tareas automaticas |
| `git_sync` | boolean | Si `true`, la sincronizacion git se gestiona via cron. Claudia no hace commit/push manualmente |
| `default_reminder_hour` | number | Hora por defecto para recordatorios sin hora especifica (0-23) |

## Keys de skills

### `skill_briefing`

Configuracion del briefing diario que se envia por Telegram.

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `enabled` | boolean | Activa o desactiva el briefing |
| `schedules` | array | Lista de horarios. Cada uno tiene `name`, `hour`, `minute`, `days` y `sections` |
| `sections` | object | Que incluye cada briefing: `calendar` (agenda) y `tasks` (tareas pendientes) |

### `skill_intake`

Configuracion del pipeline de intake (captura y procesamiento de contenido).

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `expire_days` | number | Dias antes de marcar items de la cola como expirados |

### `gmail_accounts`

Cuentas de email configuradas. Cada key es una direccion de email:

```json
"gmail_accounts": {
  "usuario@gmail.com": {
    "name": "Nombre descriptivo",
    "type": "gmail",
    "token": "nombre_del_token"
  }
}
```

El campo `token` apunta al fichero en `user/credentials/gmail/tokens/<token>.json`.

### `calendar_aliases`

Mapea identificadores de calendario o email a nombres cortos. Compartido por Calendar y Gmail.

```json
"calendar_aliases": {
  "email@ejemplo.com": "Nombre corto",
  "id-largo-de-calendario@group.calendar.google.com": "Familia"
}
```

Los aliases funcionan en dos direcciones: al mostrar datos se usa el nombre corto, y al crear eventos puedes usar el alias en vez del ID completo.

## Otros ficheros en este directorio

| Fichero | Proposito |
|---------|-----------|
| `feeds.json` | Estado de los feeds del intake (URLs pendientes, timestamps). Es mutable — lo actualiza el sistema en cada ejecucion |

## Personalizar

Puedes anadir keys propias para tus extensiones. La convencion es `skill_<nombre>` para config de skills y nombres descriptivos para el resto. Claudia leera cualquier key que le indiques desde aqui.

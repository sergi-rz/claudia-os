# Claudia Gmail — Correo integrado

Gestiona tu correo de Gmail desde Claudia. Lee, busca, organiza, crea borradores y envía emails usando la API de Gmail con autenticación OAuth2.

## Que hace

Claudia tiene acceso completo a tu bandeja de entrada: puede listar correos recientes, buscar por cualquier criterio (remitente, asunto, fecha...), leer mensajes concretos, crear borradores, archivar, etiquetar y enviar. Soporta varias cuentas de Gmail configuradas bajo nombres distintos ("personal", "trabajo", etc.).

El envío directo está disponible en el código (`--action send`) pero **no es el modo por defecto**. Claudia crea borradores por defecto y solo envía cuando `user/context/constraints.md` lo autoriza explícitamente para el contexto actual (por ejemplo, el briefing programado del intake pipeline) o cuando tú lo confirmas en la conversación mostrando el contenido exacto antes de mandarlo. Los borradores son reversibles; los envíos no.

## Como usarlo

### Desde conversacion con Claudia

Pide lo que necesites en lenguaje natural:

- "Mira si tengo correos sin leer"
- "Busca emails de Juan de esta semana"
- "Redacta un borrador para Ana sobre la reunion del martes"
- "Archiva ese correo"

### Comandos directos

```bash
# Listar correos recientes
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action list --max 20

# Solo no leidos
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action list --unread

# Buscar
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action search --query "from:juan subject:factura"

# Leer un mensaje concreto
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action read --id <message_id>

# Crear borrador
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action draft --to "contacto@example.com" --subject "Reunion" --body "Hola..."

# Enviar (sujeto a restricciones)
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action send --to "a@b.com" --subject "Asunto" --body "Texto"

# Archivar
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action archive --id <message_id>

# Etiquetar
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action label --id <message_id> --label "Clientes"

# Ver cuentas configuradas
python3 .claude/skills/claudia-gmail/gmail.py --action accounts
```

## Configuracion

### Paso 1 — Credenciales de Google (una sola vez)

1. Ve a https://console.cloud.google.com/apis/credentials
2. Crea un proyecto (o usa uno existente)
3. Habilita la API de Gmail: APIs & Services > Library > busca "Gmail API" > Enable
4. Configura la pantalla de consentimiento: OAuth consent screen > External > crea
5. Crea credenciales: Create Credentials > OAuth client ID > Desktop app
6. Descarga el JSON y guardalo como `user/credentials/gmail/credentials.json`

### Paso 2 — Autorizar una cuenta

```bash
python3 .claude/skills/claudia-gmail/auth.py personal
```

`auth.py` arranca un servidor loopback en `127.0.0.1`, abre el navegador y captura automáticamente la redirección de Google (flujo oficial "Installed App"; el antiguo OOB de pegar el código a mano ya no se soporta). El token queda guardado en `user/credentials/gmail/tokens/personal.json`.

**En un VPS sin entorno gráfico**, abre un túnel SSH a un puerto fijo desde tu máquina local:

```bash
ssh -L 8765:127.0.0.1:8765 usuario@tu-servidor
# y en el servidor:
python3 .claude/skills/claudia-gmail/auth.py personal --port 8765 --no-browser
```

Copia la URL impresa y ábrela en el navegador local.

Para añadir más cuentas:
```bash
python3 .claude/skills/claudia-gmail/auth.py trabajo
```

### Paso 3 — Dependencias Python

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

El venv de la skill esta en `.claude/skills/claudia-gmail/venv/`. Si existe, los scripts lo usan automaticamente.

## Aliases de contactos

Gmail comparte la key `calendar_aliases` en `user/config/settings.json` con Calendar. Mapea emails a nombres cortos para que los listados sean mas legibles:

```json
{
  "juan@example.com": "Juan",
  "contabilidad@empresa.com": "Gestoria",
  "noreply@github.com": "GitHub"
}
```

Tras el setup inicial, Claudia ofrece configurar aliases revisando tus remitentes recientes.

## Donde se guarda todo

| Que | Donde |
|-----|-------|
| Credenciales OAuth | `user/credentials/gmail/credentials.json` |
| Tokens por cuenta | `user/credentials/gmail/tokens/<nombre>.json` |
| Aliases compartidos | `user/config/settings.json` → `calendar_aliases` |

## Skills relacionadas

- **claudia-intake** — usa Gmail para enviar el briefing diario por email (envio automatico autorizado)
- **claudia-calendar** — comparte los aliases en `settings.json`
- **telegram-bot** — canal alternativo para notificaciones y briefings

## Personalización

Puedes ajustar el comportamiento de esta skill sin tocar los archivos del core (que se actualizan con el sistema). Edita `user/behavior.md` dentro del directorio de la skill:

```
.claude/skills/claudia-gmail/
└── user/
    └── behavior.md   ← tus ajustes van aquí
```

Escribe en lenguaje natural lo que quieres cambiar. Ejemplos:

- "Todos los borradores deben terminar con mi firma estándar (añádela aquí)"
- "Al listar correos, muestra solo los no leídos por defecto"
- "Usa un tono más formal en los borradores dirigidos a dominios de empresa"
- "Al archivar, añade también la etiqueta 'Procesado' automáticamente"

Las instrucciones de `user/behavior.md` tienen preferencia en caso de conflicto con el comportamiento por defecto.

**No modifiques `SKILL.md` directamente** — ese archivo pertenece al core y se sobreescribirá en actualizaciones.

## Troubleshooting

- **Error 403 al enviar**: el token puede haber expirado. Re-ejecuta `python3 auth.py personal` para refrescarlo
- **"credentials.json not found"**: descarga el JSON desde Google Cloud Console y guardalo en `user/credentials/gmail/`
- **No aparecen correos**: comprueba que la cuenta esta autorizada con `--action accounts`
- **Aliases no se muestran**: verifica que `calendar_aliases` en `user/config/settings.json` existe y tiene formato valido

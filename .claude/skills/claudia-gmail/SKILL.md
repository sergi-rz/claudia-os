---
name: claudia-gmail
description: "Lee, busca, organiza, crea borradores y envía correos en Gmail. Usar cuando el usuario pida revisar correo, buscar emails, crear borradores o gestionar su bandeja."
scope: core
user-invocable: true
argument-hint: "[listar|buscar|leer|borrador|...]"
---

# Gmail — Gestión de correo

Gmail API v1 con OAuth2 scope `gmail.modify` (leer, organizar, borradores, envío).

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio. Si tiene contenido, aplícalo como ajustes sobre el comportamiento de esta skill — en caso de conflicto con lo definido aquí, prevalece lo del usuario.

## Uso

Siempre con el venv de la skill (si existe) o python3 del sistema:

```bash
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action list [--max 20] [--unread]
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action read --id <message_id>
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action search --query "from:juan"
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action draft --to "a@b.com" --subject "Re: X" --body "Hola..."
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action archive --id <message_id>
python3 .claude/skills/claudia-gmail/gmail.py --account personal --action label --id <message_id> --label "Clientes"
python3 .claude/skills/claudia-gmail/gmail.py --action accounts
```

## Aliases de contactos

Fichero compartido: `user/config/settings.json` (key `calendar_aliases`, el mismo que usa Calendar). Mapea emails a nombres cortos. En listados y búsquedas, el remitente se muestra con el alias en vez de la dirección completa.

```json
{
  "juan@example.com": "Juan",
  "contabilidad@empresa.com": "Gestoría",
  "noreply@github.com": "GitHub"
}
```

El campo `message_id_header` solo aparece al leer un correo concreto (necesario para reply-to), no en listados.

### Configuración asistida de aliases

Tras completar el setup de Gmail, ofrece al usuario configurar aliases:

1. Ejecuta `gmail.py --account <cuenta> --action list --max 20` para ver remitentes recientes
2. Extrae las direcciones únicas del campo `from`
3. Muestra al usuario: "He encontrado estos remitentes frecuentes: [lista]. ¿Quieres asignar alias a alguno? Así en futuros listados verás el nombre corto en vez del email."
4. Con las respuestas, escribe la key `calendar_aliases` en `user/config/settings.json` (o actualiza si ya existe, respetando entradas previas de Calendar u otras skills)

## Reglas

- **Envío existe pero no es el modo por defecto.** El comando `--action send` está disponible en el código, pero nunca lo uses sin cumplir las dos condiciones:
  1. `user/context/constraints.md` lo autoriza explícitamente para el contexto actual (p.ej. briefings automáticos, intake) o el usuario lo confirma en la conversación.
  2. Has mostrado al usuario el contenido exacto (destinatario, asunto, cuerpo) antes de enviar.
- **Modo seguro por defecto:** crea un borrador (`--action draft`) y pide al usuario que lo revise y envíe desde Gmail. Los borradores siempre son reversibles; un `send` no.
- Cuentas configuradas: ver con `--action accounts`

## Setup (primera vez)

Gmail usa OAuth2, no API keys simples. La configuración tiene dos pasos:

### Paso 1 — Obtener credentials.json (una sola vez)

1. Ve a https://console.cloud.google.com/apis/credentials
2. Crea un proyecto (o selecciona uno existente)
3. Habilita la API de Gmail: APIs & Services → Library → busca "Gmail API" → Enable
4. Configura la pantalla de consentimiento: OAuth consent screen → External → crea
5. Crea credenciales: Create Credentials → OAuth client ID → Desktop app
6. Descarga el JSON y guárdalo como `user/credentials/gmail/credentials.json`

### Paso 2 — Autorizar una cuenta

```bash
python3 .claude/skills/claudia-gmail/auth.py personal
```

`auth.py` arranca un servidor loopback en `127.0.0.1:<puerto>`, abre el navegador y captura el código de Google automáticamente (flujo oficial "Installed App" de Google). El token queda guardado en `user/credentials/gmail/tokens/personal.json`.

**En un VPS sin entorno gráfico**, abre antes un túnel SSH hacia un puerto fijo desde tu máquina local:

```bash
ssh -L 8765:127.0.0.1:8765 usuario@tu-servidor
# y en el servidor:
python3 .claude/skills/claudia-gmail/auth.py personal --port 8765 --no-browser
```

Copia la URL impresa y ábrela en el navegador local. La redirección `http://127.0.0.1:8765/?code=…` llegará al servidor remoto por el túnel.

Puedes autorizar varias cuentas con nombres distintos:
```bash
python3 .claude/skills/claudia-gmail/auth.py trabajo
```

### Dependencias Python

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

Sin credentials.json, el script `auth.py` mostrará instrucciones al ejecutarse.

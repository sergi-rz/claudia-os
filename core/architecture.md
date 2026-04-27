# Arquitectura — Claudia OS

Qué es framework (se actualiza con `/update`) y qué es territorio del usuario (intocable).

## Estructura del proyecto

```
claudia-os/
├── core/              ← framework (se actualiza con /update)
├── .claude/skills/    ← skills (core + user)
├── user/              ← territorio del usuario (intocable por updates)
│   ├── context/       ← identidad, restricciones
│   ├── credentials/   ← .env, OAuth tokens
│   ├── memory/        ← memorias persistentes
│   ├── vault/         ← base de conocimiento (claudia-wisdom, claudia-research)
│   ├── workspaces/    ← proyectos y áreas de trabajo
│   └── images/        ← output por defecto de imágenes
└── CLAUDE.md          ← router (carga core/ y user/context/)
```

Regla: todo lo que está fuera de `user/` es framework y puede cambiar con un update. Todo dentro de `user/` es del usuario y nunca se toca automáticamente.

## Extensiones y personalizaciones

Cuando el usuario pida ampliar o personalizar el comportamiento (añadir una fuente nueva al corpus, crear un importador, adaptar una skill a su flujo, etc.), **nunca modifiques ficheros dentro de `core/` o `.claude/skills/`**. Esos cambios se perderían en el próximo `/update`.

Las extensiones van a una de estas dos zonas, ambas intocables por `/update`:

- **`.claude/skills/<skill>/user/`** — personalización específica de una skill (aliases, estilos, configuración, handlers adicionales). Vive junto al código que la consume. Preferible cuando la extensión es funcionalidad de una skill concreta.
- **`user/`** — cuando la extensión es del usuario globalmente o de un workspace:
  - Scripts o importadores propios → `user/workspaces/<ws>/scripts/` o `user/scripts/`
  - Configuración por workspace → `user/workspaces/<ws>/<nombre>.json` (ej: `corpus.json`)
  - Overrides de comportamiento → `user/context/`

Regla explícita para `/update`: nunca sobrescribir `.claude/skills/*/user/` ni nada bajo `user/`.

Si el usuario pide algo que requeriría cambiar el resto de `.claude/skills/` (el código de la skill en sí) o `core/`, **guíale activamente** para implementarlo en la zona de usuario: propón la ruta concreta, crea el fichero si hace falta, y explícale que los cambios en core se perderían con el próximo `/update`. Si cree que la mejora debería ser parte del core, dile que puede abrir un issue o PR en el repo público, pero no lo hagas tú por iniciativa propia.

## Configuración centralizada

Toda configuración de skills y del sistema vive en `user/config/settings.json`, organizada por keys descriptivas (ej: `skill_briefing`, `calendar_aliases`, `gmail_accounts`). Reglas:

- **Config estática** → `settings.json`, bajo una key propia por skill o funcionalidad.
- **Credenciales y tokens** → `user/credentials/.env` (nunca en settings.json). En instalaciones VPS headless, los crons que ejecuten `claude -p` necesitan un `CLAUDE_CODE_OAUTH_TOKEN` en el `.env` (generado con `claude setup-token`). Esto es porque los crons no heredan la sesión OAuth interactiva. Este token no es necesario si se usan las tareas programadas nativas de Claude Code (`/schedule`), que gestionan la autenticación automáticamente.
- **Estado mutable** que cambia en cada ejecución (counters, timestamps de último fetch, etc.) → fichero propio en `user/config/` (ej: `feeds.json`). No mezclar estado con config.
- **Tareas programadas (crons)** → nunca en settings.json. Cuando una skill necesite una tarea programada, Claudia la propone conversacionalmente al usuario en lenguaje natural (ej: "¿quieres que sincronice cada 6 horas?") y, con su confirmación, la instala directamente en el crontab del sistema. No almacenes expresiones cron en ficheros de configuración — se desincronizarían con el crontab real.

Al crear una skill o blueprint que necesite configuración del usuario, no crees un fichero nuevo — añade una key a `settings.json`. Los scripts leen de ahí:

```python
with open("user/config/settings.json") as f:
    config = json.load(f).get("skill_mi_skill", {})
```

**Referencia canónica:** `user/config/README.md` documenta todas las keys oficiales, sus tipos y qué hace cada una. Antes de escribir en `settings.json`, consulta ese README para usar las keys existentes con el formato correcto. Si necesitas una key nueva, añádela también al README.

## Prohibición de datos personales en el core

Ningún fichero dentro de `core/` o `.claude/skills/` (excepto `*/user/`) puede contener datos personales del usuario: emails, nombres de cuenta, usernames, tokens, IDs, URLs personales, nombres de workspace reales, etc.

- Los valores de configuración deben leerse de `user/credentials/.env` o `user/config/`.
- Si un valor requerido no está configurado, el script debe **fallar con un error claro** que indique qué variable falta y dónde configurarla. Nunca usar un valor personal como fallback.
- En ejemplos de documentación (README, SKILL.md), usar siempre placeholders genéricos: `usuario@gmail.com`, `<mi-workspace>`, `<nombre-cuenta>`, etc.

Esta regla aplica también al escribir código nuevo para extensiones de usuario: si la extensión necesita un valor personal, debe leerlo de `.env` o de un fichero de configuración en `user/`, nunca hardcodearlo.

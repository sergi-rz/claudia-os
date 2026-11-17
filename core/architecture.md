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
│   ├── vault/         ← base de conocimiento (wisdom, research). Índice SQLite en .index/ (gitignored, regenerable)
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

### Memoria por workspace

Cada workspace puede tener su memoria viva en `user/workspaces/<ws>/memory/MEMORY.md`:
estado actual del proyecto, decisiones (con fecha y porqué) y gotchas específicos.
Es distinta de la memoria global (`user/memory/`): aquí va solo lo que importa dentro
de ese proyecto, no lecciones transversales ni contenido (el contenido va al vault).

El disparador de mantenerla vive en el `CLAUDE.md` del propio workspace —que se carga
automáticamente al trabajar ahí—, no en `core/`. Así la instrucción llega en el contexto
correcto y funciona también en local, sin depender del cron nocturno.

## Skills privadas

Una skill puede marcarse como privada creando un fichero `.private` en su raíz (ej: `.claude/skills/mi-skill/.private`). El contenido es libre (puede describir por qué es privada, o estar vacío).

Efecto:
- `scripts/reset-test-install.sh` detecta automáticamente los `.private` markers y excluye esas skills al copiar al repo público.
- Una verificación post-copia aborta si alguna skill privada se cuela al target.
- Para crear una skill privada nueva: crear la skill normalmente en `.claude/skills/` y añadir un fichero `.private` en su raíz.

Si el usuario pide algo que requeriría cambiar el resto de `.claude/skills/` (el código de la skill en sí) o `core/`, **guíale activamente** para implementarlo en la zona de usuario: propón la ruta concreta, crea el fichero si hace falta, y explícale que los cambios en core se perderían con el próximo `/update`. Si cree que la mejora debería ser parte del core, dile que puede abrir un issue o PR en el repo público, pero no lo hagas tú por iniciativa propia.

## Configuración centralizada

Toda configuración de skills y del sistema vive en `user/config/settings.json`, organizada por keys descriptivas (ej: `skill_briefing`, `calendar_aliases`, `gmail_accounts`). Reglas:

- **Config estática** → `settings.json`, bajo una key propia por skill o funcionalidad.
- **Credenciales y tokens** → `user/credentials/.env` (nunca en settings.json). En instalaciones VPS headless, los crons que ejecuten `claude -p` necesitan un `CLAUDE_CODE_OAUTH_TOKEN` en el `.env` (generado con `claude setup-token`). Esto es porque los crons no heredan la sesión OAuth interactiva. En la app de escritorio no hace falta: ahí no se usa `claude -p` (ver *Tareas programadas*).
- **Estado mutable** que cambia en cada ejecución (counters, timestamps de último fetch, etc.) → fichero propio en `user/config/` (ej: `feeds.json`). No mezclar estado con config.
- **Tareas programadas** → nunca en settings.json. Ver la sección *Tareas programadas*.

Al crear una skill o blueprint que necesite configuración del usuario, no crees un fichero nuevo — añade una key a `settings.json`. Los scripts leen de ahí:

```python
with open("user/config/settings.json") as f:
    config = json.load(f).get("skill_mi_skill", {})
```

**Referencia canónica:** `user/config/README.md` documenta todas las keys oficiales, sus tipos y qué hace cada una. Antes de escribir en `settings.json`, consulta ese README para usar las keys existentes con el formato correcto. Si necesitas una key nueva, añádela también al README.

## Tareas programadas

Cuando una skill necesite ejecutarse sola, Claudia se lo propone al usuario en lenguaje natural
(«¿quieres que lo revise cada mañana?») y, con su confirmación, la programa ella. El usuario no
tiene que abrir una terminal ni editar nada. No guardes horarios en ficheros de configuración: se
desincronizarían con la tarea real.

El cómo depende de dónde vive la instalación. Si no lo sabes, pregúntalo:

| Dónde | Cómo se programa | Límites |
|---|---|---|
| **Servidor** (VPS, equipo siempre encendido) | Crontab del sistema | Los crons que lanzan `claude -p` necesitan `CLAUDE_CODE_OAUTH_TOKEN` en el `.env` |
| **Ordenador del usuario con la app de escritorio de Claude** | Tarea programada de la app (en la barra lateral, *Programadas*): un prompt, una carpeta y un horario | Solo corre con la app abierta y el ordenador despierto |
| **Ordenador del usuario sin la app** (solo terminal) | Cron en Linux, LaunchAgent en macOS o el Programador de tareas de Windows | Solo corre con el ordenador encendido |

Las **rutinas en la nube** (`/schedule`) no sirven para esto: corren sobre un clon limpio del repo,
sin los ficheros, el vault ni las credenciales del usuario.

### En la app de escritorio

- **Créala tú** con la herramienta de tareas programadas de la sesión, si la tienes. Si no, dale al
  usuario el prompt, la carpeta y el horario exactos para que la cree en *Programadas* con un clic.
- **Si ya hay una tarea para lo mismo, corrígela** en vez de crear otra: dos tareas con el mismo
  trabajo se pisan.
- **El prompt es una instrucción completa:** cada ejecución abre una sesión nueva, sin la
  conversación en la que se creó. Di qué comandos ejecutar, en qué orden y qué hacer si uno falla.
- **El trabajo de modelo lo hace el agente de la tarea, nunca `claude -p`.** `claude -p` usa la
  sesión del CLI, no la de la app: en un equipo que solo usa la app puede no estar instalado, o
  tener la sesión caducada. Si un script lanza `claude -p` en el cron del servidor, necesita un modo
  en el que esa parte la haga el agente (por ejemplo, `--prepare` y `--save` en `claudia-intake`).
- **Que no se pare pidiendo permisos.** Si una ejecución pide un permiso, se queda esperando a
  alguien que no está. Guarda la tarea en modo de permisos *Auto*. Las reglas `permissions.allow`
  de `.claude/settings.local.json` son la alternativa, pero en modo automático el agente no puede
  escribir sus propios permisos (se bloquea, y está bien que sea así): si hacen falta, dale al
  usuario las reglas exactas, por ejemplo `Bash(python3 .claude/skills/<skill>/<script>.py:*)`.
- **Pruébala al crearla** con *Ejecutar ahora* y comprueba que termina sin pedir nada. Si no
  puedes lanzarla tú (los permisos pueden bloquearlo), pide al usuario que pulse *Ejecutar ahora*
  en *Programadas* y que compruebe ahí que el modo de permisos es *Auto*. La
  conversación en la que la creaste no recibe aviso cuando acaba: para ver cómo fue, abre la sesión
  de esa ejecución en *Programadas* o comprueba sus resultados en disco.
- La app desplaza la hora unos minutos para repartir carga: una tarea de las 11:00 puede salir a
  las 11:13.
- **Ejecuciones perdidas:** si el ordenador estaba dormido o la app cerrada, la ejecución se salta.
  Al volver, la app lanza una sola recuperación por tarea (la más reciente de los últimos siete días).
  Una skill programada debe tolerarlo: no duplicar si corre dos veces y no perder nada si se salta
  unos días.
- Elige horas en las que el ordenador suele estar encendido (media mañana mejor que de madrugada).

Cada skill dice en su `SKILL.md` qué hay que programar, cada cuánto y con qué comandos; el cómo es
siempre esta sección.

## Prohibición de datos personales en el core

Ningún fichero dentro de `core/` o `.claude/skills/` (excepto `*/user/`) puede contener datos personales del usuario: emails, nombres de cuenta, usernames, tokens, IDs, URLs personales, nombres de workspace reales, etc.

- Los valores de configuración deben leerse de `user/credentials/.env` o `user/config/`.
- Si un valor requerido no está configurado, el script debe **fallar con un error claro** que indique qué variable falta y dónde configurarla. Nunca usar un valor personal como fallback.
- En ejemplos de documentación (README, SKILL.md), usar siempre placeholders genéricos: `usuario@gmail.com`, `<mi-workspace>`, `<nombre-cuenta>`, etc.

Esta regla aplica también al escribir código nuevo para extensiones de usuario: si la extensión necesita un valor personal, debe leerlo de `.env` o de un fichero de configuración en `user/`, nunca hardcodearlo.

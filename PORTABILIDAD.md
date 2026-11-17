# Portabilidad — usar Claudia OS con otros agentes

Claudia OS viene preparado para **Claude Code**. Este documento explica qué hay que cambiar
para que funcione con **Codex**, **OpenCode** u otro agente de terminal que lea `AGENTS.md`.

La conversión son tres cambios estructurales y ninguno toca el contenido de las instrucciones
ni de las skills. Es reversible.

> **Si eres el agente leyendo esto:** puedes aplicar la conversión completa siguiendo la
> sección [Conversión](#conversión). Antes de empezar, avisa al usuario de que vas a crear
> symlinks y pregúntale si trabaja en Windows, porque ahí el paso 1 cambia.

---

## Por qué hace falta convertir

Cada agente busca sus instrucciones en un fichero distinto:

| Agente | Fichero de instrucciones | Skills |
|--------|--------------------------|--------|
| Claude Code | `CLAUDE.md` | `.claude/skills/` |
| Codex | `AGENTS.md` | `.agents/skills/` |
| OpenCode | `AGENTS.md` | `.claude/skills/` |

Claudia OS se distribuye con `CLAUDE.md` porque es el entorno para el que está pensado. La
conversión consiste en que **el contenido pase a vivir en `AGENTS.md`** y que `CLAUDE.md` se
convierta en un puntero, de forma que los tres agentes lean el mismo texto y no haya dos
fuentes que se desincronicen.

La regla general: **el contenido real vive en el fichero que más agentes leen de forma nativa,
y el que se queda fuera recibe un enlace.** Con las instrucciones el impar es Claude Code (no
lee `AGENTS.md`), así que `CLAUDE.md` es el enlace. Con las skills el impar es Codex (Claude
Code y OpenCode ya descubren `.claude/skills/`), así que el enlace es `.agents/skills`. Por eso
las dos flechas apuntan en sentidos opuestos.

---

## Conversión

### Paso 1 — `AGENTS.md` como fuente, `CLAUDE.md` como symlink

Claudia OS tiene un `CLAUDE.md` en la raíz y otro en varias carpetas (`user/vault/`, y uno por
workspace si los has creado). Hay que convertirlos todos.

```bash
find . -name CLAUDE.md -not -path './.git/*' -not -path '*/node_modules/*' | sort -r |
while read -r f; do
  d=$(dirname "$f")
  mv "$f" "$d/AGENTS.md"
  ln -s AGENTS.md "$d/CLAUDE.md"
done
```

El `sort -r` no es decorativo: procesa las rutas más profundas primero, para que ningún symlink
quede apuntando a un `AGENTS.md` que todavía no existe.

**Por qué un symlink y no un import `@AGENTS.md`.** Claude Code admite importar otro fichero
escribiendo `@AGENTS.md` dentro de `CLAUDE.md`, y parece la opción limpia. No lo es: si arrancas
Claude Code dentro de un subdirectorio, el `CLAUDE.md` de la raíz se carga como ancestro y su
import resuelve *fuera* del working directory. Claude pide entonces aprobación para imports
externos, y **si la declinas, los imports quedan desactivados de forma permanente y sin volver
a preguntar**: las instrucciones raíz se pierden en silencio, sin ningún error. Un symlink no
es un import y no dispara ese diálogo.

#### Windows

Crear symlinks en Windows exige **Modo Desarrollador activado** o permisos de administrador.
Si no lo tienes, usa el import como alternativa: en lugar del `ln -s`, crea un `CLAUDE.md` cuyo
contenido sea una sola línea.

```
@AGENTS.md
```

Acepta el diálogo de imports externos la primera vez que aparezca. Si lo declinas por error,
tendrás que reactivar los imports para recuperar las instrucciones.

Ten en cuenta además que **git en Windows materializa los symlinks como ficheros de texto**
salvo que actives `core.symlinks`. Si clonas un repo convertido en una máquina Windows sin esa
opción, tu `CLAUDE.md` acabará siendo un fichero cuyo contenido es literalmente la palabra
`AGENTS.md` — y Claude lo cargará como si fuesen tus instrucciones. Es un fallo silencioso:
no da ningún error, simplemente el asistente deja de saber quién eres.

### Paso 2 — Exponer las skills a Codex

Codex busca las skills en `.agents/skills/`. En vez de mover nada, se enlaza:

```bash
mkdir -p .agents
ln -s ../.claude/skills .agents/skills
```

Claude Code y OpenCode siguen leyendo `.claude/skills/`, que no se ha movido. Fíjate en que
`.agents` es un directorio normal y solo `skills` dentro de él es el symlink.

### Paso 3 — Ampliar el límite de contexto de Codex

Codex trunca la cadena de `AGENTS.md` a **32 KiB por defecto**. Al encadenarse raíz + workspace
+ subproyecto es fácil superarlo, y cuando ocurre Codex corta las instrucciones sin avisar.
Crea `.codex/config.toml`:

```toml
# El encadenado AGENTS.md (raíz + workspace + subproyecto) puede superar el límite
# por defecto de 32 KiB de Codex; ampliamos el margen para no truncar instrucciones.
project_doc_max_bytes = 65536
```

Para saber si te afecta, suma la cadena que se carga en tu workspace más profundo:

```bash
find . -name AGENTS.md -not -path './.git/*' -exec wc -c {} +
```

---

## Verificar que ha funcionado

```bash
# 1. Ningún CLAUDE.md debe ser un fichero real: todos symlinks (0 = correcto)
find . -name CLAUDE.md -type f -not -path './.git/*' -not -path '*/node_modules/*' | wc -l

# 2. Ningún symlink roto (sin salida = correcto)
find . -xtype l -not -path './.git/*' -not -path '*/node_modules/*'

# 3. El symlink de skills resuelve
readlink -f .agents/skills
```

En Windows con el fallback de import, el punto 1 devolverá el número de ficheros `CLAUDE.md`
en lugar de 0. Es lo esperado: comprueba entonces que cada uno contiene solo `@AGENTS.md`.

Después, arranca cada agente y pídele que te diga quién eres. Si responde con tu contexto
personal, está leyendo las instrucciones. Pídele también que liste sus skills: deben ser las
que tengas en `.claude/skills/`, **sin duplicados**.

---

## Qué NO se convierte

Lo siguiente es específico de Claude Code y no tiene equivalente automático. Nada de esto
rompe la instalación: son capacidades que dejarás de tener, no errores.

**`.claude/settings.json` y `.claude/statusline.sh`.** Codex y OpenCode los ignoran. Si usas
la variable `CLAUDIA_ADVANCED_MEMORY`, tendrás que exportarla en tu shell.

**Tareas programadas de la app.** Las tareas programadas de la app de escritorio de Claude no
existen en los demás. La app de escritorio de Codex tiene las suyas (sin probar con Claudia); con
la CLI de Codex u OpenCode no hay, así que usa cron (Linux), un LaunchAgent (macOS) o el
Programador de tareas de Windows. Esto solo aplica si trabajas en local: en una instalación de
servidor ya estabas usando cron, y sigue funcionando igual. Ver *Tareas programadas* en
`core/architecture.md` y [VPS.md](VPS.md).

**`claudia-intake` en modo batch.** El procesamiento por lotes invoca el CLI `claude -p` desde
Python para sintetizar el wisdom. Si no tienes el CLI de Claude instalado, ese modo no
funciona — la skill sigue sirviendo desde la conversación. Para portarlo, sustituye la llamada
en `intake_process.py` por el equivalente de tu agente (`codex exec`, `opencode run`) y ajusta
el parseo de la respuesta, que espera JSON.

**`claudia-research` en niveles `standard` y `deep`.** Lanza tres sub-agentes en paralelo. Si
tu agente no tiene una capacidad equivalente, ejecutará las tres perspectivas en secuencia
dentro de la misma conversación: el resultado es parecido, tarda más. El nivel `quick` no se
ve afectado.

**Skills que dependen de búsqueda web o lectura de URLs** (`claudia-research`, `claudia-scrape`,
`claudia-wisdom`). Están escritas describiendo la capacidad, no el nombre de la herramienta, así
que funcionan con cualquier agente que la tenga. Si el tuyo no la trae, `claudia-scrape` cae a
`curl` por su cuenta, pero la búsqueda web no tiene alternativa.

---

## Notas por agente

Los tres pasos se han verificado con **Codex 0.153.0** y **OpenCode 1.18.18**. En ambos, las
skills se descubrieron correctamente y **sin duplicados**. Las notas siguientes cubren lo que
puede cambiar en otras versiones.

### Codex

Necesita los tres pasos. Con el symlink del paso 2 descubre las skills del proyecto y activa la
correcta a partir de su `description`, sin que haya que nombrarla.

Si en tu versión aparecieran duplicadas, significa que está leyendo `.claude/skills` y
`.agents/skills` como dos fuentes distintas. Entonces el symlink sobra:

```bash
rm .agents/skills
```

### OpenCode

Lee `AGENTS.md` y descubre `.claude/skills/` de forma nativa: le basta con el paso 1. Verás
alguna skill de más respecto a Codex, pero no son duplicados — son las tuyas de usuario y las
nativas de OpenCode.

Si en tu versión sí salieran duplicadas las del proyecto, arranca con:

```bash
OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1 opencode
```

### Otros agentes

Cualquiera que lea `AGENTS.md` funcionará con el paso 1. Para las skills, mira dónde las busca
y añade un symlink a `.claude/skills` igual que en el paso 2.

---

## Volver a Claude Code

La conversión se deshace con el paso inverso: el `AGENTS.md` vuelve a ser el `CLAUDE.md` real y
el symlink desaparece.

```bash
find . -name AGENTS.md -not -path './.git/*' -not -path '*/node_modules/*' | sort -r |
while read -r f; do
  d=$(dirname "$f")
  rm -f "$d/CLAUDE.md"
  mv "$f" "$d/CLAUDE.md"
done
rm -rf .agents .codex
```

Recomendable hacerlo si vas a compartir el repositorio con alguien que use Windows, por el
problema de los symlinks descrito en el paso 1.

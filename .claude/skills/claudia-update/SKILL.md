---
name: claudia-update
description: "Actualiza el framework de Claudia OS desde el repo canónico sergi-rz/claudia-os, protegiendo todo el territorio del usuario (user/, .claude/skills/*/user/). Uso: /claudia-update"
user-invocable: true
---

# claudia-update

## Qué hace

Sincroniza la instalación local con la última versión del framework publicada en `sergi-rz/claudia-os`. Nunca toca el territorio del usuario.

**Territorio del usuario — intocable:**
- `user/` — todo, sin excepciones
- `.claude/skills/*/user/` — personalizaciones de skills
- `.claude/settings.json`, `.claude/settings.local.json`
- Blueprints en `blueprints/` que no existan en el repo canónico (son del usuario)

**Territorio del framework — actualizable:**
- `core/`
- `.claude/skills/<skill>/` (excepto `*/user/`)
- `CLAUDE.md`
- `scripts/`
- `blueprints/_template/` + blueprints que vengan del canónico
- Documentos raíz: `README.md`, `ROADMAP.md`, `PHILOSOPHY.md`, `CONTRIBUTING.md`, `ATTRIBUTION.md`, `SECURITY.md`, `CLAUDIA_OS_OVERVIEW.md`, `VPS.md`

## Invocación

- `/claudia-update` — comprueba y aplica actualizaciones
- `/claudia-update --check` — muestra qué cambiaría sin aplicar nada

## Repositorio canónico

```
Remote:  upstream
URL:     https://github.com/sergi-rz/claudia-os.git
Branch:  main
```

## Flujo

### Paso 1 — Preparar remote upstream

1. Comprueba si existe el remote `upstream`:
   ```
   git remote get-url upstream
   ```
2. Si no existe, añádelo:
   ```
   git remote add upstream https://github.com/sergi-rz/claudia-os.git
   ```
3. Fetch:
   ```
   git fetch upstream
   ```

### Paso 2 — Detectar cambios en el framework

Ejecuta:
```
git diff --stat HEAD upstream/main -- core/ .claude/skills/ CLAUDE.md scripts/ blueprints/ README.md ROADMAP.md PHILOSOPHY.md CONTRIBUTING.md ATTRIBUTION.md SECURITY.md CLAUDIA_OS_OVERVIEW.md VPS.md
```

Si no hay cambios: _"Tu instalación ya está al día con el framework."_ Para.

### Paso 3 — Detectar cambios locales no commiteados en el framework

Ejecuta:
```
git status --porcelain -- core/ CLAUDE.md scripts/
```

Si hay ficheros del framework con cambios locales sin commitear, avisa antes de continuar:

```
⚠ Tienes cambios locales en ficheros del framework que serían sobreescritos:
  <lista de ficheros>

Estos cambios no están en el repo canónico. Se perderán con el update.
¿Deseas continuar de todos modos, o prefieres commitear o stashear primero?
```

Espera OK explícito. Sin OK, para.

### Paso 4 — Mostrar resumen de cambios

Muestra un resumen legible organizado por categoría. Para skills, distingue entre *actualizada* y *NUEVA*. Ejemplo de formato:

```
Actualizaciones disponibles desde sergi-rz/claudia-os:

Framework:
  core/memory.md          modificado
  core/behavior.md        modificado

Skills:
  .claude/skills/claudia-wisdom/SKILL.md    actualizada
  .claude/skills/claudia-nueva/             NUEVA

Documentos raíz:
  README.md               modificado
  ROADMAP.md              modificado

Tu carpeta user/ no se toca. Tus personalizaciones en */user/ tampoco.
```

Si el usuario invocó con `--check`: para aquí. No apliques nada.

### Paso 5 — Confirmar

Pregunta:
> "¿Aplico estas actualizaciones? Los cambios quedarán sin commitear para que puedas revisarlos antes."

Espera OK explícito. Sin OK, para.

### Paso 6 — Aplicar actualizaciones

Aplica en este orden:

**6a. Core, CLAUDE.md, scripts y documentos raíz:**
```
git checkout upstream/main -- core/ CLAUDE.md scripts/ README.md ROADMAP.md PHILOSOPHY.md CONTRIBUTING.md ATTRIBUTION.md SECURITY.md CLAUDIA_OS_OVERVIEW.md VPS.md
```

**6b. Skills — con exclusión explícita de `*/user/`:**
```
git checkout upstream/main -- .claude/skills/ ":(exclude).claude/skills/*/user/"
```

Si el shell reporta que la sintaxis `:(exclude)` no es soportada, haz el checkout skill a skill:
```
git checkout upstream/main -- .claude/skills/<skill>/
```
Y para cada skill que tuviera un subdirectorio `user/` local: restáuralo inmediatamente con:
```
git checkout HEAD -- .claude/skills/<skill>/user/
```

**6c. Blueprints — solo los del canónico, sin eliminar los del usuario:**

Obtén la lista de blueprints en upstream:
```
git ls-tree --name-only upstream/main blueprints/
```

Para cada blueprint de upstream (excepto `README.md` como fichero suelto):
```
git checkout upstream/main -- blueprints/<nombre>/
```

No elimines ni modifiques blueprints locales que no aparezcan en esa lista.

### Paso 7 — Confirmar resultado

Ejecuta:
```
git diff --stat HEAD
git status --porcelain
```

Muestra al usuario:
- Ficheros actualizados
- Skills nuevas (si las hay)
- Rollback disponible: `git checkout HEAD -- .`
- _"Revisa los cambios con `git diff HEAD` antes de commitear."_

## Reglas invariantes

1. **Nunca commitear.** El usuario decide cuándo.
2. **`user/` es sagrado.** Ningún fichero bajo `user/` puede ser tocado, creado ni eliminado.
3. **`*/user/` en skills es sagrado.** Si `git checkout` lo sobreescribe, restáuralo de inmediato.
4. **Sin OK explícito en Paso 5, no hay Paso 6.**
5. **Si `upstream/main` no existe, parar con mensaje claro.** No mostrar errores git crudos.
6. **Blueprints locales no en upstream: no tocar.** Son del usuario.
7. **No eliminar skills locales.** Una skill que esté en local pero no en upstream podría ser del usuario.

---
name: claudia-blueprint
description: "Aplica un blueprint de Claudia OS a la instancia del usuario, siguiendo los 7 pasos del formato. Busca el blueprint primero en la carpeta local blueprints/, y si no existe lo descarga del repo canónico sergi-rz/claudia-os. Uso: /claudia-blueprint <nombre>."
user-invocable: true
---

# claudia-blueprint

## Qué hace

Orquesta la aplicación de un blueprint (recipe declarativo de 7 pasos) contra la instancia local del usuario. La lógica de qué instalar vive en cada `blueprint.md`; esta skill sólo encadena los pasos, gestiona la descarga del repo canónico cuando el blueprint no está en local, y refuerza las reglas del formato (OK gates, nunca commitear, revertir si quedan marcadores vivos).

Pensado para que el usuario pueda leer un tuit tipo _"he publicado una nueva funcionalidad, instálala con `/claudia-blueprint <nombre>`"_ y aplicarla en un solo comando.

## Invocación

- `/claudia-blueprint <nombre>` — aplica el blueprint llamado `<nombre>`.
- `/claudia-blueprint` (sin argumento) — lista los blueprints disponibles en local y para.

## Repositorio canónico

```
URL:        https://github.com/sergi-rz/claudia-os
Branch:     main
Base raw:   https://raw.githubusercontent.com/sergi-rz/claudia-os/main/blueprints/
```

Nota: hasta que se publique la v1 del template, el repo está vacío. Si un blueprint no está en local y la descarga devuelve 404, la skill avisa: _"El blueprint `<nombre>` no existe todavía en el repo canónico (la v1 aún no está publicada). Tráelo manualmente a `blueprints/<nombre>/` antes de aplicarlo."_ y para.

## Flujo

### 0. Resolver blueprint

1. Si no hay argumento:
   - Lista `blueprints/*/blueprint.md` en el repo local (excluye `_template/`).
   - Muestra nombres + `description` de cada frontmatter.
   - Para. No sigas al Paso 1.

2. Si hay argumento `<nombre>`:
   - Comprueba si existe `blueprints/<nombre>/blueprint.md` en local.
   - Si **sí existe**: úsalo. Salta al Paso 1.
   - Si **no existe**: intenta descargarlo del repo canónico (ver subsección siguiente).

### 0b. Descarga desde el repo canónico

Cuando el blueprint no está en local:

1. Avisa: _"El blueprint `<nombre>` no está en local. Voy a descargarlo de `sergi-rz/claudia-os`. ¿OK?"_ Espera confirmación.

2. Con OK, usa **WebFetch** para descargar `https://raw.githubusercontent.com/sergi-rz/claudia-os/main/blueprints/<nombre>/blueprint.md`.
   - Si 404: para y avisa: _"No existe `<nombre>` en el repo canónico (puede que aún no esté publicado — la v1 del template está pendiente). Blueprints disponibles en local: <lista del Paso 0.1>."_
   - Si no es markdown válido: para y avisa.

3. Parsea el frontmatter para leer el manifest `assets:`.

4. Por cada entrada `source:`, descarga `https://raw.githubusercontent.com/sergi-rz/claudia-os/main/blueprints/<nombre>/<source>`. Si alguna falla, para — no apliques un blueprint incompleto.

5. Escribe todo el árbol en local (`blueprints/<nombre>/blueprint.md` + assets).

6. Avisa: _"Blueprint descargado a `blueprints/<nombre>/`. Queda rastro en git para auditoría y re-aplicación."_

A partir de aquí el blueprint vive en local como si el usuario lo hubiera escrito él mismo. El flujo continúa igual que si ya estuviera.

### 1. Paso 1 — Metadatos

Lee el frontmatter de `blueprints/<nombre>/blueprint.md`. Valida:

- Campos obligatorios presentes: `name`, `version`, `scope`, `toca`, `reversibilidad`, `riesgo`.
- Si `assets:` existe, cada entrada tiene `source` y `target`.
- Cada `source` referenciado existe como fichero en `blueprints/<nombre>/`.

Si falta algo, para y avisa con el campo concreto.

Muestra al usuario un resumen corto: nombre, versión, qué toca, riesgo declarado. Pregunta: _"¿Procedemos con Discovery?"_ Espera OK.

### 2. Paso 2 — Discovery

Lee la sección `## Paso 2 — Discovery` del `blueprint.md`. Ejecuta cada punto **como lectura pasiva** (Read, Glob, Grep — nada de escrituras). Para cada fuente descrita:

- Intenta localizar en la instancia del usuario la ruta/formato real.
- Registra: existe / no existe / formato detectado.

Construye un mapa `{fuente: estado_real}` que usarás en el Paso 3.

### 3. Paso 3 — Propuesta adaptada + confirmación

Genera un mensaje con **las fuentes reales detectadas**, no las genéricas del blueprint:

```
He revisado tu instancia. Propongo aplicar <nombre> v<version>:

Fuentes reales detectadas que la skill usará:
  - <solo las que existen, con su formato real>

Fuentes del blueprint genérico que NO aplican aquí:
  - <lista, o "ninguna">

Voy a crear:
  - <target> de cada asset
  - <directorios adicionales que el blueprint declare>

No voy a tocar nada existente.

¿OK, o ajustamos?
```

**Espera OK explícito.** Si el usuario redirige, ajusta y vuelve a pedir OK. No pases al Paso 4 sin confirmación.

### 4. Paso 4 — Pre-flight

Lee la sección `## Paso 4 — Pre-flight` del blueprint y ejecuta los checks declarados. Como mínimo:

- `git status --porcelain -- <rutas-del-blueprint>` vacío. Si no: para y pide al usuario commitear o stashear esas rutas.
- No hay merge/rebase en curso (`.git/MERGE_HEAD`, `.git/REBASE_HEAD` no existen).
- Los `target` de los assets no existen todavía (si existieran, el blueprint los sobreescribiría — requiere confirmación extra del usuario).

Cambios sin commit en **otras rutas** del repo: avisar pero no bloquear.

### 5. Paso 5 — Cambios

Por cada entrada del manifest `assets:`:

1. Lee `blueprints/<nombre>/<source>`.
2. Busca marcadores `<!-- ADAPTAR: ... -->` (y variantes `# ADAPTAR:`, `// ADAPTAR:`).
3. Por cada marcador:
   - Muestra al usuario contexto (5-10 líneas alrededor) y el valor propuesto basado en Discovery.
   - Pide OK o valor alternativo.
4. Sustituye todos los marcadores por los valores confirmados.
5. Crea el directorio padre de `target` si no existe.
6. Escribe el resultado en `target`. Aplica `mode` con `chmod` si está declarado.
7. **Verificación post-escritura:** grep `ADAPTAR` sobre `target`. Si devuelve alguna línea, revierte (borra el fichero escrito) y para con error — el blueprint tiene un bug.

Ejecuta también los pasos adicionales declarados en el `blueprint.md` (crear directorios vacíos con `.gitkeep`, mover ficheros, etc.).

### 6. Paso 6 — Post

**Nunca commitees.**

Ejecuta:
- `git status`
- `git diff --stat HEAD -- <rutas-del-blueprint>`

Muestra al usuario:
- Qué ficheros se añadieron.
- Comando de rollback: el declarado en el frontmatter `reversibilidad`.
- Mensaje de commit sugerido: `feat: add <nombre> skill via blueprint v<version>` (o lo que el blueprint declare explícitamente en Paso 6).

### 7. Paso 7 — Verificación

Lee la sección `## Paso 7 — Verificación` del blueprint y ejecuta los checks declarados. Si el blueprint pide invocar una skill recién creada, hazlo. Reporta cada check como pasado o fallado.

Si algún check falla: **para**. No declares el blueprint aplicado. Sugiere al usuario revisar la salida y decidir si rollback o fix manual.

Si todos pasan: _"Blueprint `<nombre>` v<version> aplicado y verificado. Recuerda commitear cuando revises el diff."_

## Reglas invariantes

1. **Nunca commitear.** El usuario commitea cuando él quiere.
2. **OK gate en Paso 3 es obligatorio.** Sin OK explícito, no hay Paso 4.
3. **Marcadores `ADAPTAR` vivos tras escritura = bug.** Siempre revertir.
4. **Fallo en cualquier paso = parar.** No intentes auto-reparar.
5. **Blueprints sin frontmatter válido no se aplican.** Valida antes de empezar.
6. **Descargas de GitHub se guardan siempre en local** (`blueprints/<nombre>/`), para que el usuario tenga rastro auditable y pueda re-aplicar offline.

## Notas

- Esta skill es el único cliente oficial para aplicar blueprints. Ver `blueprints/README.md` para la guía de autoría.
- Si el usuario quiere aplicar un blueprint desde un fork o rama distinta, tendrá que clonarlo manualmente a `blueprints/<nombre>/` antes de invocar `/claudia-blueprint <nombre>`. No se soporta override de URL por comando (principio de mínima superficie).

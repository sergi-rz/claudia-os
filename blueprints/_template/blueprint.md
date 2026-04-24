<!--
  Template de blueprint — guía de uso: blueprints/README.md.

  Instrucciones para el creador:
  1. Copia esta carpeta como blueprints/<nombre>/
  2. Sustituye cada bloque <!-- ADAPTAR: ... --> por contenido real.
  3. Añade los ficheros plantilla que necesite el blueprint en assets/
     y decláralos en el frontmatter bajo `assets:`.
  4. Borra este comentario de cabecera antes de publicar.
  5. Aplica el blueprint contra tu instancia real antes de mergear.
-->

---
name: <!-- ADAPTAR: nombre-kebab-case -->
version: 0.1.0
scope: <!-- ADAPTAR: core | addon -->
toca: <!-- ADAPTAR: lista de rutas que va a crear o modificar, separadas por coma -->
reversibilidad: <!-- ADAPTAR: comando de rollback concreto, ej. "rm -rf .claude/skills/<nombre>" -->
riesgo: <!-- ADAPTAR: bajo | medio | alto — con una línea justificando -->
assets:
  # - source: assets/SKILL.md
  #   target: .claude/skills/<nombre>/SKILL.md
  # - source: assets/script.sh
  #   target: .claude/skills/<nombre>/script.sh
  #   mode: "0755"        # opcional, si el fichero debe ser ejecutable
---

# Blueprint: <!-- ADAPTAR: nombre -->

<!-- ADAPTAR: 2-3 frases que expliquen qué instala este blueprint y qué problema resuelve.
     Esto es lo primero que lee el usuario para decidir si le interesa aplicarlo. -->

---

## Paso 1 — Metadatos

Ver frontmatter arriba.

<!-- ADAPTAR: notas relevantes sobre madurez de este blueprint (prototipo, estable, etc.) -->

---

## Paso 2 — Discovery

Antes de proponer nada al usuario, lee y toma nota. **No actúes — solo observa.**
Describe conceptos, no rutas fijas. Para cada fuente, indica formatos candidatos y deja claro que el runtime debe detectar el real.

1. **Skills existentes** — lista `.claude/skills/*/SKILL.md`. Comprueba que no existe ya una skill llamada `<!-- ADAPTAR: nombre de la skill a instalar -->`. Si existe, para y avisa al usuario.

2. **<!-- ADAPTAR: fuente concreta — ¿qué concepto buscas? -->**
   - Rutas candidatas: <!-- ADAPTAR: lista -->
   - Formatos candidatos: <!-- ADAPTAR: ej. "YYYY-MM.md, *.jsonl, o subcarpetas" -->
   - Si no existe en esta instancia, regístralo como "ausente" — no supongas.

<!-- Añade más entradas de Discovery según necesite el blueprint. Mínimo: una por fuente de datos que la skill vaya a leer, más una por dependencia (credenciales, skills hermanas, proceso pm2, etc.). -->

Al terminar, tienes un mapa del entorno real del usuario. Ese mapa alimenta el Paso 3.

---

## Paso 3 — Propuesta adaptada + confirmación

Muestra al usuario un resumen **adaptado a lo que encontraste en Discovery**. No uses plantillas con fuentes que no existen en su caso.

Estructura sugerida:

```
He revisado tu instancia. Propongo:

**Fuentes reales detectadas que la skill leerá:**
- <lista adaptada, solo lo que existe>

**Fuentes del blueprint genérico que NO aplican aquí:**
- <lista, o "ninguna">

**Voy a crear:**
- <ruta>
- <ruta>

**No voy a tocar** nada existente.

¿OK, o ajustamos (excluir fuentes, cambiar rutas, renombrar)?
```

**Espera OK explícito.** Si el usuario redirige, ajusta y vuelve a pedir OK.

---

## Paso 4 — Pre-flight

Comprueba solo las rutas que el blueprint va a tocar. No exijas árbol git completo limpio.

**Bloquear y parar si:**
- `git status --porcelain -- <rutas-del-blueprint>` devuelve cualquier línea (hay cambios sin commit en rutas que vamos a tocar).
- Hay un merge o rebase en curso (`.git/MERGE_HEAD` o `.git/REBASE_HEAD` existen).
- <!-- ADAPTAR: dependencias específicas: credenciales, comandos disponibles, permisos, etc. -->

**Avisar pero no bloquear si:**
- Hay cambios sin commit en otras rutas del repo. Recuérdale al usuario que para rollback limpio debería commitear o stashear sus cambios antes. Él decide.

---

## Paso 5 — Cambios

Aplicar los assets declarados en el frontmatter y cualquier paso adicional que el blueprint requiera.

Para cada entrada en `assets:`:

1. Lee el fichero en `<blueprint-dir>/<source>`.
2. Localiza todos los marcadores `<!-- ADAPTAR: ... -->` (y equivalentes en otros lenguajes: `# ADAPTAR:`, `// ADAPTAR:`).
3. Para cada marcador, muéstrale al usuario el contexto (5-10 líneas alrededor) y el dato detectado en Discovery que propones usar. Pide OK o ajuste.
4. Sustituye los marcadores por los valores confirmados.
5. Escribe el resultado en `<target>`. Si el `mode` está declarado, aplícalo con `chmod`.
6. Si al terminar queda algún marcador `<!-- ADAPTAR -->` vivo en el fichero escrito, es un bug — revertir y parar.

Pasos adicionales específicos del blueprint (crear directorios, mover ficheros, etc.):

<!-- ADAPTAR: lista ordenada si aplica, o "ninguno" -->

---

## Paso 6 — Post

**No commitees nada.** Los blueprints se aplican, se revisan, y commitea el usuario.

- Muestra `git status` para que el usuario vea qué se añadió.
- Muestra `git diff --stat HEAD -- <rutas-del-blueprint>` (el diff completo solo bajo petición).
- Recuerda al usuario:
  - **Rollback:** `<!-- ADAPTAR: comando concreto, típicamente "rm -rf <ruta1> <ruta2>" -->`
  - **Commit cuando conforme:** `<!-- ADAPTAR: mensaje de commit sugerido -->`

---

## Paso 7 — Verificación

Lista de checks concretos (no genéricos):

1. <!-- ADAPTAR: acción end-to-end — ej. "Invoca /<skill>" -->
2. Comprueba que:
   - <!-- ADAPTAR: check verificable 1 — ruta creada, output con formato correcto, etc. -->
   - <!-- ADAPTAR: check verificable 2 -->
   - <!-- ADAPTAR: check verificable 3 -->
3. Si algún check falla, para y debug antes de dar el blueprint por aplicado.

---

## Notas para iterar (opcional)

<!-- ADAPTAR: deja aquí aprendizajes observados en las primeras aplicaciones
     que deban alimentar la siguiente versión de este blueprint.
     Borra esta sección cuando el blueprint esté estable. -->

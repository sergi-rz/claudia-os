---
name: weekly-review
version: 0.2.0
scope: addon
toca: .claude/skills/weekly-review/, user/vault/weekly-reviews/
reversibilidad: rm -rf .claude/skills/weekly-review/ user/vault/weekly-reviews/
riesgo: bajo — solo crea ficheros nuevos, no modifica nada existente
assets:
  - source: assets/SKILL.md
    target: .claude/skills/weekly-review/SKILL.md
---

# Blueprint: weekly-review

Instala una skill `/weekly-review` que lee la actividad de los últimos 7 días del usuario (tareas, ideas, aprendizajes episódicos) y genera un fichero de revisión semanal en `user/vault/weekly-reviews/YYYY-WW.md`.

Pensado para invocación manual los viernes o cuando el usuario pida un cierre de semana.

---

## Paso 1 — Metadatos

Ver frontmatter arriba.

Versión 0.2.0: segundo formato del blueprint (carpeta + assets/). La primera versión (0.1.0) usó markdown único con la plantilla embebida y se aplicó el 2026-04-21.

---

## Paso 2 — Discovery

Antes de proponer nada al usuario, lee y toma nota. **No actúes — solo observa.**

1. **Skills existentes** — lista `.claude/skills/*/SKILL.md`. Comprueba que no existe ya una skill llamada `weekly-review`. Si existe, para y avisa.

2. **Tareas del usuario** — ¿dónde registra el usuario tareas hechas/pendientes?
   - Rutas candidatas: `user/workspaces/_me/notes/tasks.md`, `user/tasks.md`, o cualquier fichero con secciones tipo `## Completadas`, `## Pendientes`, `## Proyectos`.
   - Detecta la ruta real y las secciones que usa. Si no hay nada, regístralo como ausente.

3. **Ideas capturadas** — ¿hay un canal donde el usuario anota ideas?
   - Rutas candidatas: `user/workspaces/_me/notes/ideas.md`, `user/ideas.md`, o similar.
   - Si existe pero vacío, regístralo; no es error.

4. **Memoria episódica / aprendizajes** — ¿existe algún canal con eventos o aprendizajes timestamped?
   - Rutas candidatas: `user/memory/episodes/` (YYYY-MM.md, *.jsonl, o subcarpetas), `user/memory/AGENT_LEARNINGS.jsonl`, o similar.
   - Detecta el formato real que use esta instancia. Si es JSONL, comprueba que los registros tienen timestamp parseable.

5. **Logs por workspace** — ¿cada workspace tiene un directorio de logs?
   - Rutas candidatas: `user/workspaces/*/logs/` con ficheros `YYYY-MM-DD.md` u otro formato.
   - Registra qué workspaces los tienen y cuáles no.

6. **Identidad y tono** — lee `user/context/identity.md` si existe. Solo para guía de tono en el output, no como dato.

7. **Vault de revisiones previas** — comprueba `user/vault/weekly-reviews/`. Si existe y tiene ficheros, **lee el más reciente** para respetar convención de formato previa.

Al terminar tienes un mapa de qué fuentes existen en esta instancia y cuáles no. Ese mapa alimenta el Paso 3.

---

## Paso 3 — Propuesta adaptada + confirmación

Muestra al usuario un resumen con las fuentes reales detectadas, no con la plantilla genérica:

```
He revisado tu instancia. Propongo:

**Fuentes reales detectadas que la skill leerá:**
- <lista adaptada, solo lo que existe>

**Fuentes del blueprint genérico que NO aplican aquí:**
- <lista, o "ninguna">

**Voy a crear:**
- .claude/skills/weekly-review/SKILL.md
- user/vault/weekly-reviews/ (si no existe)

**No voy a tocar** nada existente.

¿OK, o ajustamos (excluir fuentes, cambiar rutas, renombrar)?
```

**Espera OK explícito.** Si el usuario redirige, ajusta y vuelve a pedir OK.

---

## Paso 4 — Pre-flight

**Bloquear y parar si:**
- `git status --porcelain -- .claude/skills/weekly-review/ user/vault/weekly-reviews/` devuelve cualquier línea.
- Hay un merge o rebase en curso.
- `.claude/skills/weekly-review/` ya existe (colisión — no fue detectada en Discovery).

**Avisar pero no bloquear si:**
- Hay cambios sin commit en otras rutas del repo. Recuérdale al usuario que para rollback limpio debería commitear o stashear antes. Él decide.

---

## Paso 5 — Cambios

1. Crear directorio `.claude/skills/weekly-review/`.

2. Aplicar el asset `assets/SKILL.md` → `.claude/skills/weekly-review/SKILL.md`:
   - Localiza el bloque `<!-- ADAPTAR: ... -->` en la sección `## Fuentes`.
   - Sustitúyelo por la lista real detectada en Discovery. Para cada fuente real, una línea con ruta + qué se lee de ella. Añade una sección al final sobre fuentes del blueprint genérico que NO aplican en esta instancia (si procede).
   - Escribe el resultado. Si al terminar queda algún marcador `<!-- ADAPTAR -->` vivo, revertir.

3. Crear directorio `user/vault/weekly-reviews/` con un `.gitkeep` vacío si no existe.

---

## Paso 6 — Post

**No commitees nada.** Los blueprints se aplican, se revisan, y commitea el usuario.

- Muestra `git status`.
- Muestra `git diff --stat HEAD -- .claude/skills/weekly-review/ user/vault/weekly-reviews/`.
- Recuerda al usuario:
  - **Rollback:** `rm -rf .claude/skills/weekly-review/ user/vault/weekly-reviews/`
  - **Commit cuando conforme:** `feat: add weekly-review skill via blueprint v0.2.0`

---

## Paso 7 — Verificación

1. Invoca `/weekly-review`.
2. Comprueba:
   - Se crea `user/vault/weekly-reviews/YYYY-WW.md` con el número de semana ISO correcto.
   - El contenido menciona datos reales de al menos una fuente con actividad en la ventana de 7 días.
   - Las fuentes ausentes o vacías aparecen listadas bajo "Fuentes no disponibles esta semana" — sin fallo ruidoso.
   - Los cuatro bloques (Hecho / Pendiente / Patrones / Próxima semana) están presentes.
3. Si algún check falla, para y debug antes de dar el blueprint por aplicado.

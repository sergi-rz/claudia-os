# Blueprints — guía de autoría

## Qué es un blueprint

Una receta aplicable por prompt que instala funcionalidad nueva en la instancia de un usuario de Claudia OS. No es código ejecutable directo: es una carpeta con una especificación markdown (`blueprint.md`) de 7 pasos y los ficheros plantilla (`assets/`) que un Claude runtime lee, adapta al entorno concreto del usuario, y escribe.

La filosofía subyacente: Claudia OS se distribuye como template editorial, no como software mantenido. Las mejoras viajan como blueprints que cada usuario aplica a su propia instancia cuando le interesan. La divergencia entre instancias es el comportamiento esperado, no un fallo.

## Reparto de roles

| Rol | Qué hace |
|---|---|
| **Maintainer** | Escribe blueprints nuevos cuando detecta funcionalidad compartible entre usuarios |
| **Usuario final** | Aplica blueprints que le interesen con `/claudia-blueprint <nombre>`. **No escribe blueprints** — si necesita algo específico, crea la skill directamente en su propia instancia |

Esto implica que los blueprints deben estar diseñados para la **diversidad de entornos del usuario**. Un blueprint que asume que existe X o Y falla silenciosamente en instancias que no los tienen. Por eso los pasos Discovery y Propuesta adaptada son centrales.

## Estructura de un blueprint

Cada blueprint es una carpeta:

```
blueprints/
  <nombre>/
    blueprint.md          # especificación de 7 pasos + frontmatter con manifest
    assets/               # ficheros plantilla que el blueprint copia a la instancia
      SKILL.md
      script.sh           # scripts, configs, cualquier fichero no trivial
```

El frontmatter de `blueprint.md` declara qué assets copiar y dónde:

```yaml
assets:
  - source: assets/SKILL.md
    target: .claude/skills/<nombre>/SKILL.md
  - source: assets/script.sh
    target: .claude/skills/<nombre>/script.sh
    mode: "0755"          # opcional: permisos si el fichero debe ser ejecutable
```

El runtime lee cada `source`, procesa los marcadores `<!-- ADAPTAR: ... -->` (ver Paso 5), y escribe el resultado en `target`.

## Los 7 pasos

### 1. Metadatos

Frontmatter con nombre, versión, qué rutas toca, comando exacto de rollback, nivel de riesgo (bajo / medio / alto), y el manifest de assets.

### 2. Discovery

Leer el entorno del usuario **antes** de decidir nada. Cada entrada de Discovery describe *qué concepto buscar* y *qué formatos son candidatos*, con instrucción explícita de detectar el formato real que use esa instancia.

```
Bien:
  4. Memoria episódica — ¿existe algún canal de eventos con timestamp?
     Rutas candidatas: user/memory/episodes/ (YYYY-MM.md, *.jsonl, o subcarpetas).
     Detecta el formato real que use el usuario.

Mal:
  4. Memoria episódica — comprueba si existe user/memory/episodes/YYYY-MM.md
```

Nunca asumas estructura — pregunta por concepto y adapta.

### 3. Propuesta adaptada + confirmación

Mostrar al usuario un resumen **con las fuentes reales detectadas en Discovery**, no con la plantilla genérica del blueprint. No menciones fuentes que no existan en su instancia.

Pedir OK explícito antes de tocar nada. Si el usuario redirige, ajustar y volver a pedir OK.

### 4. Pre-flight

Checks defensivos **solo sobre las rutas que el blueprint va a tocar**, no sobre el árbol completo. Exigir árbol limpio global es ruido en repos de uso activo y la regla acaba ignorada.

```
Bloquear si:
- git status --porcelain -- <rutas-del-blueprint> no está vacío
- hay merge o rebase en curso
- faltan credenciales o dependencias declaradas en Paso 1

Avisar pero no bloquear si:
- hay cambios sin commit en otras rutas (recordar al usuario que para rollback
  limpio debería commitear o stashear sus cambios antes)
```

### 5. Cambios

Para cada entrada del manifest `assets:` del frontmatter:

1. Leer el fichero en `<blueprint-dir>/<source>`.
2. Localizar todos los marcadores `<!-- ADAPTAR: ... -->` (o `# ADAPTAR:`, `// ADAPTAR:` según lenguaje).
3. Mostrar al usuario contexto (5-10 líneas alrededor) y el valor detectado en Discovery que se propone usar. Pedir OK o ajuste por marcador.
4. Sustituir los marcadores por los valores confirmados.
5. Escribir el resultado en `<target>`. Aplicar `mode` si está declarado.
6. Si al terminar queda algún `<!-- ADAPTAR -->` vivo en un fichero escrito, es un bug — revertir.

Pasos adicionales específicos (crear directorios vacíos, mover ficheros, etc.) se listan explícitamente en el `blueprint.md` después del bloque de assets.

### 6. Post

**Claude nunca commitea.** Los blueprints se aplican, se revisan, y commitea el usuario.

- Mostrar `git status` y `git diff --stat HEAD -- <rutas-del-blueprint>`.
- Recordar al usuario: comando de rollback concreto y mensaje de commit sugerido.

### 7. Verificación

Probar end-to-end con checks **verificables** (ruta creada, output con formato correcto, skill responde), no genéricos ("funciona sin fallar"). Si algún check falla, parar y debug antes de dar el blueprint por aplicado.

## Cómo escribir un blueprint nuevo

1. Copia `_template/` → `<nombre>/` en `blueprints/`.
2. Rellena `blueprint.md`. Cada `<!-- ADAPTAR -->` indica qué personalizar.
3. Añade los ficheros plantilla en `<nombre>/assets/` y decláralos en el frontmatter bajo `assets:`.
4. Pasa el checklist de abajo.
5. Aplícalo contra tu instancia **antes** de mergear. Si no pasa tu propio dogfood, no pasa el del usuario.
6. Commit: `feat(blueprints): add <nombre> blueprint v0.1.0 (sin aplicar)`.
7. Aplicación y verificación en commit separado si procede.

## Checklist antes de mergear

- [ ] **Discovery** describe conceptos, no rutas fijas. Cada fuente menciona formatos candidatos y pide detectar el real.
- [ ] **Propuesta adaptada** muestra fuentes reales detectadas, no la plantilla genérica. No menciona fuentes que Discovery no encontró.
- [ ] **Pre-flight** comprueba solo rutas del blueprint, no árbol completo.
- [ ] **Assets** declarados en frontmatter tienen marcadores `<!-- ADAPTAR -->` en los campos que deben adaptarse, y nada hardcodeado que debería ser adaptable.
- [ ] **Paso 6** explicita "Claude no commitea" y da rollback de rutas concretas.
- [ ] **Paso 7** lista checks verificables, no genéricos.
- [ ] **Riesgo declarado** en frontmatter es realista.
- [ ] **Dogfooded** al menos una vez contra una instancia real.

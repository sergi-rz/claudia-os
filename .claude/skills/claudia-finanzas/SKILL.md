---
name: claudia-finanzas
description: "Análisis de gastos familiares: importa extractos bancarios, categoriza movimientos con reglas, enriquece con detalle de merchants, y genera dashboards."
scope: core
user-invocable: true
argument-hint: "import <file> | categorizar | enrich <merchant> | dashboard | regenerar | rules | status"
---

# Finanzas — Análisis inteligente de gastos

Importa extractos bancarios (CSV), categoriza automáticamente cada movimiento, enriquece con detalle de merchants (Amazon, etc.), y genera dashboards visuales.

> **Personalización:** antes de ejecutar, lee `user/behavior.md` en este directorio, si existe. Si tiene contenido, aplícalo como ajustes — en caso de conflicto con lo definido aquí, prevalece lo del usuario. Si el usuario pide un ajuste permanente de la skill, guárdalo ahí: crea el fichero si no existe (`behavior.example.md` tiene ideas).

## First-run: bootstrap automático

Al ejecutar cualquier comando `/claudia-finanzas`, comprobar si existe `user/workspaces/claudia-finanzas/rules.yaml`.

**Si NO existe** (primer uso):
1. Crear `user/workspaces/claudia-finanzas/` con estructura completa:
   ```
   user/workspaces/claudia-finanzas/
   ├── rules.yaml            ← copiado de templates/rules_template.yaml
   ├── CLAUDE.md             ← copiado de templates/workspace.md
   ├── data/extractos/
   ├── data/enrichments/
   └── dashboard/
       └── index.html        ← copiado de templates/dashboard.html
   ```
2. Mensaje de bienvenida:
   ```
   Workspace de finanzas creado. Estructura lista.

   Para empezar:
   1. Pega un extracto bancario CSV aquí o ejecuta /claudia-finanzas import <ruta_al_csv>
   2. Ejecuta /claudia-finanzas categorizar para clasificar movimientos

   Las reglas de categorización están en user/workspaces/claudia-finanzas/rules.yaml.
   Puedes editarlas manualmente o dejar que se actualicen durante la categorización.
   ```
3. No pedir entrevista ni configuración. Sin preguntas. Bootstrap silencioso.

**Si SÍ existe** → ejecutar comando normal.

## Workspace y formato canónico

### Directorio de trabajo

```
user/workspaces/claudia-finanzas/
├── rules.yaml              ← reglas de categorización (extractos + enrichment_patterns de productos)
├── CLAUDE.md
├── data/
│   ├── extractos/          ← CSVs normalizados (un fichero por año: 2024.csv, 2025.csv)
│   ├── extractos_raw/      ← originales sin tocar, tal como los subió el usuario
│   └── enrichments/        ← desglose de merchants y tickets (formato unificado)
└── dashboard/
    ├── index.html          ← dashboard HTML
    └── data.json           ← datos generados por pipeline
```

**`extractos_raw/`** almacena los ficheros originales del usuario (CSV, Excel, etc.) como backup. Nombrado: `{año}_{banco}_{fecha_import}.{ext}` (ej: `2026_bbva_20260524.xlsx`). Permite regenerar los normalizados si cambia el formato canónico o hay un error en la normalización.

### Formato CSV canónico

```csv
fecha,concepto,importe,saldo,categoria,movimiento,observaciones
2026-01-03,Mercadona 1234,-67.82,5432.10,alimentacion/supermercado,Pago con tarjeta,4940XXXX MERCADONA
```

- `fecha`: YYYY-MM-DD
- `concepto`: nombre del merchant o descripción
- `importe`: positivo = ingreso, negativo = gasto
- `saldo`: saldo tras el movimiento
- `categoria`: clave de rules.yaml (formato `main/sub`, e.g. `restaurantes/cafes_desayunos`)
- `movimiento`: tipo de movimiento del banco (pago con tarjeta, transferencia, etc.)
- `observaciones`: datos adicionales del banco (número de tarjeta, referencia, etc.)

## Pipeline Python

Los scripts están en `.claude/skills/claudia-finanzas/pipeline/`.

**Invocación:**
```bash
python3 .claude/skills/claudia-finanzas/pipeline/merge_extract.py <workspace> <new_csv>
python3 .claude/skills/claudia-finanzas/pipeline/categorize.py <workspace> [--recat]
python3 .claude/skills/claudia-finanzas/pipeline/generate.py <workspace>
python3 .claude/skills/claudia-finanzas/pipeline/insights.py <workspace>
python3 .claude/skills/claudia-finanzas/pipeline/enrich_products.py <workspace> <enrichment_csv>
python3 .claude/skills/claudia-finanzas/pipeline/match_enrichments.py <workspace> <enrichment_csv>
python3 .claude/skills/claudia-finanzas/pipeline/reconcile_enrichments.py <workspace>
```

- `merge_extract.py` — mergea CSV normalizado con extractos existentes, dedup por (fecha,concepto,importe), output JSON con {new, duplicates, total, years_affected}
- `categorize.py` — aplica rules.yaml + enrichments a CSVs, output JSON con {matched, uncategorized, total, updated}. Enrichments con categorías mixtas (tickets con varios productos) no sobreescriben la categoría del extracto. Flag `--recat`: re-evalúa todos los movimientos contra las reglas actuales (útil tras añadir o modificar patterns/thresholds). Enrichments siguen teniendo prioridad; movimientos sin match en rules mantienen su categoría existente.
- `generate.py` — lee CSVs categorizados + enrichments → genera data.json con `enrichment_breakdown` para analytics detallados
- `insights.py` — analiza data.json → añade campos insights y alerts
- `enrich_products.py` — categoriza productos de enrichments contra `rules.yaml (sección `enrichment_patterns`)` (determinista, sin IA)
- `match_enrichments.py` — cruza enrichments con extracto por fecha±5d + importe±0.02€, asigna status (matched/provisional/unmatched)
- `reconcile_enrichments.py` — reconcilia enrichments provisionales tras importar nuevo extracto, reporta transiciones y unmatched para revisión

El pipeline completo es: import (IA) → merge → reconcile → categorize → generate → insights.

## Comandos

### `/claudia-finanzas import <file>`

Importa un extracto de **cualquier formato** y lo normaliza al CSV canónico usando IA.

El usuario puede subir CSV de cualquier banco, Excel (.xlsx), texto pegado en el chat, o cualquier formato legible. La IA interpreta la estructura y genera el CSV canónico. Los scripts Python downstream siempre reciben el mismo formato.

**Flujo:**

**Paso 0 — Guardar original:**

Copiar el fichero original (sin modificar) a `data/extractos_raw/` con nombre descriptivo: `{año}_{banco}_{fecha_import}.{ext}`. Si el usuario pega texto inline, guardar como `.txt`. Crear el directorio si no existe.

**Paso 1 — Leer el fichero:**
- `.xlsx`/`.xls` → convertir a texto con openpyxl (ya en venv):
  ```bash
  source .claude/skills/claudia-finanzas/venv/bin/activate && python3 -c "
  import openpyxl, sys
  wb = openpyxl.load_workbook(sys.argv[1])
  ws = wb.active
  for row in ws.iter_rows(values_only=True):
      print('\t'.join(str(c) if c is not None else '' for c in row))
  " <ruta_fichero>
  ```
- `.csv`/`.txt` → leer directamente. Si hay problemas de encoding (caracteres rotos), convertir primero: `iconv -f ISO-8859-1 -t UTF-8 <fichero>`
- Texto inline → el usuario lo pega directamente en el chat, Claude lo lee del mensaje

**Paso 2 — Normalizar (IA):**

Claude interpreta el contenido y genera un CSV normalizado. Reglas de normalización:
- **Fechas**: convertir a YYYY-MM-DD (detectar formato del banco: DD/MM/YYYY, DD-MM-YYYY, etc.)
- **Importes**: punto decimal, sin separador de miles, sin símbolo €. Ejemplo: `1.234,56 €` → `1234.56`
- **Signo**: gastos/cargos = negativo, ingresos/abonos = positivo
- **Columnas cargo/abono separadas** (común en ING, BBVA, Bankinter): combinar en una sola columna `importe` (cargo como negativo, abono como positivo)
- **Filas de metadatos** (cabeceras del banco, resúmenes, totales): ignorar, solo extraer filas de movimientos
- **`categoria`**: dejar SIEMPRE vacía (la rellena categorize.py)
- **`movimiento`**: mapear de la columna del banco que describa el tipo de operación (pago con tarjeta, transferencia, etc.). Si no existe, dejar vacío
- **`observaciones`**: mapear de columnas adicionales del banco (referencia, número de tarjeta, detalle ampliado). Si no existe, dejar vacío
- **`saldo`**: mapear si existe en el banco. Si no, dejar vacío

Escribir el CSV normalizado a `/tmp/extracto_normalized.csv` con las 7 columnas canónicas.

**Paso 3 — Validar con el usuario:**

Mostrar las primeras 5 filas normalizadas en formato tabla para que el usuario confirme que la normalización es correcta. Esperar confirmación antes de continuar.

**Paso 4 — Mergear (determinista):**
```bash
source .claude/skills/claudia-finanzas/venv/bin/activate && python3 .claude/skills/claudia-finanzas/pipeline/merge_extract.py <workspace> /tmp/extracto_normalized.csv
```
Dedup automático por (fecha, concepto, importe). Agrupa por año en `data/extractos/{año}.csv`.

**Paso 5 — Reconciliar enrichments provisionales:**
```bash
source .claude/skills/claudia-finanzas/venv/bin/activate && python3 .claude/skills/claudia-finanzas/pipeline/reconcile_enrichments.py <workspace>
```
Re-evalúa todos los enrichments `provisional` contra los extractos actualizados. Posibles transiciones:
- `provisional` → `matched` — el extracto confirma el movimiento. Informar al usuario.
- `provisional` → `unmatched` — el extracto cubre la fecha pero no hay match. Presentar lista al usuario con tres opciones por item:
  1. **Vincular manualmente** — el usuario indica a qué movimiento del extracto corresponde
  2. **Aprobar sin match** — mantener como gasto válido sin correspondencia bancaria (otra tarjeta, efectivo, etc.)
  3. **Descartar** — eliminar el enrichment (error de entrada, duplicado, etc.)

Para vincular manualmente: buscar movimientos cercanos en fecha (±10d) y mostrar candidatos. Si el usuario elige uno, actualizar `fecha_extracto` e `importe_total` en el enrichment y cambiar status a `matched`.

Para aprobar sin match: cambiar status a `approved` (se trata como `matched` en analytics).

Para descartar: eliminar las filas del enrichment CSV.

Si no hay provisionales o no hay transiciones, saltar este paso silenciosamente.

**Paso 6 — Pipeline:**

Ejecutar categorize → generate → insights. Mostrar resumen: X movimientos nuevos, Y duplicados descartados, Z categorizados, W pendientes.

### `/claudia-finanzas categorizar`

Categorización asistida interactiva para movimientos sin categoría.

**Flujo:**
1. Ejecutar `categorize.py` para aplicar reglas automáticas
2. Leer CSVs y recoger movimientos con `categoria` vacía
3. Agrupar por concepto normalizado (lowercase, trim)
4. Ordenar por importe acumulado descendente (absoluto)
5. Presentar con referencias numéricas:
   ```
   Movimientos sin categoría (47 en total, 12 conceptos únicos):

   #1   GIMNASIO MCFIT         3 mov ·  89,97 €
   #2   BAR EL RINCÓN          7 mov · 124,50 €
   #3   PEPE FARMACIA          2 mov ·  23,40 €
   ...
   ```
6. El usuario responde con asignaciones: "1 salud/gimnasio, 2 restaurantes, 3 salud/farmacia"
   - Formatos válidos: "1 salud/gimnasio" | "1-3 restaurantes" (rango) | "1,2,5 compras"
7. Por cada asignación:
   a. Actualizar `categoria` en los CSVs para todos los movimientos del concepto
   b. Añadir el pattern al `rules.yaml` en la categoría correspondiente
8. Si quedan pendientes, ofrecer otra ronda
9. Al terminar: ejecutar pipeline generate → insights
10. Mostrar resumen: X categorizados, Y pendientes, sugerir regenerar dashboard

**Importante:** al añadir patterns a rules.yaml, usar el concepto normalizado en minúsculas. Insertar en la categoría correcta respetando la estructura YAML.

### `/claudia-finanzas enrich <fuente>`

Pipeline unificado de enrichment. Funciona igual para tickets de supermercado (foto), pedidos de Amazon/Privalia (texto/CSV), o cualquier otra fuente.

**Formato unificado de enrichment CSV:**
```csv
fecha_pedido,fecha_extracto,importe_total,importe_item,subcategoria,item,source,status
```
- `importe_total`: importe del movimiento bancario (para matching)
- `importe_item`: importe del producto individual (para analytics)
- `source`: `ticket` | `amazon` | `privalia` | etc.
- `status`: `matched` | `provisional` | `unmatched` (lo rellena match_enrichments.py)

**Flujo:**

**Paso 1 — Leer la entrada:**
- Imagen (ticket) → leer directamente con la capacidad de lectura de ficheros del host (los modelos multimodales la interpretan sin conversión previa)
- CSV/texto → leer directamente o inline del chat
- Las subcategorías DEBEN usar claves de rules.yaml (e.g. `ninos/ropa_calzado`, NO `niños/ropa`)

**Paso 2 — Normalizar (IA):**

Claude extrae del contenido:
- `fecha_pedido`: fecha del ticket/pedido (YYYY-MM-DD)
- `importe_total`: total del ticket/pedido (negativo)
- Por cada producto/item: `importe_item` (negativo), `item` (descripción)
- `source`: detectar automáticamente (ticket, amazon, privalia, etc.)
- `subcategoria`: categorizar los productos que Claude identifique con confianza. Dejar vacía los dudosos.

Escribir el enrichment CSV en `data/enrichments/{source}_{año}.csv` (append si ya existe).

**Paso 3 — Categorización determinista:**
```bash
source .claude/skills/claudia-finanzas/venv/bin/activate && python3 .claude/skills/claudia-finanzas/pipeline/enrich_products.py <workspace> <enrichment_csv>
```
Matchea items sin subcategoría contra `rules.yaml (sección `enrichment_patterns`)`. Los ya conocidos se categorizan sin IA.

**Paso 4 — Categorización IA (solo items nuevos):**

Si `enrich_products.py` reporta items sin match (`unmatched_items`):
1. Claude los categoriza usando claves de rules.yaml
2. Actualiza el enrichment CSV con las subcategorías
3. Añade los nuevos patterns a `rules.yaml (sección `enrichment_patterns`)` para que en próximos enrichments se resuelvan sin IA

**Paso 5 — Cruce con extracto:**
```bash
python3 .claude/skills/claudia-finanzas/pipeline/match_enrichments.py <workspace> <enrichment_csv>
```
- Match por `fecha ± 5 días` + `importe_total ± 0.02€`
- `matched` → vinculado al extracto
- `provisional` → el extracto no cubre esa fecha aún (se reconciliará al importar extracto nuevo)
- `unmatched` → el extracto cubre la fecha pero no hay match (otra tarjeta/cuenta, o error)

**Paso 6 — Pipeline:**

Ejecutar categorize → generate → insights. El `categorize.py` solo sobreescribe la categoría del extracto si TODOS los items de un enrichment tienen la misma subcategoría. Si son mixtos (ticket con niños + alimentación), el extracto conserva su categoría original.

Mostrar resumen: N items, M categorías asignadas (X deterministas + Y por IA), estado de matching.

### `/claudia-finanzas dashboard`

Regenera dashboard completo.

**Flujo:**
1. Ejecutar pipeline: categorize → generate → insights
2. Si el servidor HTTP no está corriendo, lanzarlo:
   ```bash
   cd user/workspaces/claudia-finanzas/dashboard && python3 -m http.server 8090 --bind 0.0.0.0 &
   ```
3. Informar la URL de acceso (e.g. `http://localhost:8090`)

### `/claudia-finanzas regenerar`

Alias rápido para regenerar data.json + insights sin categorizar.

**Flujo:**
1. Ejecutar generate.py + insights.py
2. Mostrar resumen

### `/claudia-finanzas rules`

Muestra estadísticas de rules.yaml: categorías, patterns totales, categorías sin patterns.

### `/claudia-finanzas status`

Resumen rápido: periodos importados, movimientos totales, % categorizados, ahorro acumulado.

## Categorización: lógica de matching

El categorizador busca patterns en 3 columnas (concepto + movimiento + observaciones).
Case-insensitive, contains match. Pattern más largo matchea primero.

Orden de prioridad:
1. **Enrichments** — si hay match fecha±3d + importe exacto en enrichments/, usa esa subcategoría
2. **Rules.yaml** — patterns por contains en las 3 columnas
3. **Amount threshold** — `restaurantes/cafes_desayunos` con threshold -20: si |importe| ≤ 20, asigna cafes_desayunos; si > 20, asigna restaurante

Flags especiales en rules.yaml:
- `is_saving: true` → categoría de ahorro (excluida del gasto)
- `is_neutral: true` → categoría neutra (traspasos internos, excluida)
- `is_income: true` → ingresos (excluidos del gasto)

## data.json: contrato con dashboard

```json
{
  "years": ["2024", "2025", "2026"],
  "summary": {"2026": {"ingresos": 218.04, "movimientos": 527, "sin_categoria": 36}},
  "cat_totals": {"2026": {"hipoteca": 3878.38, "alimentacion/supermercado": 3680.73, ...}},
  "monthly_totals": {"2026": {"1": 5432.10, "2": 4891.30, ...}},
  "monthly_by_cat": {"2026": {"1": {"alimentacion": 1246.07, ...}, ...}},
  "top_merchants": {"2026": [["Mercadona", 3680.73], ...]},
  "cat_labels": {"alimentacion": "Alimentación", "suministros/luz": "Suministros / Luz", ...},
  "patterns_map": {"hipoteca": ["pattern1", "pattern2"], ...},
  "concepts_by_cat": {"2026": {"hipoteca": [["Concepto 1", 4, -3772.20], ...]}},
  "enrichment_provisional": {"2026": {"alimentacion/cafe": 26.97}},
  "insights": [{"type": "interanual", "label": "📈 Vehículo", "text": "...", "direction": "up"}],
  "alerts": [{"icon": "⚠", "text": "..."}],
  "generated_at": "2026-05-22 16:26"
}
```

Claves mensuales: `"1"`, `"2"`, ..., `"12"` (string, NO `"2026-01"`).
Conceptos: `[nombre, count, total]` tuples. Total es negativo para gastos.
Top merchants: `[[nombre, importe_abs], ...]` arrays.

## Parsers de banco (legacy)

Los parsers en `parsers/` son utilidades auxiliares. El import principal usa normalización por IA (ver comando `import` arriba). `generic_csv.py` queda disponible como fallback programático si se necesita en scripts fuera del flujo interactivo.

## Notas de diseño

- **IA como parser universal:** la normalización de extractos la hace la IA, no parsers deterministas. Esto permite al usuario subir cualquier formato sin adaptaciones. El pipeline determinista (categorize → generate → insights) solo trabaja con CSV canónico.
- **Privacidad:** los datos financieros nunca salen del sistema local
- **Idempotencia:** importar el mismo extracto no duplica (dedup por fecha+concepto+importe en `merge_extract.py`)
- **Separación framework/usuario:** templates y pipeline en la skill (actualizable), datos y rules en el workspace del usuario (protegido)

#!/usr/bin/env python3
"""
Claudia OS — Intake Processor
Lee items 'new' de la cola, pre-extrae contenido, sintetiza el wisdom y lo guarda en el vault.

Dos formas de sintetizar, según quién ejecute:
- Cron (servidor): el script lanza `claude -p` por su cuenta.
- Agente (tarea de la app de escritorio, o en el chat): el agente que ya está en marcha hace la
  síntesis. Nunca se lanza otro Claude por debajo.

Uso:
    python3 intake_process.py              # Cron: procesar cola con claude -p
    python3 intake_process.py --dry-run    # Ver qué se procesaría
    python3 intake_process.py --max 3      # Limitar a N items
    python3 intake_process.py --prepare    # Agente, paso 1: pre-extrae y deja el lote para sintetizar
    python3 intake_process.py --save       # Agente, paso 2: guarda en el vault lo que sintetizó
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VAULT_WISDOM = REPO_ROOT / "user" / "vault" / "wisdom"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intake_queue import get_items, update_status, get_stats, _now_iso
from intake_extract import extract_content

BATCH_SIZE = 5  # Max items por llamada a Claude
SHORT_LIMIT = 15000   # caracteres por pieza dentro de un lote de varias
LONG_LIMIT = 120000   # una pieza más larga (vídeo, pódcast, entrevista) va sola en su lote, con este tope
AGENT_BATCH = REPO_ROOT / "user" / "vault" / ".index" / "intake_batch.json"
AGENT_RESULT = REPO_ROOT / "user" / "vault" / ".index" / "intake_batch_result.json"
STUCK_AFTER_HOURS = 2  # Antigüedad tras la que un item 'processing' se da por abandonado

TRANSIENT_ERROR_PATTERNS = [
    "no such file or directory",
    "timeout",
    "connection refused",
    "connection reset",
    "temporary failure",
    "resource temporarily unavailable",
    "429",                 # rate limit (Substack lo da al bajar muchas páginas seguidas)
    "too many requests",
]
FETCH_PAUSE_SECONDS = 2  # pausa entre descargas, para no disparar el rate limit de los sitios


def _is_transient_error(error):
    """Detecta errores transitorios que merecen reintento automático."""
    if not error:
        return False
    return any(p in error.lower() for p in TRANSIENT_ERROR_PATTERNS)

EXTRACTION_WARNINGS = {
    "article_x": (
        "⚠️ <b>Artículo de X no extraíble automáticamente</b>\n\n"
        "El artículo enlazado desde este tweet requiere un navegador para renderizarse "
        "(contenido JavaScript). He procesado los metadatos disponibles, pero no el contenido completo.\n\n"
        "📖 <b>Léelo aquí:</b> {article_url}\n"
        "🐦 <b>Tweet original:</b> {url}"
    ),
}


def _notify_telegram(text):
    """Envía notificación puntual al usuario por Telegram."""
    import urllib.request
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_USER_ID")
    if not token or not chat_id:
        return
    try:
        data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _load_env():
    """Carga variables de user/credentials/.env."""
    creds = REPO_ROOT / "user/credentials/.env"
    if creds.exists():
        for line in creds.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _slugify(text):
    """Genera un slug a partir de texto."""
    if not text:
        return "untitled"
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60]


def _build_wisdom_prompt(extractions):
    """Construye el prompt para Claude con todo el contenido pre-extraído."""
    items_text = []
    for item_id, data in extractions.items():
        content = data.get("text", "")

        if data.get("needs_webfetch"):
            # X Article u otro contenido que requiere WebFetch
            fetch_url = data.get("metadata", {}).get("article_url", data.get("url", ""))
            items_text.append(
                f'=== ITEM {item_id} ===\n'
                f'URL: {data.get("url", "")}\n'
                f'Type: {data.get("content_type", "article_x")}\n'
                f'Author: {data.get("author", "Desconocido")}\n'
                f'\nINSTRUCCION: Usa WebFetch en la siguiente URL para leer el contenido completo del artículo, '
                f'luego extrae el wisdom como con cualquier otro item:\n'
                f'FETCH_URL: {fetch_url}\n'
                f'=== END ITEM {item_id} ==='
            )
            continue

        if not content:
            continue

        # Truncar contenido muy largo (una pieza sola en su lote admite mucho más: ver _batches)
        limit = LONG_LIMIT if len(extractions) == 1 else SHORT_LIMIT
        if len(content) > limit:
            content = content[:limit] + "\n\n[... contenido truncado ...]"
        context = f'Context: {data["context"]}\n' if data.get("context") else ""

        items_text.append(
            f'=== ITEM {item_id} ===\n'
            f'URL: {data.get("url", "")}\n'
            f'Title: {data.get("title", "Sin titulo")}\n'
            f'Type: {data.get("content_type", "article")}\n'
            f'Author: {data.get("author", "Desconocido")}\n'
            f'{context}'
            f'\nCONTENT:\n{content}\n'
            f'=== END ITEM {item_id} ==='
        )

    all_content = "\n\n".join(items_text)

    prompt = f"""Eres un asistente de extraccion de conocimiento. Tienes {len(extractions)} contenidos para procesar.

Para CADA item, extrae:
1. takeaway: Lo mas importante en maximo 20 palabras
2. ideas: 5-15 ideas clave (las mas interesantes, sorprendentes o contraintuitivas)
3. insights: 3-7 insights refinados (ideas elevadas a principio, mas abstractas y transferibles)
4. quotes: 3-10 citas textuales memorables (con atribucion al autor)
5. concepts: Terminos, frameworks o modelos mentales (con breve definicion)
6. actions: 0-5 acciones concretas recomendadas
7. topics: 2-5 temas/categorias para clasificar
8. quality: alta/media/baja
9. slug: slug descriptivo para el nombre de fichero (ej: "miessler-ai-agent-stack")
10. title: titulo limpio del contenido

Si un item trae "Context", es una indicacion del usuario sobre esa pieza: siguela. Por ejemplo, en una
entrevista o un podcast con varias voces puede pedir que extraigas solo lo que dice una persona
(Author); entonces ideas, insights y citas son solo suyas, y lo del entrevistador o de otros invitados
no se le atribuye.

Responde UNICAMENTE con un JSON valido (sin markdown, sin backticks, sin texto antes o despues).
El JSON debe ser un objeto con los item_id como claves:

{{
  "item_id_1": {{
    "title": "...",
    "takeaway": "...",
    "ideas": ["...", "..."],
    "insights": ["...", "..."],
    "quotes": ["Quote text — Author", "..."],
    "concepts": ["**Concepto** — definicion", "..."],
    "actions": ["...", "..."],
    "topics": ["tema1", "tema2"],
    "quality": "alta|media|baja",
    "slug": "slug-descriptivo"
  }},
  ...
}}

CONTENIDOS A PROCESAR:

{all_content}"""

    return prompt


def _parse_claude_output(stdout):
    """Parsea el output JSON de claude -p."""
    # Claude con --output-format json wrappea en un objeto
    try:
        outer = json.loads(stdout)
        # El resultado real puede estar en .result o en el texto directo
        if isinstance(outer, dict) and "result" in outer:
            text = outer["result"]
        elif isinstance(outer, list):
            # Array de content blocks
            text = ""
            for block in outer:
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
        elif isinstance(outer, str):
            text = outer
        else:
            text = stdout
    except json.JSONDecodeError:
        text = stdout

    # Limpiar posibles backticks markdown
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] No se pudo parsear JSON de Claude: {e}")
        print(f"  Raw output (primeros 500 chars): {text[:500]}")
        return {}


def _save_wisdom_file(item_id, wisdom, extraction, today):
    """Guarda un fichero wisdom en el vault."""
    VAULT_WISDOM.mkdir(parents=True, exist_ok=True)

    # La fecha del vault es la de publicación si se conoce; si no, la del procesado.
    published = extraction.get("published")
    date = published if published and re.match(r"^\d{4}-\d{2}-\d{2}$", str(published)) else today
    slug = wisdom.get("slug", _slugify(wisdom.get("title", item_id)))
    filename = f"{date}_{slug}.md"
    filepath = VAULT_WISDOM / filename

    title = wisdom.get("title", extraction.get("title", "Sin titulo"))
    author = extraction.get("author", "Desconocido")
    url = extraction.get("url", "")
    content_type = extraction.get("content_type", "article")
    topics = wisdom.get("topics", [])
    quality = wisdom.get("quality", "media")

    # Build frontmatter
    topics_str = json.dumps(topics, ensure_ascii=False)
    frontmatter = (
        f'---\n'
        f'source: "{url}"\n'
        f'type: {content_type}\n'
        f'author: "{author}"\n'
        f'title: "{title}"\n'
        f'date: {date}\n'
        f'topics: {topics_str}\n'
        f'quality: {quality}\n'
        f'origin: intake\n'
        f'---\n'
    )

    # Build body
    body_parts = [f"# {title}\n"]
    body_parts.append(f"**Fuente:** {url}")
    body_parts.append(f"**Autor:** {author}")
    body_parts.append(f"**Procesado:** {today}\n")

    if wisdom.get("takeaway"):
        body_parts.append(f"## Takeaway\n\n{wisdom['takeaway']}\n")

    if wisdom.get("ideas"):
        body_parts.append("## Ideas clave\n")
        for idea in wisdom["ideas"]:
            body_parts.append(f"- {idea}")
        body_parts.append("")

    if wisdom.get("insights"):
        body_parts.append("## Insights\n")
        for ins in wisdom["insights"]:
            body_parts.append(f"- {ins}")
        body_parts.append("")

    if wisdom.get("quotes"):
        body_parts.append("## Citas\n")
        for q in wisdom["quotes"]:
            if q.startswith(">"):
                body_parts.append(q)
            else:
                body_parts.append(f"> {q}")
            body_parts.append("")

    if wisdom.get("concepts"):
        body_parts.append("## Conceptos clave\n")
        for c in wisdom["concepts"]:
            body_parts.append(f"- {c}")
        body_parts.append("")

    if wisdom.get("actions"):
        body_parts.append("## Acciones recomendadas\n")
        for a in wisdom["actions"]:
            body_parts.append(f"- {a}")
        body_parts.append("")

    content = frontmatter + "\n" + "\n".join(body_parts) + "\n"
    filepath.write_text(content)
    print(f"  Saved: {filename}")
    return filename



def _vault_sources():
    """URLs ya en el vault, leidas del campo `source:` del frontmatter."""
    sources = set()
    if not VAULT_WISDOM.exists():
        return sources
    for f in VAULT_WISDOM.glob("*.md"):
        try:
            with f.open(encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    if i > 20:
                        break
                    if line.startswith("source:"):
                        sources.add(line.split(":", 1)[1].strip().strip('"').strip("'"))
                        break
        except Exception:
            continue
    return sources


def _rescue_stuck(max_age_hours=STUCK_AFTER_HOURS):
    """Rescata items abandonados en 'processing' por una ejecucion que murio a media.

    No se pueden reencolar a ciegas: la ejecucion pudo escribir ya el fichero en el
    vault antes de caer, y reprocesarlos genera duplicados con otro slug. Se comprueba
    el `source:` del vault antes de decidir. Devuelve (reencolados, cerrados).
    """
    stuck = get_items(status="processing")
    if not stuck:
        return 0, 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    sources = None
    rescued = closed = 0
    for item in stuck:
        try:
            queued = datetime.fromisoformat(item["queued_at"])
        except Exception:
            continue
        if queued.tzinfo is None:
            queued = queued.replace(tzinfo=timezone.utc)
        if queued > cutoff:
            continue  # puede ser una ejecucion viva ahora mismo
        if sources is None:
            sources = _vault_sources()
        if item.get("url") in sources:
            update_status(item["id"], "processed", processed_at=_now_iso())
            closed += 1
        else:
            update_status(item["id"], "new", error=None)
            rescued += 1
    return rescued, closed


def _pending_items(max_items=None):
    """Reintenta errores transitorios, rescata items abandonados y devuelve los 'new'."""
    # Auto-retry: resetear items con errores transitorios
    failed = get_items(status="failed")
    retried = 0
    for item in failed:
        if _is_transient_error(item.get("error")):
            update_status(item["id"], "new", error=None)
            retried += 1
    if retried:
        print(f"Auto-retry: {retried} items con errores transitorios reseteados\n")

    # Rescate de items abandonados en 'processing' (ejecucion muerta a media)
    rescued, closed = _rescue_stuck()
    if rescued or closed:
        print(f"Rescate: {rescued} reencolados, {closed} ya estaban en el vault\n")

    items = get_items(status="new")
    if max_items:
        items = items[:max_items]
    return items


def _pre_extract(items):
    """Fase 1: marca los items como 'processing' y extrae su contenido. Devuelve {id: extraction}."""
    print("Fase 1: Pre-extraccion de contenido...")
    extractions = {}
    fetched = 0
    for item in items:
        update_status(item["id"], "processing")

        # Si el item trae contenido pre-extraído (ej: mentors), saltamos el fetch
        if item.get("pre_content"):
            print(f"  Pre-extraído: {item['url'][:60]}...")
            extractions[item["id"]] = {
                "url": item["url"],
                "text": item["pre_content"],
                "title": item.get("title") or "",
                "author": item.get("author") or "Desconocido",
                "content_type": "newsletter",
                "published": item.get("published"),
                "context": item.get("context"),
            }
            continue

        if fetched:
            time.sleep(FETCH_PAUSE_SECONDS)
        fetched += 1
        print(f"  Extrayendo: {item['url'][:60]}...")
        try:
            result = extract_content(item["url"])
            # Si el item tiene author explícito (de mentors), priorizarlo
            if item.get("author") and not result.get("author"):
                result["author"] = item["author"]
            if item.get("published"):
                result["published"] = item["published"]
            if item.get("context"):
                result["context"] = item["context"]
            if result.get("text"):
                extractions[item["id"]] = result
                if result.get("title") and not item.get("title"):
                    update_status(item["id"], "processing", title=result["title"])
            elif result.get("metadata", {}).get("article_url"):
                # X Article u otro contenido que requiere WebFetch — delegar a Claude
                content_type = result.get("content_type", "article_x")
                print(f"  [WEBFETCH] {content_type} detectado, intentando via WebFetch en síntesis...")
                result["needs_webfetch"] = True
                extractions[item["id"]] = result
            else:
                error = result.get("error", "No se pudo extraer contenido")
                print(f"  [FAIL] {error[:100]}")
                update_status(item["id"], "failed", error=error, failed_at=_now_iso())
        except Exception as e:
            print(f"  [FAIL] {e}")
            update_status(item["id"], "failed", error=str(e)[:200], failed_at=_now_iso())

    return extractions


def _batches(extractions):
    """Trocea las extracciones en lotes de BATCH_SIZE: [(ids, prompt), ...].

    Una pieza de más de SHORT_LIMIT caracteres (la transcripción de un vídeo o un pódcast largo) va
    sola en su lote, para no recortarla a los primeros minutos."""
    long_ids = [k for k, v in extractions.items() if len(v.get("text") or "") > SHORT_LIMIT]
    out = [([k], _build_wisdom_prompt({k: extractions[k]})) for k in long_ids]
    ids = [k for k in extractions if k not in long_ids]
    for start in range(0, len(ids), BATCH_SIZE):
        batch_ids = ids[start:start + BATCH_SIZE]
        out.append((batch_ids, _build_wisdom_prompt({k: extractions[k] for k in batch_ids})))
    return out


def _synthesize_with_cli(extractions):
    """Fase 2 (solo cron): sintetiza con `claude -p`. Devuelve {id: wisdom}."""
    print(f"\nFase 2: Wisdom synthesis ({len(extractions)} items)...")
    all_wisdoms = {}
    batches = _batches(extractions)

    for n, (batch_ids, prompt) in enumerate(batches, 1):
        print(f"  Batch {n}: {len(batch_ids)} items...")
        try:
            # El prompt lleva texto de terceros (newsletters, artículos), así que la síntesis corre
            # sin herramientas: ni shell, ni ficheros, ni MCP, tenga los permisos que tenga el
            # proyecto. Solo los items que hay que descargar (X Articles) reciben WebFetch.
            needs_fetch = any(extractions[i].get("needs_webfetch") for i in batch_ids)
            tools = ["--tools", "WebFetch", "--allowedTools", "WebFetch"] if needs_fetch \
                else ["--tools", ""]
            result = subprocess.run(
                # El prompt va por stdin: como argumento, Linux corta a 128 KB y una transcripción
                # larga no cabe.
                ["claude", "-p", "--output-format", "json", "--max-turns", "5",
                 *tools, "--strict-mcp-config"],
                input=prompt, capture_output=True, text=True, timeout=600,
                cwd=str(REPO_ROOT),
            )
            if result.returncode != 0:
                # p. ej. «OAuth session expired»: los items quedan en 'processing' y el rescate
                # los devuelve a la cola pasadas STUCK_AFTER_HOURS.
                print(f"  [ERROR] claude -p salió con código {result.returncode}: "
                      f"{(result.stderr or result.stdout).strip()[:300]}")
                continue
            wisdoms = _parse_claude_output(result.stdout)
            all_wisdoms.update(wisdoms)
        except subprocess.TimeoutExpired:
            print("  [ERROR] Claude timeout (5 min)")
            for item_id in batch_ids:
                update_status(item_id, "failed", error="Claude timeout", failed_at=_now_iso())
        except Exception as e:
            print(f"  [ERROR] Claude: {e}")
            for item_id in batch_ids:
                update_status(item_id, "failed", error=str(e)[:200], failed_at=_now_iso())

    return all_wisdoms


def _finish(extractions, all_wisdoms, items):
    """Fases 3 a 5: guarda en el vault, reindexa y hace commit. Devuelve los items procesados."""
    if not all_wisdoms:
        print("\nNo se pudo generar wisdom de ningun item.")
        return []

    # Phase 3: Save to vault
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\nFase 3: Guardando en vault...")
    saved_files = {}
    processed_items = []

    for item_id, wisdom in all_wisdoms.items():
        if item_id not in extractions:
            continue
        try:
            filename = _save_wisdom_file(item_id, wisdom, extractions[item_id], today)
            saved_files[filename] = {**wisdom, "content_type": extractions[item_id].get("content_type")}
            update_status(item_id, "processed", processed_at=_now_iso())

            # Notificar si WebFetch también falló (calidad baja en item que lo necesitaba)
            extraction = extractions[item_id]
            if extraction.get("needs_webfetch") and wisdom.get("quality") == "baja":
                content_type = extraction.get("content_type", "article_x")
                template = EXTRACTION_WARNINGS.get(content_type)
                if template:
                    msg = template.format(
                        url=extraction.get("url", ""),
                        article_url=extraction.get("metadata", {}).get("article_url", ""),
                    )
                    _notify_telegram(msg)

            # Preparar datos para el briefing
            item_data = next((i for i in items if i["id"] == item_id), {})
            processed_items.append({
                "id": item_id,
                "url": extractions[item_id].get("url", ""),
                "title": wisdom.get("title", item_data.get("title", "")),
                "content_type": extractions[item_id].get("content_type", "article"),
                "wisdom": wisdom,
            })
        except Exception as e:
            print(f"  [ERROR] Saving {item_id}: {e}")
            update_status(item_id, "failed", error=str(e)[:200], failed_at=_now_iso())

    # Phase 4: Reindex vault search
    if saved_files:
        try:
            vault_search = REPO_ROOT / ".claude/skills/vault-search/vault_search.py"
            for filename in saved_files:
                subprocess.run(
                    ["python3", str(vault_search), "--reindex-file", f"wisdom/{filename}"],
                    cwd=str(REPO_ROOT), capture_output=True, timeout=10,
                )
            print(f"  Vault search reindexed: {len(saved_files)} files")
        except Exception as e:
            print(f"  [WARN] Vault reindex failed: {e}")

    # Phase 5: Git commit
    if saved_files:
        try:
            subprocess.run(
                ["git", "add", str(VAULT_WISDOM), str(REPO_ROOT / "user/vault/intake/queue.jsonl")],
                cwd=str(REPO_ROOT), capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"intake: {len(saved_files)} items processed ({today})"],
                cwd=str(REPO_ROOT), capture_output=True,
            )
            print(f"\nGit commit: {len(saved_files)} items")
        except Exception as e:
            print(f"  [WARN] Git commit failed: {e}")

    print(f"\nCompletado: {len(saved_files)} procesados, {len(extractions) - len(saved_files)} fallidos")
    return processed_items


def process_queue(max_items=None, dry_run=False):
    """Cron: procesa la cola de principio a fin, sintetizando con `claude -p`."""
    _load_env()
    items = _pending_items(max_items)
    if not items:
        print("No hay items pendientes en la cola.")
        return []

    print(f"Procesando {len(items)} items...\n")
    if dry_run:
        for item in items:
            print(f"  [DRY] {item['url'][:80]} ({item['source']})")
        return []

    extractions = _pre_extract(items)
    if not extractions:
        print("\nNo se pudo extraer contenido de ningun item.")
        return []
    return _finish(extractions, _synthesize_with_cli(extractions), items)


def prepare_batch(max_items=None):
    """Agente, paso 1: pre-extrae y escribe el lote que el agente tiene que sintetizar."""
    _load_env()
    if AGENT_BATCH.exists():
        age_h = (datetime.now(timezone.utc).timestamp() - AGENT_BATCH.stat().st_mtime) / 3600
        if age_h < STUCK_AFTER_HOURS:
            print(f"Ya hay un lote sin guardar en {AGENT_BATCH.relative_to(REPO_ROOT)} "
                  f"(de hace {age_h:.1f} h). Termínalo con --save antes de preparar otro.")
            return 1
        # Más viejo: sus items ya los ha devuelto a la cola el rescate de _pending_items.

    items = _pending_items(max_items)
    if not items:
        print("No hay items pendientes en la cola.")
        AGENT_BATCH.unlink(missing_ok=True)
        return 0

    print(f"Preparando {len(items)} items...\n")
    extractions = _pre_extract(items)
    if not extractions:
        print("\nNo se pudo extraer contenido de ningun item.")
        return 0

    batch = {
        "created_at": _now_iso(),
        "result_path": str(AGENT_RESULT.relative_to(REPO_ROOT)),
        "instructions": (
            "Para cada lote de 'batches', haz lo que pide su 'prompt'. Junta las respuestas de "
            "todos los lotes en un único objeto JSON {item_id: wisdom} y escríbelo en "
            "'result_path'. Después ejecuta: python3 .claude/skills/claudia-intake/intake_process.py --save"
        ),
        "batches": [{"ids": ids, "prompt": prompt} for ids, prompt in _batches(extractions)],
        "extractions": extractions,
        "items": [{"id": i["id"], "title": i.get("title", "")} for i in items if i["id"] in extractions],
    }
    AGENT_BATCH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_BATCH.write_text(json.dumps(batch, ensure_ascii=False, indent=2))
    AGENT_RESULT.unlink(missing_ok=True)
    print(f"\nLote listo: {len(extractions)} items en {len(batch['batches'])} tanda(s).")
    print(f"Sintetiza siguiendo {AGENT_BATCH.relative_to(REPO_ROOT)} y escribe el resultado en "
          f"{AGENT_RESULT.relative_to(REPO_ROOT)}; luego --save.")
    return 0


def save_batch(result_path=None):
    """Agente, paso 2: guarda en el vault el wisdom que sintetizó el agente."""
    _load_env()
    if not AGENT_BATCH.exists():
        print("No hay ningún lote preparado. Ejecuta antes --prepare.")
        return 1
    result_file = Path(result_path) if result_path else AGENT_RESULT
    if not result_file.is_absolute():
        result_file = REPO_ROOT / result_file
    if not result_file.exists():
        print(f"No encuentro el resultado en {result_file}. Escríbelo antes de --save.")
        return 1

    batch = json.loads(AGENT_BATCH.read_text())
    wisdoms = _parse_claude_output(result_file.read_text())
    if not isinstance(wisdoms, dict) or not wisdoms:
        print("El resultado no es un objeto JSON {item_id: wisdom} válido. No se guarda nada.")
        return 1

    extractions = batch["extractions"]
    processed = _finish(extractions, wisdoms, batch["items"])

    # Lo que el agente no sintetizó vuelve a la cola para el siguiente intento.
    missing = [i for i in extractions if i not in wisdoms]
    for item_id in missing:
        update_status(item_id, "new", error=None)
    if missing:
        print(f"Sin wisdom en el resultado: {len(missing)} item(s), devueltos a la cola.")

    AGENT_BATCH.unlink(missing_ok=True)
    result_file.unlink(missing_ok=True)
    return 0 if processed else 1


def main():
    parser = argparse.ArgumentParser(description="Intake Processor")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Ver qué se procesaría")
    mode.add_argument("--prepare", action="store_true",
                      help="Agente: pre-extrae y deja el lote para que lo sintetice el agente")
    mode.add_argument("--save", nargs="?", const="", metavar="RESULTADO",
                      help="Agente: guarda en el vault el resultado (por defecto intake_batch_result.json)")
    parser.add_argument("--max", type=int, help="Limitar a N items")
    args = parser.parse_args()

    if args.prepare:
        sys.exit(prepare_batch(max_items=args.max))
    if args.save is not None:
        sys.exit(save_batch(args.save or None))
    process_queue(max_items=args.max, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

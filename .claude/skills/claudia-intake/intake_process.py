#!/usr/bin/env python3
"""
Claudia OS — Intake Processor
Lee items 'new' de la cola, pre-extrae contenido, lanza claude -p
para wisdom synthesis, guarda en vault.

Uso:
    python3 intake_process.py              # Procesar cola
    python3 intake_process.py --dry-run    # Ver qué se procesaría
    python3 intake_process.py --max 3      # Limitar a N items
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VAULT_WISDOM = REPO_ROOT / "user" / "vault" / "wisdom"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intake_queue import get_items, update_status, get_stats, _now_iso
from intake_extract import extract_content

BATCH_SIZE = 5  # Max items por llamada a Claude

TRANSIENT_ERROR_PATTERNS = [
    "no such file or directory",
    "timeout",
    "connection refused",
    "connection reset",
    "temporary failure",
    "resource temporarily unavailable",
]


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

        # Truncar contenido muy largo
        if len(content) > 15000:
            content = content[:15000] + "\n\n[... contenido truncado ...]"

        items_text.append(
            f'=== ITEM {item_id} ===\n'
            f'URL: {data.get("url", "")}\n'
            f'Title: {data.get("title", "Sin titulo")}\n'
            f'Type: {data.get("content_type", "article")}\n'
            f'Author: {data.get("author", "Desconocido")}\n'
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

    slug = wisdom.get("slug", _slugify(wisdom.get("title", item_id)))
    filename = f"{today}_{slug}.md"
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
        f'date: {today}\n'
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



def process_queue(max_items=None, dry_run=False):
    """Procesa items 'new' de la cola."""
    _load_env()

    # Auto-retry: resetear items con errores transitorios
    failed = get_items(status="failed")
    retried = 0
    for item in failed:
        if _is_transient_error(item.get("error")):
            update_status(item["id"], "new", error=None)
            retried += 1
    if retried:
        print(f"Auto-retry: {retried} items con errores transitorios reseteados\n")

    items = get_items(status="new")
    if not items:
        print("No hay items pendientes en la cola.")
        return []

    if max_items:
        items = items[:max_items]

    print(f"Procesando {len(items)} items...\n")

    if dry_run:
        for item in items:
            print(f"  [DRY] {item['url'][:80]} ({item['source']})")
        return []

    # Phase 1: Pre-extract content
    print("Fase 1: Pre-extraccion de contenido...")
    extractions = {}
    for item in items:
        print(f"  Extrayendo: {item['url'][:60]}...")
        update_status(item["id"], "processing")
        try:
            result = extract_content(item["url"])
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

    if not extractions:
        print("\nNo se pudo extraer contenido de ningun item.")
        return []

    # Phase 2: Wisdom synthesis via claude -p (en batches)
    print(f"\nFase 2: Wisdom synthesis ({len(extractions)} items)...")
    all_wisdoms = {}
    extraction_ids = list(extractions.keys())

    for batch_start in range(0, len(extraction_ids), BATCH_SIZE):
        batch_ids = extraction_ids[batch_start:batch_start + BATCH_SIZE]
        batch = {k: extractions[k] for k in batch_ids}

        print(f"  Batch {batch_start // BATCH_SIZE + 1}: {len(batch)} items...")
        prompt = _build_wisdom_prompt(batch)

        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json", "--max-turns", "5"],
                capture_output=True, text=True, timeout=300,
                cwd=str(REPO_ROOT),
            )
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


def main():
    parser = argparse.ArgumentParser(description="Intake Processor")
    parser.add_argument("--dry-run", action="store_true", help="Ver qué se procesaría")
    parser.add_argument("--max", type=int, help="Limitar a N items")
    args = parser.parse_args()

    process_queue(max_items=args.max, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

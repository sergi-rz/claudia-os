#!/usr/bin/env python3
"""
claudia-mentors — Fetch content from mentor sources and add to intake queue.
The intake pipeline handles wisdom extraction, vault storage and briefing.

Usage:
  python3 mentor_ingest.py                    # Daily: api + rss + gmail sources with "daily": true
  python3 mentor_ingest.py --backfill          # Historical: every gmail source
  python3 mentor_ingest.py --mentor <id>       # One mentor only
  python3 mentor_ingest.py --dry-run           # Show without queuing
  python3 mentor_ingest.py --status            # Corpus status

Config: user/config/mentors.json (template: mentors.example.json in this directory).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MENTORS_CONFIG = REPO_ROOT / "user/config/mentors.json"
MENTORS_STATE = REPO_ROOT / "user/config/mentors_state.json"
VAULT_WISDOM = REPO_ROOT / "user/vault/wisdom"
GMAIL_SCRIPT = REPO_ROOT / ".claude/skills/claudia-gmail/gmail.py"
GMAIL_PYTHON = REPO_ROOT / ".claude/skills/claudia-gmail/venv/bin/python3"
INTAKE_ADD = REPO_ROOT / ".claude/skills/claudia-intake/intake_add.py"
ENV_FILE = REPO_ROOT / "user/credentials/.env"


def _load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _load_config():
    if not MENTORS_CONFIG.exists():
        print(f"[ERROR] No se encuentra {MENTORS_CONFIG}")
        sys.exit(1)
    return json.loads(MENTORS_CONFIG.read_text())


def _load_state():
    if not MENTORS_STATE.exists():
        return {}
    return json.loads(MENTORS_STATE.read_text())


def _save_state(state):
    MENTORS_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _slugify(text):
    text = text.lower()
    for src, dst in [('á','a'),('à','a'),('ä','a'),('â','a'),('é','e'),('è','e'),
                     ('ë','e'),('ê','e'),('í','i'),('ì','i'),('ï','i'),('î','i'),
                     ('ó','o'),('ò','o'),('ö','o'),('ô','o'),('ú','u'),('ù','u'),
                     ('ü','u'),('û','u'),('ñ','n'),('ç','c')]:
        text = text.replace(src, dst)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:60]


def _vault_file_exists(date_str, title):
    """Dedup: check if a vault file already exists for this date+title."""
    slug = _slugify(title)
    for f in VAULT_WISDOM.glob(f"{date_str}_{slug[:30]}*.md"):
        return True
    return False


def _enqueue(item, mentor, dry_run=False):
    """Add a normalized item to the intake queue."""
    if dry_run:
        print(f"    [DRY-RUN] {item['date']} — {item['title'][:60]}")
        return True

    cmd = [
        "python3", str(INTAKE_ADD),
        "--url", item["url"],
        "--source", "mentor",
        "--title", item["title"],
        "--author", mentor["name"],
    ]
    if item.get("date"):
        cmd += ["--date", item["date"]]
    if item.get("content"):
        cmd += ["--pre-content", item["content"]]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    try:
        resp = json.loads(result.stdout)
        if resp.get("status") == "queued":
            print(f"  Encolado: {item['title'][:60]}")
            return True
        elif resp.get("status") == "duplicate":
            print(f"  Duplicado (ya en cola): {item['title'][:55]}")
            return False
    except Exception:
        print(f"  [ERROR] intake_add: {result.stdout[:100]} {result.stderr[:100]}")
    return False


VAULT_SEARCH = REPO_ROOT / ".claude/skills/vault-search/vault_search.py"

# Keyword → topic mapping, only used by --direct (no LLM to pick topics).
# Override with "topic_keywords" at the top level of mentors.json.
DEFAULT_TOPIC_KEYWORDS = {
    "ia":                 ["inteligencia artificial", "chatgpt", "claude", "gemini", "llm", "prompt", "agente"],
    "negocio":            ["negocio", "cliente", "venta", "factura", "ingreso", "monetiz", "precio", "cobrar", "nicho"],
    "productividad":      ["productividad", "hábito", "gestión del tiempo", "foco", "rutina"],
    "marca-personal":     ["marca personal", "visibilidad", "reputación", "audiencia"],
    "creacion-contenido": ["contenido", "newsletter", "escribir", "publicar", "creator"],
    "marketing":          ["marketing", "copywriting", "landing", "funnel", "conversión"],
    "finanzas":           ["dinero", "finanzas", "inversión", "ahorr"],
    "tecnologia":         ["tecnología", "software", "código", "programar"],
    "psicologia":         ["psicolog", "mental", "emocion", "miedo", "confianza", "motivaci"],
    "filosofia":          ["filosofía", "filosóf", "sentido", "propósito", "estoic"],
}


def _auto_topics(text: str, topic_keywords: dict) -> list:
    """Keyword-based topic matching. Baseline for direct backfill."""
    text_lower = text.lower()
    return [t for t, kws in topic_keywords.items() if any(kw in text_lower for kw in kws)]


# Generic newsletter footers. Mentor-specific ones go in "footer_patterns" (mentors.json).
DEFAULT_FOOTER_PATTERNS = [r"darse de baja", r"unsubscribe", r"©\s*20\d{2}"]
_NOISE_LINE_RE = re.compile(r"view in web browser", re.IGNORECASE)


def _clean_email_body(body: str, footer_patterns: list) -> str:
    """Strip noise lines and footer from email body."""
    footer_re = re.compile("|".join(DEFAULT_FOOTER_PATTERNS + list(footer_patterns)), re.IGNORECASE)
    lines = []
    for line in body.splitlines():
        if footer_re.search(line):
            break
        if _NOISE_LINE_RE.search(line):
            continue
        lines.append(line)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def _write_vault_direct(item, mentor, dry_run=False, topic_keywords=None):
    """Write email content directly to vault, bypassing intake and claude -p."""
    date_str = item["date"]
    title = item["title"]
    author_slug = _slugify(mentor["name"])
    title_slug = _slugify(title)
    filename = f"{date_str}_{author_slug}-{title_slug[:40]}.md"
    filepath = VAULT_WISDOM / filename

    if dry_run:
        print(f"    [DRY-RUN] {date_str} — {title[:60]}")
        return True

    body = _clean_email_body(item['content'], mentor.get("footer_patterns", []))
    topics = _auto_topics(title + " " + body, topic_keywords or DEFAULT_TOPIC_KEYWORDS)
    topics_yaml = json.dumps(topics, ensure_ascii=False)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    content = f"""---
source: "{item['url']}"
type: newsletter
author: "{mentor['name']}"
title: "{title}"
date: {date_str}
topics: {topics_yaml}
quality: baja
origin: mentor
---
# {title}

**Fuente:** {item['url']}
**Autor:** {mentor['name']}
**Procesado:** {today} (direct backfill)

## Contenido

{body}
"""

    filepath.write_text(content, encoding="utf-8")
    print(f"  [DIRECT] {date_str} — {title[:55]}")

    # Reindex in vault SQLite
    try:
        subprocess.run(
            ["python3", str(VAULT_SEARCH), "--reindex-file", f"wisdom/{filename}"],
            capture_output=True, cwd=str(REPO_ROOT)
        )
    except Exception:
        pass

    return True


# Field names an "api" source returns. Override per source with "fields" in mentors.json,
# e.g. {"id": "post_id", "title": "titulo"} when the endpoint uses other names.
DEFAULT_API_FIELDS = {"id": "id", "title": "title", "date": "date", "content": "content", "url": "url"}


def _fetch_api(source):
    """Fetch the latest item from a JSON endpoint (Bearer token). Returns normalized item or None."""
    url = source["url"]
    token = os.environ.get(source.get("credentials_key", ""))
    if not token:
        print(f"  [WARN] Token no encontrado: {source.get('credentials_key')}")
        return None

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  [ERROR] API fetch: {e}")
        return None

    fields = {**DEFAULT_API_FIELDS, **source.get("fields", {})}
    if not data.get(fields["id"]):
        return None

    return {
        "id": data[fields["id"]],
        "title": data.get(fields["title"], ""),
        "date": data.get(fields["date"], datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "content": data.get(fields["content"], ""),
        "url": data.get(fields["url"], ""),
    }


ATOM_NS = "{http://www.w3.org/2005/Atom}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"


def _atom_entries(root):
    """Normalize Atom entries (YouTube, many blogs) to (guid, title, link, date_str)."""
    for entry in root.findall(f"{ATOM_NS}entry"):
        link = ""
        for l in entry.findall(f"{ATOM_NS}link"):
            if l.get("rel", "alternate") == "alternate":
                link = l.get("href", "")
                break
        guid = entry.findtext(f"{ATOM_NS}id") or link
        date_raw = entry.findtext(f"{ATOM_NS}published") or entry.findtext(f"{ATOM_NS}updated") or ""
        date_str = date_raw[:10] if re.match(r"\d{4}-\d{2}-\d{2}", date_raw) \
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        body = entry.findtext(f"{ATOM_NS}content") or entry.findtext(f"{ATOM_NS}summary") or ""
        yield guid, entry.findtext(f"{ATOM_NS}title") or "", link, date_str, body


def _rss_entries(channel):
    from email.utils import parsedate_to_datetime
    for entry in channel.findall("item"):
        guid = entry.findtext("guid") or entry.findtext("link") or ""
        try:
            date_str = parsedate_to_datetime(entry.findtext("pubDate") or "").strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        body = entry.findtext(f"{CONTENT_NS}encoded") or entry.findtext("description") or ""
        yield guid, entry.findtext("title") or "", entry.findtext("link") or "", date_str, body


def _skip_reason(source, title, link, body_len):
    """Filtros de una fuente rss. Devuelve el motivo para saltar la pieza, o None."""
    if "/shorts/" in link and not source.get("include_shorts"):
        return "short"
    for pattern in source.get("exclude_title", []):
        if re.search(pattern, title, re.IGNORECASE):
            return "título excluido"
    min_chars = source.get("min_content_chars")
    if min_chars and body_len < min_chars:
        return "contenido corto (¿de pago?)"
    return None


def _html_to_text(raw: str) -> str:
    """Texto legible de un cuerpo HTML de feed (newsletters con mucho CSS, como las de Mailchimp)."""
    import html as _html
    t = re.sub(r"(?is)<(style|script|head)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</div>|</tr>", "\n", t)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t))
    lines = []
    for line in t.splitlines():
        line = re.sub(r"[ \t\xa0]+", " ", line).strip()
        if line in ("-->", "<!--") or re.search(r'\b(style|target|href)="', line):
            continue  # restos de comentarios condicionales y atributos rotos
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _fetch_rss(source, state_ids, limit=None, footer_patterns=None):
    """Fetch from an RSS 2.0 or Atom feed. Returns list of normalized items.

    Por defecto solo trae título y enlace: la intake descarga la página. Con
    "use_feed_content": true se usa el cuerpo del feed (limpio de HTML y cortado en el pie)."""
    url = source["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "claudia-mentors/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"  [ERROR] RSS fetch: {e}")
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  [ERROR] RSS parse: {e}")
        return []

    if root.tag == f"{ATOM_NS}feed":
        entries = _atom_entries(root)
    else:
        channel = root.find("channel")
        if channel is None:
            print("  [ERROR] RSS parse: ni RSS 2.0 ni Atom")
            return []
        entries = _rss_entries(channel)

    items = []
    skipped = {}
    for guid, title, link, date_str, body in entries:
        guid = guid.split("?")[0].rstrip("/")
        if guid in state_ids:
            continue
        reason = _skip_reason(source, title, link, len(body))
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        # YouTube's watch URLs carry the video id in the query string: keep it.
        if "youtube.com/watch" not in link:
            link = link.split("?")[0]

        items.append({
            "id": guid,
            "title": title,
            "date": date_str,
            "content": _clean_email_body(_html_to_text(body), footer_patterns or [])
                       if source.get("use_feed_content") else "",  # si no, la intake descarga la URL
            "url": link,
        })

        if limit and len(items) >= limit:
            break

    if skipped:
        print("  Omitidos por filtros: " + ", ".join(f"{n} {r}" for r, n in skipped.items()))
    return items


def _fetch_gmail(source, mentor_id, state, gmail_max=20):
    """Fetch emails from Gmail. Returns list of normalized items."""
    account = source["account"]
    query = source["query"]
    processed_ids = set(state.get(mentor_id, {}).get("processed_ids", []))

    if not GMAIL_PYTHON.exists():
        print("  [ERROR] Fuente gmail sin claudia-gmail instalada "
              f"(falta {GMAIL_PYTHON.relative_to(REPO_ROOT)}). Configura claudia-gmail primero.")
        return []

    try:
        result = subprocess.run(
            [str(GMAIL_PYTHON), str(GMAIL_SCRIPT),
             "--account", account, "--action", "search", "--query", query,
             "--max", str(gmail_max)],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"  [ERROR] Gmail search: {e}")
        return []

    messages = [m for m in data.get("messages", []) if m["id"] not in processed_ids]
    if not messages:
        return []

    print(f"  Gmail ({account}): {len(messages)} emails nuevos")
    items = []
    for msg in messages:
        try:
            result = subprocess.run(
                [str(GMAIL_PYTHON), str(GMAIL_SCRIPT),
                 "--account", account, "--action", "read", "--id", msg["id"]],
                capture_output=True, text=True, timeout=30
            )
            full = json.loads(result.stdout)
        except Exception as e:
            print(f"  [WARN] No se pudo leer email {msg['id']}: {e}")
            continue

        body = full.get("body", "").strip()
        if not body or len(body) < 80:
            continue

        try:
            from email.utils import parsedate_to_datetime
            date_str = parsedate_to_datetime(msg.get("date", "")).strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        items.append({
            "id": msg["id"],
            "title": msg.get("subject", ""),
            "date": date_str,
            "content": body,
            "url": f"gmail://{account}/{msg['id']}",
        })

    return items


KNOWN_SOURCE_TYPES = {"api", "rss", "gmail"}


def process_mentor(mentor, state, backfill=False, dry_run=False, limit=None, gmail_max=20, direct=False, collect=False, collected=None, topic_keywords=None):
    mentor_id = mentor["id"]
    print(f"\n── {mentor['name']} ({mentor_id})")

    mentor_state = state.setdefault(mentor_id, {"processed_ids": []})
    processed_ids = set(mentor_state.get("processed_ids", []))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    queued = 0
    for source in mentor.get("sources", []):
        src_type = source.get("type")
        if src_type not in KNOWN_SOURCE_TYPES:
            print(f"  [WARN] Tipo de fuente desconocido '{src_type}': se ignora "
                  f"(válidos: {', '.join(sorted(KNOWN_SOURCE_TYPES))})")
            continue

        if src_type == "api" and not backfill:
            print(f"  Fetching API...")
            item = _fetch_api(source)
            if not item:
                continue
            if item["id"] in processed_ids or _vault_file_exists(item["date"], item["title"]):
                print(f"  Ya procesado: {item['title'][:55]}")
                continue
            if _enqueue(item, mentor, dry_run):
                if not dry_run:
                    mentor_state["processed_ids"].append(item["id"])
                    mentor_state["last_run"] = today
                    _save_state(state)
                queued += 1

        elif src_type == "rss" and not backfill:
            print(f"  Fetching RSS...")
            items = _fetch_rss(source, processed_ids, limit=limit,
                               footer_patterns=mentor.get("footer_patterns", []))
            print(f"  RSS: {len(items)} item(s) nuevos")
            for item in items:
                if _vault_file_exists(item["date"], item["title"]):
                    print(f"  Ya en vault: {item['date']} {item['title'][:45]}")
                    mentor_state["processed_ids"].append(item["id"])
                    continue
                if _enqueue(item, mentor, dry_run):
                    if not dry_run:
                        mentor_state["processed_ids"].append(item["id"])
                        mentor_state["last_run"] = today
                        _save_state(state)
                    queued += 1

        elif src_type == "gmail" and (backfill or collect or source.get("daily")):
            items = _fetch_gmail(source, mentor_id, state, gmail_max=gmail_max)
            for item in items:
                if _vault_file_exists(item["date"], item["title"]):
                    print(f"  Ya en vault: {item['date']} {item['title'][:45]}")
                    mentor_state["processed_ids"].append(item["id"])
                    if not dry_run:
                        _save_state(state)
                    continue
                if collect:
                    collected.append({**item, "mentor_id": mentor_id, "mentor_name": mentor["name"]})
                    queued += 1
                    continue
                if direct:
                    ok = _write_vault_direct(item, mentor, dry_run, topic_keywords=topic_keywords)
                else:
                    ok = _enqueue(item, mentor, dry_run)
                if ok:
                    if not dry_run:
                        mentor_state["processed_ids"].append(item["id"])
                        mentor_state["last_run"] = today
                        _save_state(state)
                    queued += 1

    if not queued:
        print("  Sin contenido nuevo.")

    return queued


COLLECT_QUEUE = REPO_ROOT / "user/vault/.index/mentor_collect_queue.json"


def cmd_collect(config, state, mentor_filter=None, gmail_max=20):
    """Fetch emails from Gmail and save to a JSON queue for interactive processing."""
    mentors = config.get("mentors", [])
    if mentor_filter:
        mentors = [m for m in mentors if m["id"] == mentor_filter]

    collected = []
    for mentor in mentors:
        process_mentor(mentor, state, backfill=True, gmail_max=gmail_max,
                       collect=True, collected=collected)

    if not collected:
        print("Sin emails nuevos para recoger.")
        return

    COLLECT_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    COLLECT_QUEUE.write_text(json.dumps(collected, indent=2, ensure_ascii=False))
    print(f"\n{len(collected)} email(s) guardados en {COLLECT_QUEUE}")
    print("Pide a Claude en el chat: 'procesa el batch de mentors'")


def _count_vault_by_author():
    """Count vault entries per author, reading the `author:` frontmatter field."""
    counts = {}
    if not VAULT_WISDOM.exists():
        return counts
    for f in VAULT_WISDOM.glob("*.md"):
        try:
            with f.open(encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    if i > 20 or line.startswith("---") and i > 0:
                        break
                    if line.startswith("author:"):
                        author = line.split(":", 1)[1].strip().strip('"').strip("'")
                        counts[author] = counts.get(author, 0) + 1
                        break
        except Exception:
            continue
    return counts


PHOTOS_DIR = REPO_ROOT / "user/config/mentor-photos"
PHOTO_EXTS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _feed_image(url):
    """URL de la imagen que publica un feed (RSS <image>, iTunes o Atom logo/icon), o None."""
    req = urllib.request.Request(url, headers={"User-Agent": "claudia-mentors/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        root = ET.fromstring(resp.read().lstrip())
    channel = root.find("channel")
    if channel is not None:
        itunes = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
        return channel.findtext("image/url") or (itunes.get("href") if itunes is not None else None)
    return root.findtext(f"{ATOM_NS}logo") or root.findtext(f"{ATOM_NS}icon")


def cmd_fetch_photos(config, mentor_filter=None, force=False):
    """Descarga la foto de cada mentor desde la imagen de su feed, si la hay.

    Es la imagen de la publicación: a veces la cara del autor, a veces un logo. Revísalas; las que
    no sirvan se sustituyen a mano en user/config/mentor-photos/<id>.jpg."""
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    for mentor in config.get("mentors", []):
        mid = mentor["id"]
        if mentor_filter and mid != mentor_filter:
            continue
        existing = [p for p in PHOTOS_DIR.glob(f"{mid}.*")]
        if existing and not force:
            print(f"  {mentor['name']}: ya tiene foto ({existing[0].name})")
            continue
        url = None
        for source in mentor.get("sources", []):
            if source.get("type") != "rss":
                continue
            try:
                url = _feed_image(source["url"])
            except Exception as e:
                print(f"  {mentor['name']}: [WARN] feed ilegible ({e})")
            if url:
                break
        if not url:
            print(f"  {mentor['name']}: sin imagen en sus fuentes (ponla a mano: {mid}.jpg)")
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "claudia-mentors/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                ctype = (resp.headers.get_content_type() or "").lower()
                body = resp.read()
        except Exception as e:
            print(f"  {mentor['name']}: [WARN] no se pudo descargar la imagen ({e})")
            continue
        ext = PHOTO_EXTS.get(ctype)
        if not ext:
            print(f"  {mentor['name']}: [WARN] formato no soportado ({ctype})")
            continue
        for old in existing:
            old.unlink()
        (PHOTOS_DIR / f"{mid}{ext}").write_bytes(body)
        print(f"  {mentor['name']}: foto guardada ({mid}{ext}, {len(body) // 1024} KB). Revisa que sea su cara y no un logo.")


def cmd_status(config, state):
    print("── claudia-mentors status ──")
    counts = _count_vault_by_author()
    for mentor in config.get("mentors", []):
        mid = mentor["id"]
        ms = state.get(mid, {})
        tracked = len(ms.get("processed_ids", []))
        last = ms.get("last_run", "nunca")
        in_vault = counts.get(mentor["name"], 0)
        print(f"  {mentor['name']}: {in_vault} en vault | {tracked} IDs tracked | última ingesta: {last}")


def main():
    parser = argparse.ArgumentParser(description="claudia-mentors ingest")
    parser.add_argument("--mentor", help="Solo procesar este mentor ID")
    parser.add_argument("--backfill", action="store_true", help="Histórico completo desde Gmail")
    parser.add_argument("--dry-run", action="store_true", help="Muestra sin encolar")
    parser.add_argument("--status", action="store_true", help="Estado del corpus")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de items nuevos a procesar por fuente RSS")
    parser.add_argument("--gmail-max", type=int, default=20, help="Máximo de emails a buscar en Gmail por backfill (default: 20)")
    parser.add_argument("--direct", action="store_true", help="Escribe directamente al vault sin intake ni claude -p (0 tokens)")
    parser.add_argument("--collect", action="store_true", help="Recoge emails en JSON para procesado interactivo con Claude en el chat")
    parser.add_argument("--fetch-photos", action="store_true", help="Descarga la foto de cada mentor desde la imagen de su feed")
    parser.add_argument("--force", action="store_true", help="Con --fetch-photos, sustituye las fotos que ya haya")
    args = parser.parse_args()

    _load_env()
    config = _load_config()
    state = _load_state()

    if args.status:
        cmd_status(config, state)
        return

    if args.fetch_photos:
        cmd_fetch_photos(config, mentor_filter=args.mentor, force=args.force)
        return

    if args.collect:
        cmd_collect(config, state, mentor_filter=args.mentor, gmail_max=args.gmail_max)
        return

    mentors = config.get("mentors", [])
    if args.mentor:
        mentors = [m for m in mentors if m["id"] == args.mentor]
        if not mentors:
            print(f"Mentor '{args.mentor}' no encontrado en mentors.json")
            sys.exit(1)

    total = 0
    for mentor in mentors:
        total += process_mentor(mentor, state, backfill=args.backfill, dry_run=args.dry_run, limit=args.limit, gmail_max=args.gmail_max, direct=args.direct, collect=False, topic_keywords=config.get("topic_keywords"))

    print(f"\nTotal: {total} item(s) encolados en intake")


if __name__ == "__main__":
    main()

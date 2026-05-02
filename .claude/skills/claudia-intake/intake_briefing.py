#!/usr/bin/env python3
"""
Claudia OS — Intake Briefing
Genera y envía el briefing dual: Telegram (índice corto) + Email (completo).

Uso:
    python3 intake_briefing.py                    # Briefing completo (TG + email)
    python3 intake_briefing.py --telegram-only    # Solo Telegram
    python3 intake_briefing.py --email-only       # Solo email
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Error: 'requests' no está instalado.")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VAULT_WISDOM = REPO_ROOT / "user" / "vault" / "wisdom"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intake_queue import get_items, get_feed_new_indexed, get_stats, expire_old
from intake_email import send_email


def _load_env():
    """Carga variables de user/credentials/.env."""
    creds = REPO_ROOT / "user/credentials/.env"
    if creds.exists():
        for line in creds.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _send_telegram(text):
    """Envía mensaje a Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_USER_ID")

    if not token or not chat_id:
        print("[WARN] TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no configurados")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.ok:
            print("[OK] Telegram briefing enviado")
            return True
        else:
            print(f"[ERROR] Telegram: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")
        return False


def _get_recent_processed(hours=24):
    """Devuelve items procesados en las últimas N horas."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = get_items(status="processed")
    recent = []
    for item in items:
        try:
            processed_at = item.get("processed_at")
            if processed_at:
                dt = datetime.fromisoformat(processed_at)
                if dt > cutoff:
                    recent.append(item)
        except (ValueError, TypeError):
            continue
    return recent


def _load_wisdom_content(item):
    """Intenta cargar el contenido wisdom del vault para un item."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Buscar ficheros de hoy en el vault que coincidan con la URL
    if not VAULT_WISDOM.exists():
        return {}

    # Buscar por fecha de procesamiento
    processed_at = item.get("processed_at", "")
    date_prefix = processed_at[:10] if processed_at else today

    for md_file in VAULT_WISDOM.glob(f"{date_prefix}_*.md"):
        content = md_file.read_text()
        # Comprobar si este fichero corresponde a este item (buscar la URL)
        if item.get("url", "NOMATCH") in content:
            # Parsear las secciones del fichero wisdom
            return _parse_wisdom_file(content)

    return {}


def _parse_wisdom_file(content):
    """Parsea un fichero wisdom .md y extrae las secciones."""
    result = {}
    current_section = None
    current_items = []

    for line in content.split("\n"):
        if line.startswith("## Takeaway"):
            current_section = "takeaway"
            current_items = []
        elif line.startswith("## Ideas"):
            if current_section == "takeaway" and current_items:
                result["takeaway"] = " ".join(current_items).strip()
            current_section = "ideas"
            current_items = []
        elif line.startswith("## Insights"):
            if current_section and current_items:
                result[current_section] = current_items if current_section != "takeaway" else " ".join(current_items).strip()
            current_section = "insights"
            current_items = []
        elif line.startswith("## Citas"):
            if current_section and current_items:
                result[current_section] = current_items
            current_section = "quotes"
            current_items = []
        elif line.startswith("## "):
            if current_section and current_items:
                result[current_section] = current_items if current_section != "takeaway" else " ".join(current_items).strip()
            current_section = None
            current_items = []
        elif current_section:
            line = line.strip()
            if line.startswith("- "):
                current_items.append(line[2:])
            elif line.startswith("> "):
                current_items.append(line[2:])
            elif line and current_section == "takeaway":
                current_items.append(line)

    if current_section and current_items:
        result[current_section] = current_items if current_section != "takeaway" else " ".join(current_items).strip()

    return result


def _get_persistent_failures(hours=48):
    """Devuelve items fallidos con errores no transitorios y recientes."""
    from intake_process import _is_transient_error
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    failed = get_items(status="failed")
    recent = []
    for item in failed:
        if _is_transient_error(item.get("error")):
            continue
        try:
            ts = item.get("failed_at") or item.get("queued_at")
            if ts and datetime.fromisoformat(ts) > cutoff:
                recent.append(item)
        except (ValueError, TypeError):
            continue
    return recent


def build_telegram_message(processed, feed_indexed, stats, failed=None):
    """Construye el mensaje de Telegram."""
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    parts = [f"<b>Briefing diario — {today}</b>"]

    if processed:
        parts.append(f"\n<b>Procesados ({len(processed)}):</b>")
        for item in processed:
            title = item.get("title") or item.get("url", "")[:50]
            ctype = item.get("content_type", "")
            # Intentar obtener takeaway del wisdom
            wisdom = _load_wisdom_content(item)
            takeaway = wisdom.get("takeaway", "")
            line = f"• <i>{title}</i>"
            if ctype:
                line += f" ({ctype})"
            if takeaway:
                line += f"\n  {takeaway[:100]}"
            parts.append(line)

    if failed:
        parts.append(f"\n<b>Fallidos ({len(failed)}):</b>")
        for item in failed:
            title = item.get("title") or item.get("url", "")[:50]
            error = item.get("error", "error desconocido")[:80]
            parts.append(f"• {title}\n  {error}")

    if feed_indexed:
        parts.append(f"\n<b>Nuevo de feeds ({len(feed_indexed)}):</b>")
        for idx, item in feed_indexed:
            source = item.get("source_detail", "")
            title = item.get("title") or item.get("url", "")[:50]
            parts.append(f"{idx}. [{source}] {title}")
        parts.append("\nResponde <code>procesa 1,3</code> para extraer wisdom")

    pending = stats.get("new", 0)
    expired_count = stats.get("expired", 0)
    parts.append(f"\nCola: {pending} pendientes | {expired_count} archivados")

    return "\n".join(parts)


def generate_briefing(telegram=True, email=True, hours=24):
    """Genera y envía el briefing."""
    _load_env()

    # Expire old items first
    n_expired = expire_old(14)
    if n_expired:
        print(f"Expired {n_expired} items antiguos")

    processed = _get_recent_processed(hours)
    feed_indexed = get_feed_new_indexed()
    failed = _get_persistent_failures()
    stats = get_stats()

    has_content = bool(processed) or bool(feed_indexed) or bool(failed)
    if not has_content:
        print("No hay contenido para el briefing (sin procesados recientes ni feeds nuevos)")
        return

    print(f"Briefing: {len(processed)} procesados, {len(feed_indexed)} feeds nuevos, {len(failed)} fallidos\n")

    # Telegram
    if telegram:
        tg_msg = build_telegram_message(processed, feed_indexed, stats, failed)
        _send_telegram(tg_msg)

    # Email (si hay items procesados o fallos que reportar)
    if email and (processed or failed):
        wisdom_contents = {}
        for item in processed:
            wisdom = _load_wisdom_content(item)
            if wisdom:
                wisdom_contents[item["id"]] = wisdom

        feed_items = [item for _, item in feed_indexed]
        send_email(processed, feed_items, stats, wisdom_contents, failed)


def main():
    parser = argparse.ArgumentParser(description="Intake Briefing")
    parser.add_argument("--telegram-only", action="store_true")
    parser.add_argument("--email-only", action="store_true")
    parser.add_argument("--hours", type=int, default=24, help="Horas hacia atrás para buscar procesados")
    args = parser.parse_args()

    telegram = not args.email_only
    email = not args.telegram_only

    generate_briefing(telegram=telegram, email=email, hours=args.hours)


if __name__ == "__main__":
    main()

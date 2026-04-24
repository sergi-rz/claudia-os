#!/usr/bin/env python3
"""
Claudia OS — Intake Email Briefing
Genera y envía el briefing por email con las extracciones wisdom inline.

Uso:
    python3 intake_email.py --items '[...]' --feeds '[...]' --stats '{...}'
    python3 intake_email.py --test   # Envía email de prueba

Variables requeridas en user/credentials/.env:
    EMAIL_TO        — dirección destinataria del briefing
    SMTP_HOST       — servidor SMTP (ej. smtp.gmail.com)
    SMTP_PORT       — puerto, opcional (default: 587)
    SMTP_USER       — usuario/remitente (ej. cuenta@gmail.com)
    SMTP_PASSWORD   — contraseña o app password
"""

import argparse
import json
import os
import smtplib
import ssl
import subprocess
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CREDS_FILE = REPO_ROOT / "user/credentials/.env"
SETTINGS_FILE = REPO_ROOT / "user/config/settings.json"
GMAIL_TOKENS_DIR = REPO_ROOT / "user/credentials/gmail/tokens"
GMAIL_SCRIPT = REPO_ROOT / ".claude/skills/claudia-gmail/gmail.py"
GMAIL_VENV_PYTHON = REPO_ROOT / ".claude/skills/claudia-gmail/venv/bin/python3"


def _load_env():
    if CREDS_FILE.exists():
        for line in CREDS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _load_email_accounts():
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text()).get("gmail_accounts", {})
    return {}


def _get_email_to():
    _load_env()
    email = os.environ.get("EMAIL_TO")
    if not email:
        raise ValueError("EMAIL_TO no está configurado en user/credentials/.env")
    return email


def _resolve_sender():
    """Resuelve la cuenta remitente desde email_accounts.json o autodetecta."""
    _load_env()
    accounts = _load_email_accounts()

    # Preferencia explícita: EMAIL_FROM apunta a una dirección en email_accounts.json
    from_addr = os.environ.get("EMAIL_FROM")
    if from_addr and from_addr in accounts:
        return accounts[from_addr]

    # Primera cuenta Gmail con token válido en email_accounts.json
    for addr, cfg in accounts.items():
        if cfg.get("type") == "gmail":
            token = cfg.get("token", "")
            if (GMAIL_TOKENS_DIR / f"{token}.json").exists():
                return cfg

    # Fallback: primer token Gmail disponible en disco
    if GMAIL_TOKENS_DIR.exists():
        tokens = [f.stem for f in GMAIL_TOKENS_DIR.glob("*.json")]
        if tokens:
            return {"type": "gmail", "token": tokens[0]}

    # Último recurso: SMTP genérico desde .env
    if os.environ.get("SMTP_HOST"):
        return {
            "type": "smtp",
            "smtp_host": os.environ["SMTP_HOST"],
            "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
            "smtp_user": os.environ.get("SMTP_USER", ""),
            "smtp_password_env": "SMTP_PASSWORD",
        }

    return None


def build_html(processed_items, feed_items, stats, wisdom_contents=None, failed_items=None):
    """Genera el HTML del briefing email."""
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    wisdom_contents = wisdom_contents or {}
    failed_items = failed_items or []

    # Header
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 640px; margin: 0 auto; padding: 16px; color: #1a1a1a; background: #f9f9f9; }}
  .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 20px; color: #2563eb; margin: 0; }}
  .header .date {{ color: #666; font-size: 14px; }}
  .item {{ background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 16px; border: 1px solid #e5e7eb; }}
  .item h2 {{ font-size: 16px; margin: 0 0 8px; }}
  .item h2 a {{ color: #2563eb; text-decoration: none; }}
  .item .type {{ display: inline-block; background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .item .takeaway {{ color: #374151; font-weight: 600; margin: 8px 0; }}
  .section-title {{ font-size: 14px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px; }}
  .ideas li, .insights li {{ margin-bottom: 4px; line-height: 1.4; }}
  .insights {{ border-left: 3px solid #2563eb; padding-left: 12px; }}
  .quote {{ font-style: italic; color: #4b5563; border-left: 3px solid #d1d5db; padding-left: 12px; margin: 8px 0; }}
  .feeds {{ background: #fff; border-radius: 8px; padding: 16px; border: 1px solid #e5e7eb; }}
  .feeds li {{ margin-bottom: 6px; }}
  .feeds .source {{ color: #6b7280; font-size: 13px; }}
  .footer {{ text-align: center; color: #9ca3af; font-size: 12px; margin-top: 24px; padding-top: 12px; border-top: 1px solid #e5e7eb; }}
</style></head><body>
<div class="header">
  <h1>Claudia Briefing</h1>
  <div class="date">{today}</div>
</div>
"""

    # Processed items con wisdom inline
    if processed_items:
        html += f'<p style="color:#374151"><strong>{len(processed_items)} contenidos procesados</strong></p>\n'
        for item in processed_items:
            item_id = item.get("id", "")
            url = item.get("url", "")
            title = item.get("title") or url[:60]
            content_type = item.get("content_type", "article")
            wisdom = wisdom_contents.get(item_id, {})
            takeaway = wisdom.get("takeaway", "")
            ideas = wisdom.get("ideas", [])
            insights = wisdom.get("insights", [])
            quotes = wisdom.get("quotes", [])

            html += f"""<div class="item">
  <h2><a href="{url}">{title}</a></h2>
  <span class="type">{content_type}</span>
"""
            if takeaway:
                html += f'  <p class="takeaway">{takeaway}</p>\n'

            if ideas:
                html += '  <div class="section-title">Ideas clave</div>\n  <ul class="ideas">\n'
                for idea in ideas[:7]:
                    html += f"    <li>{idea}</li>\n"
                html += "  </ul>\n"

            if insights:
                html += '  <div class="section-title">Insights</div>\n  <div class="insights">\n  <ul>\n'
                for ins in insights[:5]:
                    html += f"    <li>{ins}</li>\n"
                html += "  </ul>\n  </div>\n"

            if quotes:
                html += '  <div class="section-title">Citas</div>\n'
                for q in quotes[:3]:
                    html += f'  <div class="quote">{q}</div>\n'

            html += "</div>\n"

    # Failed items
    if failed_items:
        html += f'<p style="color:#991b1b"><strong>{len(failed_items)} contenidos con error</strong></p>\n'
        for item in failed_items:
            url = item.get("url", "")
            title = item.get("title") or url[:60]
            error = item.get("error", "error desconocido")
            html += f"""<div class="item" style="border-color:#fca5a5">
  <h2><a href="{url}">{title}</a></h2>
  <p style="color:#991b1b;font-size:13px">{error}</p>
</div>
"""

    # Feed items
    if feed_items:
        html += f"""<div class="feeds">
  <p style="color:#374151"><strong>{len(feed_items)} nuevos de feeds</strong></p>
  <ol>
"""
        for item in feed_items:
            source = item.get("source_detail", "")
            title = item.get("title") or item.get("url", "")[:60]
            url = item.get("url", "")
            html += f'    <li><a href="{url}">{title}</a> <span class="source">— {source}</span></li>\n'
        html += "  </ol>\n  <p style='color:#6b7280;font-size:13px'>Responde \"procesa N\" en Telegram para extraer wisdom</p>\n</div>\n"

    # Footer
    pending = stats.get("new", 0)
    expired = stats.get("expired", 0)
    html += f"""<div class="footer">
  Cola: {pending} pendientes | {expired} archivados<br>
  Generado por Claudia OS
</div>
</body></html>"""

    return html


def build_plain(processed_items, feed_items, stats, wisdom_contents=None, failed_items=None):
    """Genera versión plain text del briefing."""
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    wisdom_contents = wisdom_contents or {}
    failed_items = failed_items or []
    lines = [f"Claudia Briefing — {today}", "=" * 40, ""]

    if processed_items:
        lines.append(f"PROCESADOS ({len(processed_items)}):")
        lines.append("")
        for item in processed_items:
            title = item.get("title") or item.get("url", "")[:60]
            wisdom = wisdom_contents.get(item.get("id", ""), {})
            takeaway = wisdom.get("takeaway", "")
            lines.append(f"- {title}")
            if takeaway:
                lines.append(f"  {takeaway}")
            lines.append(f"  {item.get('url', '')}")
            lines.append("")

    if failed_items:
        lines.append(f"FALLIDOS ({len(failed_items)}):")
        lines.append("")
        for item in failed_items:
            title = item.get("title") or item.get("url", "")[:60]
            error = item.get("error", "error desconocido")
            lines.append(f"- {title}")
            lines.append(f"  Error: {error}")
            lines.append("")

    if feed_items:
        lines.append(f"NUEVO DE FEEDS ({len(feed_items)}):")
        for i, item in enumerate(feed_items, 1):
            source = item.get("source_detail", "")
            title = item.get("title") or item.get("url", "")[:60]
            lines.append(f"  {i}. [{source}] {title}")
        lines.append("")

    pending = stats.get("new", 0)
    expired = stats.get("expired", 0)
    lines.append(f"Cola: {pending} pendientes | {expired} archivados")

    return "\n".join(lines)


def _send_via_gmail(account, to, subject, plain, html):
    """Envía usando el token OAuth de claudia-gmail."""
    if not GMAIL_VENV_PYTHON.exists():
        return False, "Gmail venv no encontrado"
    result = subprocess.run(
        [str(GMAIL_VENV_PYTHON), str(GMAIL_SCRIPT),
         "--account", account, "--action", "send",
         "--to", to, "--subject", subject,
         "--body", plain, "--html-body", html],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        return True, None
    return False, result.stderr[:300]


def _send_via_smtp(to, subject, plain, html, cfg):
    """Envía usando credenciales SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["user"]
    msg["To"] = to
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context()) as s:
                s.login(cfg["user"], cfg["password"])
                s.sendmail(cfg["user"], to, msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(cfg["user"], cfg["password"])
                s.sendmail(cfg["user"], to, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def send_email(processed_items, feed_items, stats, wisdom_contents=None, failed_items=None):
    """Genera y envía el briefing. Resuelve el remitente desde email_accounts.json."""
    to = _get_email_to()
    today = datetime.now(timezone.utc).strftime("%d %b %Y")
    subject = f"Claudia Briefing — {today}"
    plain = build_plain(processed_items, feed_items, stats, wisdom_contents, failed_items)
    html = build_html(processed_items, feed_items, stats, wisdom_contents, failed_items)

    sender = _resolve_sender()
    if not sender:
        print("[ERROR] No hay cuenta remitente configurada. Añade cuentas en user/config/email_accounts.json o variables SMTP_* en .env")
        return False

    if sender.get("type") == "gmail":
        token = sender["token"]
        ok, err = _send_via_gmail(token, to, subject, plain, html)
        if ok:
            print(f"[OK] Email enviado a {to} (Gmail OAuth: {token})")
            return True
        print(f"[ERROR] Gmail OAuth ({token}): {err}")
        return False

    if sender.get("type") == "smtp":
        _load_env()
        password_env = sender.get("smtp_password_env", "SMTP_PASSWORD")
        smtp_cfg = {
            "host": sender["smtp_host"],
            "port": int(sender.get("smtp_port", 587)),
            "user": sender["smtp_user"],
            "password": os.environ.get(password_env, ""),
        }
        ok, err = _send_via_smtp(to, subject, plain, html, smtp_cfg)
        if ok:
            print(f"[OK] Email enviado a {to} (SMTP: {sender['smtp_user']})")
            return True
        print(f"[ERROR] SMTP: {err}")
        return False

    print(f"[ERROR] Tipo de cuenta desconocido: {sender.get('type')}")
    return False


def _send_test():
    """Envía un email de prueba."""
    test_items = [{
        "id": "test123",
        "url": "https://example.com/test-article",
        "title": "Test Article: AI Agent Memory Systems",
        "content_type": "article",
    }]
    test_wisdom = {
        "test123": {
            "takeaway": "Los sistemas de memoria para agentes IA funcionan mejor con archivos markdown + SQLite FTS5 como indice derivado.",
            "ideas": [
                "Los embeddings son costosos y no mejoran la precision en memorias < 1000 items",
                "El formato .md es legible, editable y versionable con git",
                "SQLite FTS5 ofrece busqueda full-text sin dependencias externas",
            ],
            "insights": [
                "La simplicidad del stack importa mas que la sofisticacion teorica",
                "Los agentes que leen sus propios archivos rinden mejor que los que usan APIs de memoria",
            ],
            "quotes": [
                "The best memory system is the one your agent actually reads. - Research finding",
            ],
        }
    }
    test_feeds = [
        {"url": "https://example.com/feed1", "title": "New Video: Transformers Explained", "source_detail": "3Blue1Brown"},
        {"url": "https://example.com/feed2", "title": "SQLite for Everything", "source_detail": "Simon Willison"},
    ]
    test_stats = {"new": 2, "feed_new": 5, "processed": 3, "expired": 1, "total": 11}

    print("Enviando email de prueba...")
    ok = send_email(test_items, test_feeds, test_stats, test_wisdom)
    print(f"Resultado: {'OK' if ok else 'FAIL'}")


def main():
    parser = argparse.ArgumentParser(description="Intake Email Briefing")
    parser.add_argument("--test", action="store_true", help="Enviar email de prueba")
    parser.add_argument("--items", help="JSON array de items procesados")
    parser.add_argument("--feeds", help="JSON array de feed items")
    parser.add_argument("--stats", help="JSON dict de stats")
    parser.add_argument("--wisdom", help="JSON dict de wisdom contents por item_id")
    args = parser.parse_args()

    if args.test:
        _send_test()
    elif args.items:
        items = json.loads(args.items)
        feeds = json.loads(args.feeds) if args.feeds else []
        stats = json.loads(args.stats) if args.stats else {}
        wisdom = json.loads(args.wisdom) if args.wisdom else {}
        send_email(items, feeds, stats, wisdom)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

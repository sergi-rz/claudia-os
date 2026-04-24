#!/usr/bin/env python3
"""
Claudia OS — Google Calendar via Apps Script Web App.

Lectura:
    python3 fetch_calendar.py                       # eventos de hoy
    python3 fetch_calendar.py --days 7              # próximos 7 días
    python3 fetch_calendar.py --raw                 # salida JSON
    python3 fetch_calendar.py --calendars           # listar calendarios disponibles

Escritura:
    python3 fetch_calendar.py --action create \
        --calendar "your-email@gmail.com" \
        --title "Dentista" --start "2026-03-25T10:00" --end "2026-03-25T11:00"

    python3 fetch_calendar.py --action create \
        --title "Vacaciones" --start "2026-04-01" --all-day

    python3 fetch_calendar.py --action update \
        --event-id "abc123" --calendar "your-email@gmail.com" \
        --title "Nuevo título" --start "2026-03-25T11:00" --end "2026-03-25T12:00"

    python3 fetch_calendar.py --action delete \
        --event-id "abc123" --calendar "your-email@gmail.com"

Requiere: fichero .env en el mismo directorio con CALENDAR_WEBAPP_URL=<url>
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
ENV_FILE = os.path.join(CLAUDIA_ROOT, "user", "credentials", ".env")
SETTINGS_FILE = os.path.join(CLAUDIA_ROOT, "user", "config", "settings.json")


def _load_timezone():
    try:
        with open(SETTINGS_FILE) as f:
            tz = json.load(f).get("timezone")
            if tz:
                return ZoneInfo(tz)
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return ZoneInfo("UTC")


LOCAL_TZ = _load_timezone()

SETTINGS_FILE = os.path.join(CLAUDIA_ROOT, "user", "config", "settings.json")
CONTACT_ALIASES = {}
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE) as f:
            CONTACT_ALIASES = json.load(f).get("calendar_aliases", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"Aviso: error cargando settings.json: {e}", file=sys.stderr)
# Mapa inverso: nombre (lowercase) → email (para resolver --calendar "Familia")
ALIAS_NAME_TO_EMAIL = {v.lower(): k for k, v in CONTACT_ALIASES.items()}


def resolve_calendar(name):
    """Resuelve un alias o nombre de calendario a su ID real."""
    if not name:
        return None
    lower = name.lower()
    # Buscar por nombre de alias → email
    if lower in ALIAS_NAME_TO_EMAIL:
        return ALIAS_NAME_TO_EMAIL[lower]
    # Buscar por email directo
    if lower in {k.lower() for k in CONTACT_ALIASES}:
        return name
    return name  # ya es un ID o nombre desconocido


def display_calendar(cal_id_or_name):
    """Devuelve el alias si existe, si no el nombre original."""
    if cal_id_or_name in CONTACT_ALIASES:
        return CONTACT_ALIASES[cal_id_or_name]
    # Buscar case-insensitive
    for email, alias in CONTACT_ALIASES.items():
        if cal_id_or_name.lower() == email.lower():
            return alias
    return cal_id_or_name


def load_url():
    if not os.path.exists(ENV_FILE):
        print(f"Error: no existe {ENV_FILE}", file=sys.stderr)
        print("Crea el fichero con: CALENDAR_WEBAPP_URL=<tu_url>", file=sys.stderr)
        sys.exit(1)
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("CALENDAR_WEBAPP_URL="):
                return line.split("=", 1)[1].strip()
    print("Error: CALENDAR_WEBAPP_URL no encontrada en .env", file=sys.stderr)
    sys.exit(1)


def http_request(url, data=None):
    """GET si data es None, POST si data es dict."""
    headers = {"User-Agent": "ClaudiaOS/1.0"}
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    else:
        req = urllib.request.Request(url, headers=headers)

    response = urllib.request.urlopen(req, timeout=15)
    # Seguir redirects (Apps Script los usa)
    for _ in range(5):
        if response.status in (301, 302, 303, 307, 308):
            redirect_url = response.getheader("Location")
            if data is not None and response.status == 303:
                req = urllib.request.Request(redirect_url, headers={"User-Agent": "ClaudiaOS/1.0"})
            else:
                req = urllib.request.Request(redirect_url, headers=headers)
                if data is not None and response.status in (307, 308):
                    req.data = payload
                    req.method = "POST"
            response = urllib.request.urlopen(req, timeout=15)
        else:
            break

    body = response.read().decode("utf-8")
    if not body.strip():
        print("Error: respuesta vacía de Google Apps Script", file=sys.stderr)
        sys.exit(1)
    return json.loads(body)


def fetch_events(days=1):
    url = load_url()
    return http_request(f"{url}?days={days}")


def post_action(action_data):
    url = load_url()
    return http_request(url, action_data)


def format_events(data):
    if data["count"] == 0:
        return "No hay eventos programados."

    lines = []
    current_date = None

    for ev in data["events"]:
        start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        date_str = start.strftime("%A %d/%m/%Y")

        if date_str != current_date:
            current_date = date_str
            lines.append(f"\n## {date_str}")

        if ev["allDay"]:
            time_str = "Todo el día"
        else:
            end = datetime.fromisoformat(ev["end"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
            time_str = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

        cal_name = display_calendar(ev.get("calendarId", "")) or display_calendar(ev["calendar"])
        cal_tag = f"[{cal_name}]"
        line = f"- {time_str} — {ev['title']} {cal_tag}"
        lines.append(line)

        if ev.get("location"):
            lines.append(f"  Lugar: {ev['location']}")

    return "\n".join(lines)


def format_calendars(data):
    lines = ["Calendarios disponibles:\n"]
    for cal in data["calendars"]:
        owned = " (propio)" if cal.get("isOwned") else ""
        lines.append(f"- {cal['name']}{owned}")
        lines.append(f"  ID: {cal['id']}")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Claudia OS — Google Calendar via Apps Script")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--calendars", action="store_true")
    parser.add_argument("--action", choices=["create", "update", "delete"])
    parser.add_argument("--calendar")
    parser.add_argument("--title")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--location")
    parser.add_argument("--description")
    parser.add_argument("--event-id", dest="event_id")
    parser.add_argument("--all-day", action="store_true", dest="all_day")
    return parser.parse_args()


if __name__ == "__main__":
    opts = parse_args()

    # Listar calendarios
    if opts.calendars:
        result = post_action({"action": "list_calendars"})
        if opts.raw:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_calendars(result))
        sys.exit(0)

    # Acciones de escritura
    if opts.action in ("create", "update", "delete"):
        payload = {"action": opts.action}
        if opts.calendar:
            payload["calendarId"] = resolve_calendar(opts.calendar)
        if opts.title:
            payload["title"] = opts.title
        if opts.start:
            payload["start"] = opts.start
        if opts.end:
            payload["end"] = opts.end
        if opts.location:
            payload["location"] = opts.location
        if opts.description:
            payload["description"] = opts.description
        if opts.event_id:
            payload["eventId"] = opts.event_id
        if opts.all_day:
            payload["allDay"] = True

        result = post_action(payload)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Lectura (por defecto)
    if opts.days > 30:
        print("Aviso: Apps Script limita a 30 días. Se usarán 30.", file=sys.stderr)
        opts.days = 30
    data = fetch_events(opts.days)
    if opts.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_events(data))

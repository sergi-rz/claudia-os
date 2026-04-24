#!/usr/bin/env python3
"""
Claudia OS — Intake Feed Polling
Lee suscripciones de feeds (RSS, YouTube, Substack), detecta nuevas entradas
y las encola como feed_new.

Uso:
    python3 intake_feeds.py              # Poll todos los feeds activos
    python3 intake_feeds.py --dry-run    # Ver qué se encolaría sin encolar
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Error: 'requests' no está instalado. pip3 install requests")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FEEDS_PATH = REPO_ROOT / "user" / "config" / "feeds.json"

# Importar queue
sys.path.insert(0, str(Path(__file__).resolve().parent))
from intake_queue import add_item, is_duplicate

USER_AGENT = "ClaudiaOS-Intake/1.0"

# Namespaces comunes en feeds Atom/RSS
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}
YT_NS = {"yt": "http://www.youtube.com/xml/schemas/2015"}


def load_feeds():
    """Lee feeds.json. Devuelve dict con feeds y state."""
    if not FEEDS_PATH.exists():
        return {"feeds": [], "state": {}}
    with open(FEEDS_PATH) as f:
        return json.load(f)


def save_feeds(data):
    """Guarda feeds.json con state actualizado."""
    FEEDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDS_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_rss_items(root):
    """Parsea items de RSS 2.0."""
    items = []
    for item in root.findall(".//item"):
        entry = {
            "id": (item.findtext("guid") or item.findtext("link") or ""),
            "title": item.findtext("title") or "",
            "link": item.findtext("link") or "",
            "published": item.findtext("pubDate") or "",
        }
        if entry["id"] or entry["link"]:
            items.append(entry)
    return items


def _parse_atom_entries(root):
    """Parsea entries de Atom (usado por YouTube, Substack, etc.)."""
    items = []
    for entry in root.findall("atom:entry", ATOM_NS):
        link_el = entry.find("atom:link", ATOM_NS)
        link = link_el.get("href", "") if link_el is not None else ""

        # YouTube tiene yt:videoId
        video_id = entry.findtext("yt:videoId", namespaces=YT_NS)
        if video_id and not link:
            link = f"https://www.youtube.com/watch?v={video_id}"

        entry_id = entry.findtext("atom:id", namespaces=ATOM_NS) or link

        items.append({
            "id": entry_id,
            "title": entry.findtext("atom:title", namespaces=ATOM_NS) or "",
            "link": link,
            "published": entry.findtext("atom:published", namespaces=ATOM_NS) or "",
        })
    return items


def fetch_feed(url):
    """Fetch y parsea un feed RSS/Atom. Devuelve lista de entries."""
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Fetch failed: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        print(f"  [ERROR] XML parse failed: {e}")
        return []

    # Detectar formato
    if root.tag == "rss" or root.find(".//channel") is not None:
        return _parse_rss_items(root)
    elif root.tag.endswith("}feed") or root.tag == "feed":
        return _parse_atom_entries(root)
    else:
        # Intentar ambos parsers
        items = _parse_rss_items(root)
        if not items:
            items = _parse_atom_entries(root)
        return items


def poll_feed(feed, state, dry_run=False):
    """Pollea un feed individual. Devuelve número de items nuevos encolados."""
    name = feed["name"]
    url = feed["url"]
    print(f"  Polling: {name} ({url})")

    entries = fetch_feed(url)
    if not entries:
        print(f"  → 0 entries (fetch vacío o error)")
        return 0

    # Obtener IDs ya vistos
    feed_state = state.get(url, {"last_seen_ids": [], "last_polled": None})
    seen_ids = set(feed_state.get("last_seen_ids", []))

    new_count = 0
    new_ids = []

    for entry in entries:
        entry_id = entry["id"]
        entry_link = entry["link"]

        if entry_id in seen_ids:
            continue

        # Check duplicado en la cola también
        if entry_link and is_duplicate(entry_link):
            new_ids.append(entry_id)  # Marcar como visto aunque ya esté en cola
            continue

        if dry_run:
            print(f"    [DRY] Encolaría: {entry['title'][:60]} — {entry_link}")
        else:
            item = add_item(
                url=entry_link,
                source="feed",
                source_detail=name,
                status="feed_new",
                title=entry.get("title"),
            )
            if item:
                print(f"    + {entry['title'][:60]}")
                new_count += 1

        new_ids.append(entry_id)

    # Actualizar state: guardar todos los IDs actuales del feed (últimos 100)
    all_current_ids = [e["id"] for e in entries]
    state[url] = {
        "last_seen_ids": all_current_ids[:100],
        "last_polled": datetime.now(timezone.utc).isoformat(),
    }

    print(f"  → {new_count} nuevos de {len(entries)} entries")
    return new_count


def poll_all(dry_run=False):
    """Pollea todos los feeds activos."""
    data = load_feeds()
    feeds = data.get("feeds", [])
    state = data.get("state", {})

    if not feeds:
        print("No hay feeds configurados en user/config/feeds.json")
        return 0

    active = [f for f in feeds if f.get("active", True)]
    print(f"Polling {len(active)} feeds activos...\n")

    total_new = 0
    for feed in active:
        try:
            n = poll_feed(feed, state, dry_run)
            total_new += n
        except Exception as e:
            print(f"  [ERROR] {feed['name']}: {e}")

    if not dry_run:
        data["state"] = state
        save_feeds(data)

    print(f"\nTotal: {total_new} items nuevos encolados")
    return total_new


def main():
    parser = argparse.ArgumentParser(description="Intake Feed Polling")
    parser.add_argument("--dry-run", action="store_true", help="Ver qué se encolaría sin encolar")
    args = parser.parse_args()

    poll_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

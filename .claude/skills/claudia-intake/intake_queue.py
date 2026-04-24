#!/usr/bin/env python3
"""
Claudia OS — Intake Queue
Gestión de la cola JSONL de contenido pendiente de procesar.

Uso como módulo:
    from intake_queue import add_item, get_items, update_status, get_stats

Uso CLI:
    python3 intake_queue.py --stats
    python3 intake_queue.py --test
"""

import argparse
import fcntl
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
QUEUE_PATH = REPO_ROOT / "user" / "vault" / "intake" / "queue.jsonl"

ACTIVE_STATUSES = {"new", "feed_new", "processing", "processed"}


def _ensure_dir():
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _make_id(url, queued_at):
    return hashlib.sha256(f"{url}:{queued_at}".encode()).hexdigest()[:12]


def _read_all():
    """Lee todas las entradas del JSONL."""
    if not QUEUE_PATH.exists():
        return []
    items = []
    with open(QUEUE_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items


def _write_all(items):
    """Reescribe todo el JSONL con locking."""
    _ensure_dir()
    with open(QUEUE_PATH, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _append_item(item):
    """Añade una entrada con locking."""
    _ensure_dir()
    with open(QUEUE_PATH, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def add_item(url, source="manual", source_detail=None, context=None, status="new", title=None):
    """Añade un item a la cola. Devuelve el dict creado o None si es duplicado."""
    if is_duplicate(url):
        return None

    queued_at = _now_iso()
    item = {
        "id": _make_id(url, queued_at),
        "url": url,
        "title": title,
        "source": source,
        "source_detail": source_detail,
        "status": status,
        "queued_at": queued_at,
        "processed_at": None,
        "context": context,
        "error": None,
    }
    _append_item(item)
    return item


def get_items(status=None):
    """Devuelve items, opcionalmente filtrados por status."""
    items = _read_all()
    if status:
        items = [i for i in items if i["status"] == status]
    return items


def update_status(item_id, new_status, **extra):
    """Actualiza el status de un item y campos extra. Devuelve True si encontrado."""
    items = _read_all()
    found = False
    for item in items:
        if item["id"] == item_id:
            item["status"] = new_status
            for k, v in extra.items():
                item[k] = v
            found = True
            break
    if found:
        _write_all(items)
    return found


def expire_old(days=14):
    """Marca como expired los items new/feed_new con más de N días. Devuelve count."""
    items = _read_all()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = 0
    for item in items:
        if item["status"] in ("new", "feed_new"):
            try:
                queued = datetime.fromisoformat(item["queued_at"])
                if queued < cutoff:
                    item["status"] = "expired"
                    count += 1
            except (ValueError, KeyError):
                continue
    if count > 0:
        _write_all(items)
    return count


def is_duplicate(url):
    """Comprueba si la URL ya está en la cola con status activo."""
    items = _read_all()
    return any(i["url"] == url and i["status"] in ACTIVE_STATUSES for i in items)


def get_stats():
    """Devuelve conteo por status."""
    items = _read_all()
    stats = {}
    for item in items:
        s = item["status"]
        stats[s] = stats.get(s, 0) + 1
    stats["total"] = len(items)
    return stats


def get_feed_new_indexed():
    """Devuelve items feed_new ordenados por queued_at, con índice 1-based para referencia."""
    items = [i for i in _read_all() if i["status"] == "feed_new"]
    items.sort(key=lambda x: x.get("queued_at", ""))
    return [(idx + 1, item) for idx, item in enumerate(items)]


def promote_feed_items(indices):
    """Promueve items feed_new por índice (1-based) a status new. Devuelve lista de títulos."""
    indexed = get_feed_new_indexed()
    index_map = {idx: item for idx, item in indexed}
    titles = []
    for i in indices:
        if i in index_map:
            item = index_map[i]
            update_status(item["id"], "new")
            titles.append(item.get("title") or item["url"])
    return titles


def _run_test():
    """Test básico de todas las operaciones."""
    print("=== Intake Queue Test ===\n")

    # Add
    item = add_item("https://test.example.com/article-test", source="manual", context="test item")
    if item:
        print(f"[OK] add_item: id={item['id']}, status={item['status']}")
    else:
        print("[SKIP] add_item: URL ya existe (duplicado)")
        return

    # Get
    items = get_items(status="new")
    found = any(i["id"] == item["id"] for i in items)
    print(f"[{'OK' if found else 'FAIL'}] get_items(status='new'): encontrado={found}")

    # Duplicate check
    dup = is_duplicate("https://test.example.com/article-test")
    print(f"[{'OK' if dup else 'FAIL'}] is_duplicate: {dup}")

    # Update
    ok = update_status(item["id"], "processed", processed_at=_now_iso())
    print(f"[{'OK' if ok else 'FAIL'}] update_status → processed")

    # Stats
    stats = get_stats()
    print(f"[OK] get_stats: {stats}")

    # Clean up test item
    ok = update_status(item["id"], "expired")
    print(f"[{'OK' if ok else 'FAIL'}] cleanup → expired")

    print("\n=== Test completado ===")


def main():
    parser = argparse.ArgumentParser(description="Intake Queue CLI")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas de la cola")
    parser.add_argument("--test", action="store_true", help="Ejecutar test básico")
    parser.add_argument("--list", metavar="STATUS", help="Listar items por status")
    parser.add_argument("--expire", type=int, metavar="DAYS", help="Expirar items con más de N días")
    args = parser.parse_args()

    if args.test:
        _run_test()
    elif args.stats:
        stats = get_stats()
        print(json.dumps(stats, indent=2))
    elif args.list:
        items = get_items(status=args.list)
        for item in items:
            print(f"  [{item['id']}] {item['url']} ({item['source']}) — {item['status']}")
        print(f"\nTotal: {len(items)}")
    elif args.expire:
        n = expire_old(args.expire)
        print(f"Expired: {n} items")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

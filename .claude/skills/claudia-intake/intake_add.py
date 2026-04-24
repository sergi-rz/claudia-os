#!/usr/bin/env python3
"""
Claudia OS — Intake Add CLI
Punto de entrada ligero para añadir items a la cola.
Usado por el bot de Telegram y otros componentes.

Uso:
    python3 intake_add.py --url "https://..." --source telegram --context "..."
    python3 intake_add.py --promote-feed 2,5
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intake_queue import add_item, promote_feed_items


def main():
    parser = argparse.ArgumentParser(description="Intake Add CLI")
    parser.add_argument("--url", help="URL a encolar")
    parser.add_argument("--source", default="manual", help="Origen: telegram, manual, notes")
    parser.add_argument("--context", default=None, help="Contexto adicional")
    parser.add_argument("--title", default=None, help="Título si se conoce")
    parser.add_argument("--promote-feed", help="Promover items feed_new por índice (ej: 2,5,7)")
    args = parser.parse_args()

    if args.promote_feed:
        indices = [int(x.strip()) for x in args.promote_feed.split(",") if x.strip().isdigit()]
        titles = promote_feed_items(indices)
        print(json.dumps({"promoted": len(titles), "titles": titles}, ensure_ascii=False))
    elif args.url:
        item = add_item(
            url=args.url,
            source=args.source,
            source_detail=args.source,
            context=args.context,
            title=args.title,
        )
        if item:
            print(json.dumps({"status": "queued", "id": item["id"], "url": item["url"]}, ensure_ascii=False))
        else:
            print(json.dumps({"status": "duplicate", "url": args.url}, ensure_ascii=False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

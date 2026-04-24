#!/usr/bin/env python3
"""
Corpus sync — sincroniza el corpus de un workspace con sus fuentes publicadas.

Uso:
    python3 sync.py <workspace> [--source <nombre>] [--sync]

Config: user/workspaces/<workspace>/corpus.json
"""

import argparse
import json
import sys
from pathlib import Path

CLAUDIA_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sources import youtube, substack  # noqa: E402

DISPATCHERS = {"youtube": youtube.sync, "substack": substack.sync}


def main():
    parser = argparse.ArgumentParser(description="Sincroniza corpus de un workspace.")
    parser.add_argument("workspace", help="Nombre del workspace (carpeta bajo user/workspaces/)")
    parser.add_argument("--source", help="Nombre de fuente concreta (clave en corpus.json)")
    parser.add_argument("--sync", action="store_true", help="Descargar y procesar los nuevos. Sin esta flag, dry run.")
    args = parser.parse_args()

    workspace_root = CLAUDIA_ROOT / "user" / "workspaces" / args.workspace
    config_file = workspace_root / "corpus.json"
    if not config_file.exists():
        print(f"ERROR: no existe {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    sources = config.get("sources", {})
    if args.source:
        if args.source not in sources:
            print(f"ERROR: fuente '{args.source}' no existe en corpus.json. Disponibles: {list(sources)}")
            sys.exit(1)
        targets = {args.source: sources[args.source]}
    else:
        targets = sources

    totals = {"processed": 0, "errors": 0}
    for name, src_config in targets.items():
        src_type = src_config.get("type")
        if src_type not in DISPATCHERS:
            print(f"[{name}] tipo '{src_type}' no soportado. Saltando.")
            continue
        print(f"\n=== {name} ({src_type}) ===")
        result = DISPATCHERS[src_type](src_config, str(workspace_root), args.sync)
        totals["processed"] += result.get("processed", 0)
        totals["errors"] += result.get("errors", 0)

    if args.sync:
        print(f"\n--- Total ---\nProcesados: {totals['processed']}\nErrores: {totals['errors']}")


if __name__ == "__main__":
    main()

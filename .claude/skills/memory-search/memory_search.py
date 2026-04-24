#!/usr/bin/env python3
"""
Claudia OS — Memory Search
Indexes user/memory/ .md files with SQLite FTS5 and provides ranked search.
Falls back to grep if FTS5 is not compiled into this Python installation.
"""
import re
import sys
import sqlite3
import subprocess
from pathlib import Path

# Script lives at: .claude/skills/memory-search/memory_search.py
# Repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "user" / "memory"
INDEX_DIR = MEMORY_DIR / ".index"
INDEX_PATH = INDEX_DIR / "memory.db"


def check_fts5() -> bool:
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(content)")
        conn.close()
        return True
    except Exception:
        return False


def needs_rebuild() -> bool:
    if not INDEX_PATH.exists():
        return True
    index_mtime = INDEX_PATH.stat().st_mtime
    for md_file in MEMORY_DIR.rglob("*.md"):
        if ".index" in str(md_file):
            continue
        if md_file.stat().st_mtime > index_mtime:
            return True
    return False


def build_index():
    INDEX_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(INDEX_PATH)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories
        USING fts5(filename, content, tokenize='porter unicode61')
    """)
    conn.execute("DELETE FROM memories")
    indexed = 0
    for md_file in MEMORY_DIR.rglob("*.md"):
        if ".index" in str(md_file):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
            conn.execute("INSERT INTO memories VALUES (?, ?)", (md_file.name, content))
            indexed += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return indexed


def search_sqlite(query: str) -> list[tuple[str, str]]:
    if needs_rebuild():
        build_index()
    conn = sqlite3.connect(INDEX_PATH)
    try:
        rows = conn.execute(
            """SELECT filename,
                      snippet(memories, 1, '>>>', '<<<', '...', 30)
               FROM memories
               WHERE memories MATCH ?
               ORDER BY rank""",
            (query,)
        ).fetchall()
    except sqlite3.OperationalError:
        # Query syntax error (special chars) — fall back to LIKE
        rows = conn.execute(
            "SELECT filename, substr(content, 1, 300) FROM memories WHERE content LIKE ?",
            (f"%{query}%",)
        ).fetchall()
    conn.close()
    return rows


def search_grep(query: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["grep", "-ril", "--include=*.md", query, str(MEMORY_DIR)],
        capture_output=True, text=True
    )
    files = [
        f for f in result.stdout.strip().split("\n")
        if f and ".index" not in f
    ]
    return [(Path(f).name, f"(encontrado en {Path(f).name})") for f in files]


def parse_frontmatter(content: str) -> dict:
    """Extract frontmatter fields from a .md file."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end]
    result = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def cmd_sync_index():
    """Rebuild MEMORY.md from .md files with importance critical or high."""
    memory_md = MEMORY_DIR / "MEMORY.md"
    entries = []

    for md_file in sorted(MEMORY_DIR.glob("*.md")):
        if md_file.name == "MEMORY.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        importance = fm.get("importance", "high")  # default high for backward compat
        if importance not in ("critical", "high"):
            continue
        description = fm.get("description", "")
        if not description:
            # First non-empty line after frontmatter
            body = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL).strip()
            description = body.split("\n")[0].lstrip("#").strip()
        entries.append(f"- {md_file.name} — {description}")

    memory_md.write_text("\n".join(entries) + "\n")
    skipped = sum(
        1 for f in MEMORY_DIR.glob("*.md")
        if f.name != "MEMORY.md" and
        parse_frontmatter(f.read_text()).get("importance", "high") not in ("critical", "high")
    )
    print(f"MEMORY.md actualizado: {len(entries)} entradas (critical/high)")
    print(f"Excluidas: {skipped} entradas (medium/low) — disponibles vía memory-search")


def cmd_rebuild():
    if not check_fts5():
        print("FTS5 no disponible — no hay índice que reconstruir.")
        return
    count = build_index()
    print(f"Índice reconstruido: {count} ficheros indexados.")


def cmd_status():
    if not check_fts5():
        print("Modo: BÁSICO (grep)")
        print("Motivo: SQLite FTS5 no disponible en esta instalación de Python.")
    elif not INDEX_PATH.exists():
        print("Modo: PLENO (SQLite FTS5)")
        print("Índice: no construido aún (se construye en la primera búsqueda).")
    else:
        conn = sqlite3.connect(INDEX_PATH)
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        import os
        size_kb = INDEX_PATH.stat().st_size // 1024
        print(f"Modo: PLENO (SQLite FTS5)")
        print(f"Índice: {count} memorias indexadas ({size_kb} KB)")
        print(f"Ubicación: {INDEX_PATH}")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Uso:")
        print("  memory_search.py <query>      Buscar en memorias")
        print("  memory_search.py --sync-index Reconstruir MEMORY.md desde frontmatter importance")
        print("  memory_search.py --rebuild    Reconstruir índice SQLite")
        print("  memory_search.py --status     Ver modo y estado del índice")
        sys.exit(0)

    if args[0] == "--sync-index":
        cmd_sync_index()
        return

    if args[0] == "--rebuild":
        cmd_rebuild()
        return

    if args[0] == "--status":
        cmd_status()
        return

    query = " ".join(args)
    use_fts5 = check_fts5()

    if use_fts5:
        results = search_sqlite(query)
        mode = "SQLite FTS5"
    else:
        results = search_grep(query)
        mode = "grep"

    if not results:
        print(f"Sin resultados para: '{query}'  [modo: {mode}]")
        return

    print(f"Resultados para: '{query}'  [modo: {mode}]\n")
    for filename, snippet in results:
        print(f"  {filename}")
        print(f"  {snippet}\n")


if __name__ == "__main__":
    main()

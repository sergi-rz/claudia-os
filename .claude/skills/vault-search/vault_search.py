#!/usr/bin/env python3
"""
Claudia OS — Vault Search
SQLite FTS5 index + structured metadata for the knowledge vault.
Indexes wisdom/, research/, weekly-reviews/ with rich frontmatter queries.

Usage:
    python3 vault_search.py "query"                    # Full-text search
    python3 vault_search.py --topic agentes-ia         # Filter by topic
    python3 vault_search.py --author Miessler           # Filter by author
    python3 vault_search.py --context "tema" --max-tokens 2000  # Context pack
    python3 vault_search.py --rebuild                   # Rebuild index
    python3 vault_search.py --stats                     # Show stats
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VAULT_DIR = REPO_ROOT / "user" / "vault"
INDEX_DIR = VAULT_DIR / ".index"
INDEX_PATH = INDEX_DIR / "vault.db"

VAULT_SUBDIRS = ["wisdom", "research", "weekly-reviews"]

CHARS_PER_TOKEN = 4


def check_fts5() -> bool:
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(content)")
        conn.close()
        return True
    except Exception:
        return False


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# --- Frontmatter parsing ---

def parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end]
    result = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key == "topics":
            topics = re.findall(r'[\w-]+', value)
            result["topics"] = topics
        else:
            result[key] = value
    return result


def extract_takeaway(content: str) -> str:
    match = re.search(r'## Takeaway\s*\n+(.+?)(?:\n\n|\n##)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def detect_vault_type(filepath: Path) -> str:
    parts = filepath.parts
    for subdir in VAULT_SUBDIRS:
        if subdir in parts:
            return subdir.rstrip("s") if subdir == "weekly-reviews" else subdir
    return "unknown"


# --- Index management ---

def _create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            vault_type TEXT NOT NULL,
            title TEXT,
            author TEXT,
            source_url TEXT,
            content_type TEXT,
            date TEXT,
            quality TEXT,
            stance TEXT,
            depth TEXT,
            origin TEXT,
            takeaway TEXT,
            indexed_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_topics (
            item_id INTEGER REFERENCES vault_items(id) ON DELETE CASCADE,
            topic TEXT NOT NULL,
            PRIMARY KEY (item_id, topic)
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts
        USING fts5(filepath, title, author, takeaway, content, tokenize='porter unicode61')
    """)


def _drop_tables(conn):
    conn.execute("DROP TABLE IF EXISTS vault_topics")
    conn.execute("DROP TABLE IF EXISTS vault_items")
    conn.execute("DROP TABLE IF EXISTS vault_fts")


def needs_rebuild() -> bool:
    if not INDEX_PATH.exists():
        return True
    index_mtime = INDEX_PATH.stat().st_mtime
    for subdir in VAULT_SUBDIRS:
        d = VAULT_DIR / subdir
        if not d.exists():
            continue
        for md_file in d.rglob("*.md"):
            if ".index" in str(md_file):
                continue
            if md_file.stat().st_mtime > index_mtime:
                return True
    return False


def _collect_md_files() -> list[Path]:
    files = []
    for subdir in VAULT_SUBDIRS:
        d = VAULT_DIR / subdir
        if not d.exists():
            continue
        for md_file in d.rglob("*.md"):
            if ".index" in str(md_file) or md_file.name == "INDEX.md":
                continue
            files.append(md_file)
    return files


def _index_file(conn, md_file: Path):
    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception:
        return False

    fm = parse_frontmatter(content)
    rel_path = str(md_file.relative_to(VAULT_DIR))
    vault_type = detect_vault_type(md_file)
    takeaway = extract_takeaway(content)
    title = fm.get("title", "")
    author = fm.get("author", "")

    conn.execute("DELETE FROM vault_items WHERE filepath = ?", (rel_path,))
    conn.execute("DELETE FROM vault_fts WHERE filepath = ?", (rel_path,))

    conn.execute("""
        INSERT INTO vault_items
        (filepath, filename, vault_type, title, author, source_url, content_type,
         date, quality, stance, depth, origin, takeaway, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rel_path, md_file.name, vault_type,
        title, author,
        fm.get("source", ""), fm.get("type", ""),
        fm.get("date", ""), fm.get("quality", ""),
        fm.get("stance", ""), fm.get("depth", ""),
        fm.get("origin", ""), takeaway, _now_iso(),
    ))

    item_id = conn.execute(
        "SELECT id FROM vault_items WHERE filepath = ?", (rel_path,)
    ).fetchone()[0]

    topics = fm.get("topics", [])
    for topic in topics:
        conn.execute(
            "INSERT OR IGNORE INTO vault_topics (item_id, topic) VALUES (?, ?)",
            (item_id, topic),
        )

    body = content
    fm_end = content.find("---", 3)
    if fm_end != -1:
        body = content[fm_end + 3:]

    conn.execute(
        "INSERT INTO vault_fts (filepath, title, author, takeaway, content) VALUES (?, ?, ?, ?, ?)",
        (rel_path, title, author, takeaway, body),
    )
    return True


def build_index() -> int:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    _drop_tables(conn)
    _create_tables(conn)

    files = _collect_md_files()
    indexed = 0
    for md_file in files:
        if _index_file(conn, md_file):
            indexed += 1

    conn.commit()
    conn.close()
    return indexed


def reindex_file(relative_path: str) -> bool:
    md_file = VAULT_DIR / relative_path
    if not md_file.exists():
        return False

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    result = _index_file(conn, md_file)
    conn.commit()
    conn.close()
    return result


def _ensure_index():
    if needs_rebuild():
        build_index()


# --- Search ---

def search_fts(query: str, filters: dict = None) -> list[dict]:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)
    conn.row_factory = sqlite3.Row

    if filters:
        matching_paths = _apply_filters(conn, filters)
        if not matching_paths:
            conn.close()
            return []

    try:
        rows = conn.execute("""
            SELECT filepath, snippet(vault_fts, 4, '>>>', '<<<', '...', 30) as snippet
            FROM vault_fts
            WHERE vault_fts MATCH ?
            ORDER BY rank
        """, (query,)).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute("""
            SELECT filepath, substr(content, 1, 300) as snippet
            FROM vault_fts WHERE content LIKE ?
        """, (f"%{query}%",)).fetchall()

    results = []
    for row in rows:
        fp = row["filepath"]
        if filters and fp not in matching_paths:
            continue
        item = _get_item_metadata(conn, fp)
        if item:
            item["snippet"] = row["snippet"]
            results.append(item)

    conn.close()
    return results


def search_structured(filters: dict) -> list[dict]:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)
    conn.row_factory = sqlite3.Row

    matching_paths = _apply_filters(conn, filters)

    results = []
    for fp in matching_paths:
        item = _get_item_metadata(conn, fp)
        if item:
            results.append(item)

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    conn.close()
    return results


def _apply_filters(conn, filters: dict) -> set[str]:
    conditions = []
    params = []

    if filters.get("author"):
        conditions.append("LOWER(author) LIKE ?")
        params.append(f"%{filters['author'].lower()}%")
    if filters.get("quality"):
        conditions.append("quality = ?")
        params.append(filters["quality"])
    if filters.get("type"):
        conditions.append("content_type = ?")
        params.append(filters["type"])
    if filters.get("depth"):
        conditions.append("depth = ?")
        params.append(filters["depth"])
    if filters.get("stance"):
        conditions.append("stance = ?")
        params.append(filters["stance"])
    if filters.get("vault_type"):
        conditions.append("vault_type = ?")
        params.append(filters["vault_type"])
    if filters.get("since"):
        conditions.append("date >= ?")
        params.append(filters["since"])
    if filters.get("origin"):
        conditions.append("origin LIKE ?")
        params.append(f"%{filters['origin']}%")

    where = " AND ".join(conditions) if conditions else "1=1"
    rows = conn.execute(
        f"SELECT filepath FROM vault_items WHERE {where}", params
    ).fetchall()
    paths = {r["filepath"] for r in rows}

    if filters.get("topic"):
        topic_rows = conn.execute("""
            SELECT vi.filepath FROM vault_items vi
            JOIN vault_topics vt ON vi.id = vt.item_id
            WHERE vt.topic = ?
        """, (filters["topic"],)).fetchall()
        topic_paths = {r["filepath"] for r in topic_rows}
        paths = paths & topic_paths if conditions else topic_paths

    return paths


def _get_item_metadata(conn, filepath: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM vault_items WHERE filepath = ?", (filepath,)
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    topics = conn.execute(
        "SELECT topic FROM vault_topics WHERE item_id = ?", (row["id"],)
    ).fetchall()
    item["topics"] = [t["topic"] for t in topics]
    return item


def search_grep(query: str) -> list[tuple[str, str]]:
    results = []
    for subdir in VAULT_SUBDIRS:
        d = VAULT_DIR / subdir
        if not d.exists():
            continue
        result = subprocess.run(
            ["grep", "-ril", "--include=*.md", query, str(d)],
            capture_output=True, text=True,
        )
        for f in result.stdout.strip().split("\n"):
            if f and ".index" not in f and "INDEX.md" not in f:
                results.append((Path(f).name, f"(encontrado en {Path(f).name})"))
    return results


# --- Output formatting ---

def format_results(results: list[dict], mode: str = "default") -> str:
    if not results:
        return "Sin resultados."

    lines = []
    for i, item in enumerate(results, 1):
        title = item.get("title") or item.get("filename", "?")
        author = item.get("author", "")
        date = item.get("date", "")
        ctype = item.get("content_type", "")
        quality = item.get("quality", "")
        depth = item.get("depth", "")
        topics = ", ".join(item.get("topics", []))

        meta_parts = [p for p in [ctype, depth, quality] if p]
        meta = ", ".join(meta_parts)

        header = f"{i}. [{date}] {title}"
        if author:
            header += f" — {author}"
        if meta:
            header += f" ({meta})"

        lines.append(header)

        if item.get("takeaway"):
            lines.append(f"   -> {item['takeaway'][:120]}")
        if topics:
            lines.append(f"   Topics: {topics}")

        if mode == "default" and item.get("snippet"):
            lines.append(f"   {item['snippet'][:200]}")

        lines.append(f"   [{item.get('filepath', '')}]")
        lines.append("")

    return "\n".join(lines)


def format_context_pack(results: list[dict], max_tokens: int = 3000) -> str:
    total = len(results)
    max_chars = max_tokens * CHARS_PER_TOKEN
    lines = []
    used = 0

    for i, item in enumerate(results, 1):
        title = item.get("title") or item.get("filename", "?")
        author = item.get("author", "")
        date = item.get("date", "")
        ctype = item.get("content_type", "")
        quality = item.get("quality", "")
        depth = item.get("depth", "")
        topics = ", ".join(item.get("topics", []))
        takeaway = item.get("takeaway", "")

        meta_parts = [p for p in [ctype, depth, quality] if p]
        meta = ", ".join(meta_parts)

        entry = f"{i}. [{date}] {title}"
        if author:
            entry += f" — {author}"
        if meta:
            entry += f" ({meta})"
        entry += "\n"
        if takeaway:
            entry += f"   -> {takeaway[:150]}\n"
        if topics:
            entry += f"   Topics: {topics}\n"

        if used + len(entry) > max_chars:
            lines.append(f"\n[... {total - i + 1} resultados más truncados por budget de tokens]")
            break

        lines.append(entry)
        used += len(entry)

    shown = len([l for l in lines if l and l[0].isdigit()])
    header = f"=== {shown} resultados (de {total} totales) ===\n"
    return header + "\n".join(lines)


# --- Stats and listings ---

def get_stats() -> dict:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)

    total = conn.execute("SELECT COUNT(*) FROM vault_items").fetchone()[0]
    by_type = conn.execute(
        "SELECT vault_type, COUNT(*) FROM vault_items GROUP BY vault_type"
    ).fetchall()
    by_quality = conn.execute(
        "SELECT quality, COUNT(*) FROM vault_items WHERE quality != '' GROUP BY quality"
    ).fetchall()
    by_ctype = conn.execute(
        "SELECT content_type, COUNT(*) FROM vault_items WHERE content_type != '' GROUP BY content_type"
    ).fetchall()
    top_topics = conn.execute("""
        SELECT topic, COUNT(*) as cnt FROM vault_topics
        GROUP BY topic ORDER BY cnt DESC LIMIT 10
    """).fetchall()
    top_authors = conn.execute("""
        SELECT author, COUNT(*) as cnt FROM vault_items
        WHERE author != '' GROUP BY author ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    conn.close()
    return {
        "total": total,
        "by_vault_type": dict(by_type),
        "by_quality": dict(by_quality),
        "by_content_type": dict(by_ctype),
        "top_topics": dict(top_topics),
        "top_authors": dict(top_authors),
    }


def list_topics() -> list[tuple[str, int]]:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)
    rows = conn.execute("""
        SELECT topic, COUNT(*) as cnt FROM vault_topics
        GROUP BY topic ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return rows


def list_authors() -> list[tuple[str, int]]:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)
    rows = conn.execute("""
        SELECT author, COUNT(*) as cnt FROM vault_items
        WHERE author != '' GROUP BY author ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return rows


def generate_index() -> str:
    _ensure_index()
    conn = sqlite3.connect(INDEX_PATH)
    conn.row_factory = sqlite3.Row

    lines = ["# Wisdom Index\n"]

    lines.append("## Por tema\n")
    topics = conn.execute(
        "SELECT DISTINCT topic FROM vault_topics ORDER BY topic"
    ).fetchall()
    for (topic,) in topics:
        lines.append(f"### {topic}")
        rows = conn.execute("""
            SELECT vi.filepath, vi.title, vi.takeaway, vi.author, vi.date
            FROM vault_items vi
            JOIN vault_topics vt ON vi.id = vt.item_id
            WHERE vt.topic = ? AND vi.vault_type = 'wisdom'
            ORDER BY vi.date DESC
        """, (topic,)).fetchall()
        for r in rows:
            takeaway = (r["takeaway"] or "")[:100]
            author = r["author"] or ""
            date = r["date"] or ""
            title = r["title"] or r["filepath"]
            lines.append(f"- [{title}]({r['filepath'].split('/')[-1]}) — {takeaway} ({author}, {date})")
        lines.append("")

    lines.append("## Recientes\n")
    recent = conn.execute("""
        SELECT filepath, title, content_type, date, takeaway
        FROM vault_items WHERE vault_type = 'wisdom'
        ORDER BY date DESC LIMIT 20
    """).fetchall()
    for r in recent:
        title = r["title"] or r["filepath"]
        ctype = r["content_type"] or ""
        date = r["date"] or ""
        topics_rows = conn.execute("""
            SELECT topic FROM vault_topics
            WHERE item_id = (SELECT id FROM vault_items WHERE filepath = ?)
        """, (r["filepath"],)).fetchall()
        topics_str = ", ".join(t[0] for t in topics_rows)
        lines.append(f"- {date} [{title}]({r['filepath'].split('/')[-1]}) — {ctype} — {topics_str}")

    conn.close()
    return "\n".join(lines) + "\n"


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Vault Search — Claudia OS")
    parser.add_argument("query", nargs="*", help="Full-text search query")
    parser.add_argument("--topic", help="Filter by topic")
    parser.add_argument("--author", help="Filter by author")
    parser.add_argument("--quality", choices=["alta", "media", "baja"], help="Filter by quality")
    parser.add_argument("--type", dest="content_type", help="Filter by content type (video, article, etc.)")
    parser.add_argument("--depth", choices=["normal", "deep"], help="Filter by depth")
    parser.add_argument("--stance", choices=["esceptico", "bullish", "neutral", "mixto"])
    parser.add_argument("--vault-type", choices=["wisdom", "research", "weekly-review"])
    parser.add_argument("--since", help="Filter items from date (YYYY-MM-DD)")
    parser.add_argument("--origin", help="Filter by origin (user, intake, research/...)")

    parser.add_argument("--context", metavar="QUERY_OR_TOPIC",
                        help="Context-pack mode: compact output for prompt injection")
    parser.add_argument("--max-tokens", type=int, default=3000, help="Token budget for --context")

    parser.add_argument("--list-topics", action="store_true", help="List all topics with counts")
    parser.add_argument("--list-authors", action="store_true", help="List all authors with counts")
    parser.add_argument("--stats", action="store_true", help="Show vault statistics")
    parser.add_argument("--rebuild", action="store_true", help="Force full index rebuild")
    parser.add_argument("--reindex-file", metavar="PATH", help="Reindex a single file (relative to vault/)")
    parser.add_argument("--generate-index", action="store_true",
                        help="Auto-generate INDEX.md from database")
    parser.add_argument("--status", action="store_true", help="Show index status")

    args = parser.parse_args()

    if args.rebuild:
        count = build_index()
        print(f"Index rebuilt: {count} files indexed.")
        return

    if args.reindex_file:
        ok = reindex_file(args.reindex_file)
        print(f"Reindexed: {args.reindex_file}" if ok else f"File not found: {args.reindex_file}")
        return

    if args.status:
        if not check_fts5():
            print("Mode: BASIC (grep) — FTS5 unavailable")
            return
        if not INDEX_PATH.exists():
            print("Mode: FULL (SQLite FTS5) — index not built yet")
            return
        conn = sqlite3.connect(INDEX_PATH)
        count = conn.execute("SELECT COUNT(*) FROM vault_items").fetchone()[0]
        conn.close()
        size_kb = INDEX_PATH.stat().st_size // 1024
        print(f"Mode: FULL (SQLite FTS5)")
        print(f"Index: {count} items ({size_kb} KB)")
        print(f"Path: {INDEX_PATH}")
        return

    if args.stats:
        stats = get_stats()
        print(f"Total items: {stats['total']}\n")
        print("By vault type:")
        for k, v in stats["by_vault_type"].items():
            print(f"  {k}: {v}")
        print("\nBy quality:")
        for k, v in stats["by_quality"].items():
            print(f"  {k}: {v}")
        print("\nBy content type:")
        for k, v in stats["by_content_type"].items():
            print(f"  {k}: {v}")
        print("\nTop topics:")
        for k, v in stats["top_topics"].items():
            print(f"  {k}: {v}")
        print("\nTop authors:")
        for k, v in stats["top_authors"].items():
            print(f"  {k}: {v}")
        return

    if args.list_topics:
        for topic, count in list_topics():
            print(f"  {topic}: {count}")
        return

    if args.list_authors:
        for author, count in list_authors():
            print(f"  {author}: {count}")
        return

    if args.generate_index:
        content = generate_index()
        index_path = VAULT_DIR / "wisdom" / "INDEX.md"
        index_path.write_text(content)
        print(f"INDEX.md generated at {index_path}")
        return

    filters = {}
    if args.topic:
        filters["topic"] = args.topic
    if args.author:
        filters["author"] = args.author
    if args.quality:
        filters["quality"] = args.quality
    if args.content_type:
        filters["type"] = args.content_type
    if args.depth:
        filters["depth"] = args.depth
    if args.stance:
        filters["stance"] = args.stance
    if args.vault_type:
        filters["vault_type"] = args.vault_type
    if args.since:
        filters["since"] = args.since
    if args.origin:
        filters["origin"] = args.origin

    if args.context:
        query_text = " ".join(args.query) if args.query else ""
        if not filters.get("topic"):
            filters["topic"] = args.context
        if query_text:
            results = search_fts(query_text, filters)
        elif filters:
            results = search_structured(filters)
        else:
            results = search_structured({})
        print(format_context_pack(results, args.context and args.max_tokens or 3000))
        return

    query_text = " ".join(args.query) if args.query else ""

    if not check_fts5():
        if query_text:
            results = search_grep(query_text)
            print(f"Results for '{query_text}' [mode: grep]\n")
            for fname, snippet in results:
                print(f"  {fname}")
                print(f"  {snippet}\n")
        else:
            print("FTS5 unavailable. Use a text query for grep fallback.")
        return

    if query_text and filters:
        results = search_fts(query_text, filters)
    elif query_text:
        results = search_fts(query_text)
    elif filters:
        results = search_structured(filters)
    else:
        parser.print_help()
        return

    print(format_results(results))


if __name__ == "__main__":
    main()

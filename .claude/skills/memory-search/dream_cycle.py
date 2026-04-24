#!/usr/bin/env python3
"""
Claudia OS — Dream Cycle
Nightly compression of episodic memory into semantic lessons.

Runs via cron (ejemplo: 3am cada noche; sustituye /ruta/a/claudia-os
por la ruta absoluta de tu clon):
  0 3 * * * cd /ruta/a/claudia-os && python3 .claude/skills/memory-search/dream_cycle.py

Steps:
  1. Load AGENT_LEARNINGS.jsonl
  2. Detect recurring patterns (same skill+action prefix, ≥2 times)
  3. Promote high-salience recurring patterns (score ≥7.0) to semantic/LESSONS.md
  4. Decay old low-salience entries (>90 days, score <2.0) to episodes/snapshots/
  5. Archive WORKSPACE.md if it has active content
  6. Git commit the result

Adapted from github.com/codejunkie99/agentic-stack (MIT License, Copyright 2026 Avid).
"""
import datetime
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MEMORY_DIR = REPO_ROOT / "user" / "memory"
EPISODIC_PATH = MEMORY_DIR / "episodes" / "AGENT_LEARNINGS.jsonl"
SNAPSHOTS_DIR = MEMORY_DIR / "episodes" / "snapshots"
LESSONS_PATH = MEMORY_DIR / "semantic" / "LESSONS.md"
WORKSPACE_PATH = MEMORY_DIR / "working" / "WORKSPACE.md"

PROMOTION_THRESHOLD = 7.0
DECAY_DAYS = 90
SALIENCE_FLOOR = 2.0


# --- Salience (inlined to avoid import path issues in cron) ---

def salience_score(entry: dict) -> float:
    ts = entry.get("timestamp")
    if not ts:
        return 0.0
    try:
        age_days = (datetime.datetime.now() - datetime.datetime.fromisoformat(ts)).days
    except ValueError:
        age_days = 999
    pain = entry.get("pain_score", 5)
    importance = entry.get("importance", 5)
    recurrence = entry.get("recurrence_count", 1)
    recency = max(0.0, 10.0 - age_days * 0.3)
    return recency * (pain / 10.0) * (importance / 10.0) * min(recurrence, 3)


# --- Load / write episodic ---

def load_entries() -> list[dict]:
    if not EPISODIC_PATH.exists():
        return []
    entries = []
    for line in EPISODIC_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def write_entries(entries: list[dict]):
    with open(EPISODIC_PATH, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# --- Promote recurring patterns to semantic/LESSONS.md ---

def find_recurring(entries: list[dict]) -> list[dict]:
    groups: dict[str, list] = defaultdict(list)
    for e in entries:
        key = f"{e.get('skill', 'general')}::{e.get('action', '')[:50]}"
        groups[key].append(e)

    promotable = []
    for group in groups.values():
        if len(group) < 2:
            continue
        best = max(group, key=salience_score)
        best = dict(best)
        best["recurrence_count"] = len(group)
        score = salience_score(best)
        if score >= PROMOTION_THRESHOLD:
            best["_salience"] = score
            promotable.append(best)
    return promotable


def promote_to_lessons(promotable: list[dict]) -> int:
    if not promotable:
        return 0
    existing = LESSONS_PATH.read_text(encoding="utf-8") if LESSONS_PATH.exists() else ""
    new_lines = []
    for e in promotable:
        lesson = e.get("reflection") or e.get("action") or "unknown"
        line = f"- [{e.get('skill', '?')}] {lesson}"
        if line not in existing:
            new_lines.append(line)
    if not new_lines:
        return 0
    LESSONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LESSONS_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n## Auto-promovido {datetime.date.today().isoformat()}\n")
        for line in new_lines:
            f.write(line + "\n")
    return len(new_lines)


# --- Decay old low-salience entries ---

def decay_entries(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    cutoff = datetime.datetime.now() - datetime.timedelta(days=DECAY_DAYS)
    kept, archived = [], []
    for e in entries:
        try:
            ts = datetime.datetime.fromisoformat(e.get("timestamp", ""))
        except ValueError:
            kept.append(e)
            continue
        if ts < cutoff and salience_score(e) < SALIENCE_FLOOR:
            archived.append(e)
        else:
            kept.append(e)
    if archived:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = SNAPSHOTS_DIR / f"archive_{datetime.date.today().isoformat()}.jsonl"
        with open(archive_path, "a", encoding="utf-8") as f:
            for e in archived:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return kept, archived


# --- Archive WORKSPACE.md if it has active content ---

def archive_workspace() -> bool:
    if not WORKSPACE_PATH.exists():
        return False
    content = WORKSPACE_PATH.read_text(encoding="utf-8").strip()
    if not content or "_(sin tarea activa)_" in content:
        return False
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = SNAPSHOTS_DIR / f"WORKSPACE_{datetime.date.today().isoformat()}.md"
    dest.write_text(content, encoding="utf-8")
    WORKSPACE_PATH.write_text(
        "# Workspace — estado de tarea actual\n\n_(sin tarea activa)_\n",
        encoding="utf-8"
    )
    return True


# --- Git snapshot ---

def git_commit(promoted: int, decayed: int, kept: int, ws_archived: bool) -> str:
    msg = f"dream cycle: promoted={promoted} decayed={decayed} kept={kept}"
    if ws_archived:
        msg += " workspace=archived"
    try:
        subprocess.run(["git", "add", str(MEMORY_DIR)], check=False, cwd=REPO_ROOT)
        subprocess.run(["git", "commit", "-m", msg], check=False, cwd=REPO_ROOT)
    except FileNotFoundError:
        pass
    return msg


# --- Main ---

def run():
    entries = load_entries()
    if not entries:
        print(f"dream cycle ({datetime.date.today()}): no episodic entries — nothing to do")
        return

    recurring = find_recurring(entries)
    promoted = promote_to_lessons(recurring)

    kept, archived = decay_entries(entries)
    write_entries(kept)

    ws_archived = archive_workspace()

    commit_msg = git_commit(promoted, len(archived), len(kept), ws_archived)
    print(commit_msg)


if __name__ == "__main__":
    run()

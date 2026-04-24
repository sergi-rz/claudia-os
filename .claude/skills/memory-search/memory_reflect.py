#!/usr/bin/env python3
"""
Claudia OS — Memory Reflect
Appends a structured entry to the episodic log (AGENT_LEARNINGS.jsonl).
Call after any significant action, success or failure.

Usage:
  memory_reflect.py --skill <name> --action <desc> --importance <1-10>
                    [--pain <1-10>] [--reflection <text>]
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EPISODIC_PATH = REPO_ROOT / "user" / "memory" / "episodes" / "AGENT_LEARNINGS.jsonl"


def append_entry(skill: str, action: str, importance: int,
                 pain_score: int = 3, reflection: str = "") -> dict:
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "skill": skill,
        "action": action,
        "pain_score": max(1, min(10, pain_score)),
        "importance": max(1, min(10, importance)),
        "recurrence_count": 1,
        "reflection": reflection,
    }
    EPISODIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EPISODIC_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main():
    p = argparse.ArgumentParser(description="Log an entry to episodic memory.")
    p.add_argument("--skill", required=True, help="Skill or context (e.g. 'claudia-research')")
    p.add_argument("--action", required=True, help="What happened (1 line)")
    p.add_argument("--importance", type=int, default=5, help="1-10, how important to remember")
    p.add_argument("--pain", type=int, default=3, help="1-10, cost of failure (1 if success)")
    p.add_argument("--reflection", default="", help="Distilled lesson (optional)")
    args = p.parse_args()

    entry = append_entry(
        skill=args.skill,
        action=args.action,
        importance=args.importance,
        pain_score=args.pain,
        reflection=args.reflection,
    )
    print(f"Logged: [{entry['skill']}] {entry['action']} "
          f"(importance={entry['importance']}, pain={entry['pain_score']})")


if __name__ == "__main__":
    main()

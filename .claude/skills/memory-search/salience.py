"""
Salience scoring for episodic memory entries.

Formula: recency * (pain/10) * (importance/10) * min(recurrence, 3)

Adapted from github.com/codejunkie99/agentic-stack (MIT License, Copyright 2026 Avid).
"""
import datetime


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

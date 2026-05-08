#!/usr/bin/env python3
"""SQLite schema for YouTube analytics data. One database per channel."""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
DATA_DIR = os.path.join(CLAUDIA_ROOT, 'user', 'data', 'yt-analytics')

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS channel (
    channel_id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    subscriber_count INTEGER,
    video_count INTEGER,
    view_count INTEGER,
    custom_url TEXT,
    thumbnail_url TEXT,
    uploads_playlist_id TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    published_at TEXT NOT NULL,
    duration_seconds INTEGER,
    tags TEXT,
    category_id TEXT,
    thumbnail_url TEXT,
    is_short INTEGER DEFAULT 0,
    corpus_file TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video_metrics (
    video_id TEXT NOT NULL REFERENCES videos(video_id),
    date TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    watch_time_minutes REAL DEFAULT 0,
    average_view_duration_seconds REAL DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    subscribers_gained INTEGER DEFAULT 0,
    subscribers_lost INTEGER DEFAULT 0,
    estimated_revenue REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, date)
);

CREATE TABLE IF NOT EXISTS channel_metrics (
    date TEXT PRIMARY KEY,
    views INTEGER DEFAULT 0,
    watch_time_minutes REAL DEFAULT 0,
    subscribers_gained INTEGER DEFAULT 0,
    subscribers_lost INTEGER DEFAULT 0,
    estimated_revenue REAL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS traffic_sources (
    video_id TEXT NOT NULL REFERENCES videos(video_id),
    source_type TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    watch_time_minutes REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, source_type)
);

CREATE TABLE IF NOT EXISTS demographics (
    video_id TEXT NOT NULL REFERENCES videos(video_id),
    age_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    viewer_percentage REAL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (video_id, age_group, gender)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    videos_processed INTEGER DEFAULT 0,
    date_range_start TEXT,
    date_range_end TEXT,
    status TEXT DEFAULT 'running',
    error_message TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts
USING fts5(video_id, title, description, tags, tokenize='porter unicode61');

PRAGMA user_version = 1;
"""


def get_db(channel_id):
    os.makedirs(DATA_DIR, exist_ok=True)
    db_path = os.path.join(DATA_DIR, f'{channel_id}.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        conn.executescript(SCHEMA_SQL)

    return conn

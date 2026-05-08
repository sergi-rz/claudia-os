#!/usr/bin/env python3
"""
Claudia OS — YouTube Analytics CLI.

Uso:
    python3 yt_analytics.py --action sync --channel mi-canal [--full] [--since 2025-01-01]
    python3 yt_analytics.py --action overview --channel mi-canal
    python3 yt_analytics.py --action video-stats --channel mi-canal [--top 10] [--sort views]
    python3 yt_analytics.py --action trends --channel mi-canal [--period 30d]
    python3 yt_analytics.py --action traffic --channel mi-canal [--video-id X]
    python3 yt_analytics.py --action demographics --channel mi-canal
    python3 yt_analytics.py --action compare --channel mi-canal --videos "id1,id2"
    python3 yt_analytics.py --action corpus-link --channel mi-canal --workspace mi-workspace
    python3 yt_analytics.py --action search --channel mi-canal --query "vibe coding"
    python3 yt_analytics.py --action accounts
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDIA_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
YT_CREDS_DIR = os.path.join(CLAUDIA_ROOT, 'user', 'credentials', 'youtube')
TOKENS_DIR = os.path.join(YT_CREDS_DIR, 'tokens')
SETTINGS_FILE = os.path.join(CLAUDIA_ROOT, 'user', 'config', 'settings.json')

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
    'https://www.googleapis.com/auth/yt-analytics-monetary.readonly',
]

sys.path.insert(0, SCRIPT_DIR)
from schema import get_db  # noqa: E402
from fetchers.data_api import fetch_channel_info, fetch_all_video_ids, fetch_video_details  # noqa: E402
from fetchers.analytics_api import (  # noqa: E402
    fetch_video_metrics, fetch_channel_metrics, fetch_traffic_sources, fetch_demographics,
)


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE) as f:
        return json.load(f).get('skill_yt_analytics', {})


def resolve_channel(args, settings):
    name = args.channel or settings.get('default_channel')
    if not name:
        print(json.dumps({'error': 'No se ha especificado canal. Usa --channel o configura default_channel en settings.json'}))
        sys.exit(1)

    channels = settings.get('channels', {})
    if name not in channels:
        print(json.dumps({'error': f"Canal '{name}' no encontrado en settings.json. Canales disponibles: {list(channels)}"}))
        sys.exit(1)

    return name, channels[name]


def load_credentials(token_name):
    token_path = os.path.join(TOKENS_DIR, f'{token_name}.json')
    if not os.path.exists(token_path):
        print(json.dumps({'error': f"No hay token para '{token_name}'. Ejecuta: python3 auth.py {token_name}"}))
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            print(json.dumps({'error': f"Token expirado para '{token_name}'. Ejecuta: python3 auth.py {token_name}"}))
            sys.exit(1)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return creds


def get_services(token_name):
    creds = load_credentials(token_name)
    yt = build('youtube', 'v3', credentials=creds)
    analytics = build('youtubeAnalytics', 'v2', credentials=creds)
    return yt, analytics


# --- Actions ---

def action_accounts():
    if not os.path.exists(TOKENS_DIR):
        print(json.dumps({'accounts': []}))
        return
    accounts = [f.replace('.json', '') for f in os.listdir(TOKENS_DIR) if f.endswith('.json')]
    print(json.dumps({'accounts': accounts}))


def action_sync(args, settings):
    name, channel_cfg = resolve_channel(args, settings)
    channel_id = channel_cfg['channel_id']
    token_name = channel_cfg.get('token', name)
    ignore_shorts = settings.get('ignore_shorts', True)

    yt, analytics = get_services(token_name)
    conn = get_db(channel_id)
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO sync_log (sync_type, started_at, status) VALUES (?, ?, ?)",
        ('full_sync' if args.full else 'incremental', now, 'running'),
    )
    sync_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    try:
        # 1. Channel info
        print(f"[sync] Fetching channel info for {channel_id}...")
        info = fetch_channel_info(yt, channel_id)
        if not info:
            raise ValueError(f"Canal {channel_id} no encontrado")

        conn.execute("""
            INSERT OR REPLACE INTO channel
            (channel_id, title, description, subscriber_count, video_count,
             view_count, custom_url, thumbnail_url, uploads_playlist_id, updated_at)
            VALUES (:channel_id, :title, :description, :subscriber_count, :video_count,
                    :view_count, :custom_url, :thumbnail_url, :uploads_playlist_id, :updated_at)
        """, info)

        # 2. Video list
        print("[sync] Fetching video list...")
        all_ids = fetch_all_video_ids(yt, info['uploads_playlist_id'])
        print(f"[sync] Found {len(all_ids)} videos in channel")

        # 3. Video details
        existing = {r[0] for r in conn.execute("SELECT video_id FROM videos").fetchall()}
        new_ids = [vid for vid in all_ids if vid not in existing]

        if args.full:
            fetch_ids = all_ids
        else:
            fetch_ids = new_ids if new_ids else []

        if fetch_ids:
            print(f"[sync] Fetching details for {len(fetch_ids)} videos...")
            details = fetch_video_details(yt, fetch_ids)
            for v in details:
                if ignore_shorts and v['is_short']:
                    continue
                conn.execute("""
                    INSERT OR REPLACE INTO videos
                    (video_id, title, description, published_at, duration_seconds,
                     tags, category_id, thumbnail_url, is_short, updated_at)
                    VALUES (:video_id, :title, :description, :published_at, :duration_seconds,
                            :tags, :category_id, :thumbnail_url, :is_short, :updated_at)
                """, {**v, 'tags': json.dumps(v['tags'])})

                # FTS index
                conn.execute("DELETE FROM videos_fts WHERE video_id = ?", (v['video_id'],))
                conn.execute(
                    "INSERT INTO videos_fts (video_id, title, description, tags) VALUES (?, ?, ?, ?)",
                    (v['video_id'], v['title'], v['description'], ' '.join(v['tags'])),
                )

        # 4. Analytics metrics
        video_ids_in_db = [r[0] for r in conn.execute(
            "SELECT video_id FROM videos WHERE is_short = 0"
        ).fetchall()]

        if video_ids_in_db:
            sync_days = settings.get('sync_days_back', 90)
            if args.since:
                start_date = datetime.strptime(args.since, '%Y-%m-%d')
            elif args.full:
                earliest = conn.execute("SELECT MIN(published_at) FROM videos").fetchone()[0]
                start_date = datetime.strptime(earliest, '%Y-%m-%d') if earliest else datetime.now(timezone.utc) - timedelta(days=365)
            else:
                last_sync = conn.execute(
                    "SELECT MAX(date_range_end) FROM sync_log WHERE status = 'completed'"
                ).fetchone()[0]
                if last_sync:
                    start_date = datetime.strptime(last_sync, '%Y-%m-%d') - timedelta(days=3)
                else:
                    start_date = datetime.now(timezone.utc) - timedelta(days=sync_days)

            print(f"[sync] Fetching analytics from {start_date.strftime('%Y-%m-%d')}...")

            # Video metrics
            metrics = fetch_video_metrics(analytics, channel_id, video_ids_in_db, start_date)
            for m in metrics:
                conn.execute("""
                    INSERT OR REPLACE INTO video_metrics
                    (video_id, date, views, watch_time_minutes, average_view_duration_seconds,
                     likes, dislikes, comments, shares,
                     subscribers_gained, subscribers_lost, updated_at)
                    VALUES (:video_id, :date, :views, :watch_time_minutes, :average_view_duration_seconds,
                            :likes, :dislikes, :comments, :shares,
                            :subscribers_gained, :subscribers_lost, :updated_at)
                """, m)
            print(f"[sync] Stored {len(metrics)} metric rows")

            # Channel metrics
            ch_metrics = fetch_channel_metrics(analytics, channel_id, start_date)
            for m in ch_metrics:
                conn.execute("""
                    INSERT OR REPLACE INTO channel_metrics
                    (date, views, watch_time_minutes, subscribers_gained,
                     subscribers_lost, estimated_revenue, updated_at)
                    VALUES (:date, :views, :watch_time_minutes, :subscribers_gained,
                            :subscribers_lost, :estimated_revenue, :updated_at)
                """, m)
            print(f"[sync] Stored {len(ch_metrics)} channel metric rows")

            # Traffic sources
            traffic = fetch_traffic_sources(analytics, channel_id, video_ids_in_db)
            for t in traffic:
                conn.execute("""
                    INSERT OR REPLACE INTO traffic_sources
                    (video_id, source_type, views, watch_time_minutes, updated_at)
                    VALUES (:video_id, :source_type, :views, :watch_time_minutes, :updated_at)
                """, t)
            print(f"[sync] Stored {len(traffic)} traffic source rows")

            # Demographics
            demo = fetch_demographics(analytics, channel_id, video_ids_in_db)
            for d in demo:
                conn.execute("""
                    INSERT OR REPLACE INTO demographics
                    (video_id, age_group, gender, viewer_percentage, updated_at)
                    VALUES (:video_id, :age_group, :gender, :viewer_percentage, :updated_at)
                """, d)
            print(f"[sync] Stored {len(demo)} demographic rows")

        end_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%d')
        conn.execute("""
            UPDATE sync_log SET completed_at = ?, videos_processed = ?,
            date_range_start = ?, date_range_end = ?, status = 'completed'
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), len(video_ids_in_db),
              start_date.strftime('%Y-%m-%d') if video_ids_in_db else None,
              end_date if video_ids_in_db else None, sync_id))
        conn.commit()

        total_videos = conn.execute("SELECT COUNT(*) FROM videos WHERE is_short = 0").fetchone()[0]
        print(f"\n[sync] Done. {total_videos} videos in DB.")

    except Exception as e:
        conn.execute(
            "UPDATE sync_log SET completed_at = ?, status = 'error', error_message = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), str(e), sync_id),
        )
        conn.commit()
        print(json.dumps({'error': str(e)}))
        sys.exit(1)
    finally:
        conn.close()


def action_overview(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    channel = conn.execute("SELECT * FROM channel LIMIT 1").fetchone()
    if not channel:
        print(json.dumps({'error': 'No hay datos. Ejecuta --action sync primero.'}))
        conn.close()
        return

    total_videos = conn.execute("SELECT COUNT(*) FROM videos WHERE is_short = 0").fetchone()[0]

    last_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
    last_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')

    stats_30d = conn.execute("""
        SELECT SUM(views), SUM(watch_time_minutes), SUM(subscribers_gained), SUM(subscribers_lost), SUM(estimated_revenue)
        FROM channel_metrics WHERE date >= ?
    """, (last_30d,)).fetchone()

    stats_7d = conn.execute("""
        SELECT SUM(views), SUM(watch_time_minutes), SUM(subscribers_gained), SUM(subscribers_lost), SUM(estimated_revenue)
        FROM channel_metrics WHERE date >= ?
    """, (last_7d,)).fetchone()

    last_sync = conn.execute(
        "SELECT completed_at, date_range_start, date_range_end FROM sync_log WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    result = {
        'channel': {
            'title': channel['title'],
            'subscribers': channel['subscriber_count'],
            'total_views': channel['view_count'],
            'total_videos': total_videos,
            'updated_at': channel['updated_at'],
        },
        'last_30_days': {
            'views': stats_30d[0] or 0,
            'watch_time_hours': round((stats_30d[1] or 0) / 60, 1),
            'subscribers_gained': stats_30d[2] or 0,
            'subscribers_lost': stats_30d[3] or 0,
            'net_subscribers': (stats_30d[2] or 0) - (stats_30d[3] or 0),
            'estimated_revenue': round(stats_30d[4] or 0, 2),
        },
        'last_7_days': {
            'views': stats_7d[0] or 0,
            'watch_time_hours': round((stats_7d[1] or 0) / 60, 1),
            'subscribers_gained': stats_7d[2] or 0,
            'subscribers_lost': stats_7d[3] or 0,
            'net_subscribers': (stats_7d[2] or 0) - (stats_7d[3] or 0),
            'estimated_revenue': round(stats_7d[4] or 0, 2),
        },
        'last_sync': {
            'completed_at': last_sync['completed_at'] if last_sync else None,
            'date_range': f"{last_sync['date_range_start']} to {last_sync['date_range_end']}" if last_sync else None,
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    conn.close()


def action_video_stats(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    top_n = args.top or 10
    sort_field = args.sort or 'views'

    sort_map = {
        'views': 'SUM(m.views)',
        'ctr': 'AVG(m.ctr)',
        'retention': 'AVG(m.average_view_duration_seconds)',
        'subs': 'SUM(m.subscribers_gained) - SUM(m.subscribers_lost)',
        'watch_time': 'SUM(m.watch_time_minutes)',
    }
    order_expr = sort_map.get(sort_field, sort_map['views'])

    rows = conn.execute(f"""
        SELECT v.video_id, v.title, v.published_at, v.duration_seconds, v.corpus_file,
               SUM(m.views) as total_views,
               ROUND(SUM(m.watch_time_minutes) / 60.0, 1) as watch_time_hours,
               ROUND(AVG(m.average_view_duration_seconds), 0) as avg_view_duration,
               ROUND(AVG(m.ctr) * 100, 2) as avg_ctr_pct,
               SUM(m.impressions) as total_impressions,
               SUM(m.likes) as total_likes,
               SUM(m.comments) as total_comments,
               SUM(m.subscribers_gained) as subs_gained,
               SUM(m.subscribers_lost) as subs_lost
        FROM videos v
        LEFT JOIN video_metrics m ON v.video_id = m.video_id
        WHERE v.is_short = 0
        GROUP BY v.video_id
        ORDER BY {order_expr} DESC
        LIMIT ?
    """, (top_n,)).fetchall()

    result = []
    for r in rows:
        result.append({
            'video_id': r['video_id'],
            'title': r['title'],
            'published_at': r['published_at'],
            'duration_seconds': r['duration_seconds'],
            'has_corpus': r['corpus_file'] is not None,
            'corpus_file': r['corpus_file'],
            'total_views': r['total_views'] or 0,
            'watch_time_hours': r['watch_time_hours'] or 0,
            'avg_view_duration_seconds': r['avg_view_duration'] or 0,
            'avg_ctr_pct': r['avg_ctr_pct'] or 0,
            'total_impressions': r['total_impressions'] or 0,
            'total_likes': r['total_likes'] or 0,
            'total_comments': r['total_comments'] or 0,
            'net_subscribers': (r['subs_gained'] or 0) - (r['subs_lost'] or 0),
        })

    print(json.dumps({'videos': result, 'sort': sort_field, 'count': len(result)}, indent=2, ensure_ascii=False))
    conn.close()


def action_trends(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    period = args.period or '30d'
    days = int(period.replace('d', '').replace('y', '')) * (365 if 'y' in period else 1)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')

    rows = conn.execute("""
        SELECT date, views, watch_time_minutes, subscribers_gained, subscribers_lost, estimated_revenue
        FROM channel_metrics
        WHERE date >= ?
        ORDER BY date
    """, (since,)).fetchall()

    data = [dict(r) for r in rows]

    if len(data) > 1:
        mid = len(data) // 2
        first_half = data[:mid]
        second_half = data[mid:]
        trend = {
            'first_half_avg_views': round(sum(d['views'] for d in first_half) / len(first_half), 1),
            'second_half_avg_views': round(sum(d['views'] for d in second_half) / len(second_half), 1),
            'first_half_avg_subs': round(sum(d['subscribers_gained'] - d['subscribers_lost'] for d in first_half) / len(first_half), 2),
            'second_half_avg_subs': round(sum(d['subscribers_gained'] - d['subscribers_lost'] for d in second_half) / len(second_half), 2),
        }
    else:
        trend = None

    print(json.dumps({'period': period, 'days': len(data), 'trend': trend, 'daily': data}, indent=2, ensure_ascii=False))
    conn.close()


def action_traffic(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    if args.video_id:
        rows = conn.execute("""
            SELECT source_type, views, watch_time_minutes
            FROM traffic_sources WHERE video_id = ?
            ORDER BY views DESC
        """, (args.video_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT source_type, SUM(views) as views, SUM(watch_time_minutes) as watch_time_minutes
            FROM traffic_sources
            GROUP BY source_type
            ORDER BY views DESC
        """).fetchall()

    result = [dict(r) for r in rows]
    total_views = sum(r['views'] for r in result)
    for r in result:
        r['percentage'] = round(r['views'] / total_views * 100, 1) if total_views else 0

    print(json.dumps({'sources': result, 'total_views': total_views, 'video_id': args.video_id}, indent=2, ensure_ascii=False))
    conn.close()


def action_demographics(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    rows = conn.execute("""
        SELECT age_group, gender, ROUND(AVG(viewer_percentage), 2) as avg_pct
        FROM demographics
        GROUP BY age_group, gender
        ORDER BY avg_pct DESC
    """).fetchall()

    result = [dict(r) for r in rows]
    print(json.dumps({'demographics': result}, indent=2, ensure_ascii=False))
    conn.close()


def action_compare(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    video_ids = [v.strip() for v in args.videos.split(',')]
    placeholders = ','.join('?' * len(video_ids))

    rows = conn.execute(f"""
        SELECT v.video_id, v.title, v.published_at, v.duration_seconds, v.corpus_file,
               SUM(m.views) as total_views,
               ROUND(SUM(m.watch_time_minutes) / 60.0, 1) as watch_time_hours,
               ROUND(AVG(m.average_view_duration_seconds), 0) as avg_view_duration,
               ROUND(AVG(m.ctr) * 100, 2) as avg_ctr_pct,
               SUM(m.subscribers_gained) - SUM(m.subscribers_lost) as net_subs
        FROM videos v
        LEFT JOIN video_metrics m ON v.video_id = m.video_id
        WHERE v.video_id IN ({placeholders})
        GROUP BY v.video_id
    """, video_ids).fetchall()

    result = [dict(r) for r in rows]
    print(json.dumps({'comparison': result}, indent=2, ensure_ascii=False))
    conn.close()


def action_corpus_link(args, settings):
    name, channel_cfg = resolve_channel(args, settings)
    workspace = args.workspace or channel_cfg.get('workspace')
    if not workspace:
        print(json.dumps({'error': 'No se ha especificado workspace. Usa --workspace o configúralo en settings.json'}))
        return

    corpus_dir = os.path.join(CLAUDIA_ROOT, 'user', 'workspaces', workspace, 'yt', 'corpus')
    if not os.path.exists(corpus_dir):
        print(json.dumps({'error': f'No existe el directorio de corpus: {corpus_dir}'}))
        return

    conn = get_db(channel_cfg['channel_id'])
    matched = 0
    unmatched_corpus = 0
    video_id_pattern = re.compile(r'youtube\.com/watch\?v=([A-Za-z0-9_-]+)')

    for filename in sorted(os.listdir(corpus_dir)):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(corpus_dir, filename)
        video_id = None
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                m = video_id_pattern.search(line)
                if m:
                    video_id = m.group(1)
                    break

        if not video_id:
            continue

        relative_path = os.path.join('yt', 'corpus', filename)
        updated = conn.execute(
            "UPDATE videos SET corpus_file = ? WHERE video_id = ?",
            (relative_path, video_id),
        ).rowcount

        if updated:
            matched += 1
        else:
            unmatched_corpus += 1

    conn.commit()

    total_videos = conn.execute("SELECT COUNT(*) FROM videos WHERE is_short = 0").fetchone()[0]
    linked = conn.execute("SELECT COUNT(*) FROM videos WHERE corpus_file IS NOT NULL").fetchone()[0]

    result = {
        'matched_this_run': matched,
        'unmatched_corpus_files': unmatched_corpus,
        'total_videos_in_db': total_videos,
        'total_linked': linked,
        'total_unlinked': total_videos - linked,
    }
    print(json.dumps(result, indent=2))
    conn.close()


def action_search(args, settings):
    _, channel_cfg = resolve_channel(args, settings)
    conn = get_db(channel_cfg['channel_id'])

    rows = conn.execute("""
        SELECT v.video_id, v.title, v.published_at, v.duration_seconds, v.corpus_file
        FROM videos_fts fts
        JOIN videos v ON fts.video_id = v.video_id
        WHERE videos_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """, (args.query,)).fetchall()

    result = [dict(r) for r in rows]
    print(json.dumps({'results': result, 'query': args.query}, indent=2, ensure_ascii=False))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='YouTube Analytics CLI')
    parser.add_argument('--action', required=True,
                        choices=['sync', 'overview', 'video-stats', 'trends',
                                 'traffic', 'demographics', 'compare',
                                 'corpus-link', 'search', 'accounts'])
    parser.add_argument('--channel', help='Nombre del canal (clave en settings.json)')
    parser.add_argument('--full', action='store_true', help='Sync completo (no incremental)')
    parser.add_argument('--since', help='Fecha de inicio para sync (YYYY-MM-DD)')
    parser.add_argument('--top', type=int, help='Número de resultados (default: 10)')
    parser.add_argument('--sort', choices=['views', 'ctr', 'retention', 'subs', 'watch_time'])
    parser.add_argument('--period', help='Periodo para trends: 30d, 90d, 1y')
    parser.add_argument('--video-id', help='ID de vídeo específico')
    parser.add_argument('--videos', help='IDs de vídeos separados por coma')
    parser.add_argument('--workspace', help='Nombre del workspace para corpus-link')
    parser.add_argument('--query', help='Texto de búsqueda')
    args = parser.parse_args()

    settings = load_settings()

    if args.action == 'accounts':
        action_accounts()
    elif args.action == 'sync':
        action_sync(args, settings)
    elif args.action == 'overview':
        action_overview(args, settings)
    elif args.action == 'video-stats':
        action_video_stats(args, settings)
    elif args.action == 'trends':
        action_trends(args, settings)
    elif args.action == 'traffic':
        action_traffic(args, settings)
    elif args.action == 'demographics':
        action_demographics(args, settings)
    elif args.action == 'compare':
        action_compare(args, settings)
    elif args.action == 'corpus-link':
        action_corpus_link(args, settings)
    elif args.action == 'search':
        action_search(args, settings)


if __name__ == '__main__':
    main()

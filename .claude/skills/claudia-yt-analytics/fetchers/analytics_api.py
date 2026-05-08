"""YouTube Analytics API — metrics, traffic sources, demographics."""

from datetime import datetime, timedelta, timezone

METRICS_FIELDS = (
    'views,estimatedMinutesWatched,averageViewDuration,'
    'likes,dislikes,comments,shares,'
    'subscribersGained,subscribersLost'
)

CHANNEL_METRICS_FIELDS = (
    'views,estimatedMinutesWatched,'
    'subscribersGained,subscribersLost'
)


def _date_str(d):
    return d.strftime('%Y-%m-%d')


def _default_end_date():
    return datetime.now(timezone.utc) - timedelta(days=2)


def fetch_video_metrics(analytics, channel_id, video_ids, start_date, end_date=None):
    """Daily metrics per video. Batches video_ids to stay within API limits."""
    if end_date is None:
        end_date = _default_end_date()

    rows = []
    now = datetime.now(timezone.utc).isoformat()

    for i in range(0, len(video_ids), 200):
        batch = video_ids[i:i + 200]
        filters = f"video=={','.join(batch)}"

        try:
            resp = analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=_date_str(start_date),
                endDate=_date_str(end_date),
                metrics=METRICS_FIELDS,
                dimensions='video,day',
                filters=filters,
                sort='day',
                maxResults=10000,
            ).execute()
        except Exception as e:
            print(f"  [analytics] Error fetching metrics batch {i}: {e}")
            continue

        for row in resp.get('rows', []):
            rows.append({
                'video_id': row[0],
                'date': row[1],
                'views': row[2],
                'watch_time_minutes': row[3],
                'average_view_duration_seconds': row[4],
                'likes': row[5],
                'dislikes': row[6],
                'comments': row[7],
                'shares': row[8],
                'subscribers_gained': row[9],
                'subscribers_lost': row[10],
                'updated_at': now,
            })

    return rows


def fetch_channel_metrics(analytics, channel_id, start_date, end_date=None):
    """Daily channel-level aggregates."""
    if end_date is None:
        end_date = _default_end_date()

    try:
        resp = analytics.reports().query(
            ids=f'channel=={channel_id}',
            startDate=_date_str(start_date),
            endDate=_date_str(end_date),
            metrics=CHANNEL_METRICS_FIELDS,
            dimensions='day',
            sort='day',
            maxResults=10000,
        ).execute()
    except Exception as e:
        print(f"  [analytics] Error fetching channel metrics: {e}")
        return []

    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for row in resp.get('rows', []):
        rows.append({
            'date': row[0],
            'views': row[1],
            'watch_time_minutes': row[2],
            'subscribers_gained': row[3],
            'subscribers_lost': row[4],
            'updated_at': now,
        })

    return rows


def fetch_traffic_sources(analytics, channel_id, video_ids):
    """Lifetime traffic sources per video."""
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    start = '2005-01-01'
    end = _date_str(_default_end_date())

    for i in range(0, len(video_ids), 200):
        batch = video_ids[i:i + 200]
        filters = f"video=={','.join(batch)}"

        try:
            resp = analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start,
                endDate=end,
                metrics='views,estimatedMinutesWatched',
                dimensions='insightTrafficSourceType,video',
                filters=filters,
                maxResults=10000,
            ).execute()
        except Exception as e:
            print(f"  [analytics] Error fetching traffic sources batch {i}: {e}")
            continue

        for row in resp.get('rows', []):
            rows.append({
                'source_type': row[0],
                'video_id': row[1],
                'views': row[2],
                'watch_time_minutes': row[3],
                'updated_at': now,
            })

    return rows


def fetch_demographics(analytics, channel_id, video_ids):
    """Lifetime demographics per video."""
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    start = '2005-01-01'
    end = _date_str(_default_end_date())

    for i in range(0, len(video_ids), 200):
        batch = video_ids[i:i + 200]
        filters = f"video=={','.join(batch)}"

        try:
            resp = analytics.reports().query(
                ids=f'channel=={channel_id}',
                startDate=start,
                endDate=end,
                metrics='viewerPercentage',
                dimensions='ageGroup,gender,video',
                filters=filters,
                maxResults=10000,
            ).execute()
        except Exception as e:
            print(f"  [analytics] Error fetching demographics batch {i}: {e}")
            continue

        for row in resp.get('rows', []):
            rows.append({
                'age_group': row[0],
                'gender': row[1],
                'video_id': row[2],
                'viewer_percentage': row[3],
                'updated_at': now,
            })

    return rows

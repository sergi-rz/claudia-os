"""YouTube Data API v3 — channel info and video metadata."""

import isodate
from datetime import datetime, timezone


def fetch_channel_info(service, channel_id):
    resp = service.channels().list(
        part='snippet,statistics,contentDetails',
        id=channel_id,
    ).execute()

    items = resp.get('items', [])
    if not items:
        return None

    item = items[0]
    snippet = item['snippet']
    stats = item['statistics']
    content = item['contentDetails']

    return {
        'channel_id': channel_id,
        'title': snippet.get('title', ''),
        'description': snippet.get('description', ''),
        'subscriber_count': int(stats.get('subscriberCount', 0)),
        'video_count': int(stats.get('videoCount', 0)),
        'view_count': int(stats.get('viewCount', 0)),
        'custom_url': snippet.get('customUrl', ''),
        'thumbnail_url': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
        'uploads_playlist_id': content.get('relatedPlaylists', {}).get('uploads', ''),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }


def fetch_all_video_ids(service, uploads_playlist_id):
    """Uses playlistItems.list (1 unit) instead of search.list (100 units)."""
    video_ids = []
    page_token = None

    while True:
        resp = service.playlistItems().list(
            part='contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()

        for item in resp.get('items', []):
            vid = item['contentDetails'].get('videoId')
            if vid:
                video_ids.append(vid)

        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    return video_ids


def _parse_duration(iso_duration):
    try:
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception:
        return 0


def fetch_video_details(service, video_ids):
    """Fetches metadata in batches of 50 (API max)."""
    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = service.videos().list(
            part='snippet,contentDetails,statistics',
            id=','.join(batch),
        ).execute()

        now = datetime.now(timezone.utc).isoformat()
        for item in resp.get('items', []):
            snippet = item['snippet']
            content = item['contentDetails']
            duration_s = _parse_duration(content.get('duration', 'PT0S'))

            videos.append({
                'video_id': item['id'],
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'published_at': snippet.get('publishedAt', '')[:10],
                'duration_seconds': duration_s,
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId', ''),
                'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'is_short': 1 if duration_s < 60 else 0,
                'updated_at': now,
            })

    return videos

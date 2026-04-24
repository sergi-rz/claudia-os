"""YouTube corpus source: RSS feed sync."""

import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CLAUDIA_ROOT = Path(__file__).resolve().parents[3].parent
sys.path.insert(0, str(CLAUDIA_ROOT / '.claude' / 'skills' / 'yt-transcript'))
from extract_subtitles import process_video  # noqa: E402


def fetch_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ClaudiaBot/1.0)"
    })
    with urllib.request.urlopen(req) as response:
        xml_content = response.read()

    root = ET.fromstring(xml_content)
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id = entry.find("yt:videoId", ns).text
        title = entry.find("atom:title", ns).text
        published = entry.find("atom:published", ns).text
        link = entry.find("atom:link", ns).get("href", "")
        videos.append({
            "id": video_id,
            "title": title,
            "date": published[:10],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "is_short": "/shorts/" in link,
        })
    return videos


def existing_video_ids(corpus_dir):
    existing = set()
    if not os.path.exists(corpus_dir):
        return existing
    for filename in os.listdir(corpus_dir):
        if not filename.endswith('.md'):
            continue
        with open(os.path.join(corpus_dir, filename), encoding='utf-8') as f:
            for line in f:
                match = re.search(r'youtube\.com/watch\?v=([A-Za-z0-9_-]+)', line)
                if match:
                    existing.add(match.group(1))
                    break
    return existing


def sync(config, workspace_root, do_sync):
    channel_id = config["channel_id"]
    corpus_dir = os.path.join(workspace_root, config["corpus_dir"])
    cookies_file = config.get("cookies_file")
    if cookies_file:
        cookies_file = os.path.join(workspace_root, cookies_file)
        if not os.path.exists(cookies_file):
            cookies_file = None
    ignore_shorts = config.get("ignore_shorts", True)
    lang = config.get("lang", "es")

    print(f"[youtube] Canal: {channel_id}")
    videos = fetch_feed(channel_id)
    full = [v for v in videos if not (ignore_shorts and v["is_short"])]
    ignored_count = len(videos) - len(full)
    print(f"[youtube] Feed: {len(full)} vídeos" + (f" (+ {ignored_count} shorts ignorados)" if ignored_count else ""))

    existing = existing_video_ids(corpus_dir)
    print(f"[youtube] En corpus: {len(existing)}")

    missing = [v for v in full if v["id"] not in existing]
    if not missing:
        print("[youtube] Al día.")
        return {"processed": 0, "errors": 0}

    print(f"[youtube] Nuevos: {len(missing)}")
    for v in missing:
        print(f"  - {v['title']} ({v['date']})")

    if not do_sync:
        return {"processed": 0, "errors": 0, "missing": len(missing)}

    os.makedirs(corpus_dir, exist_ok=True)
    browser = None if cookies_file else "chrome"
    processed = errors = 0
    for v in missing:
        result = process_video(v["url"], corpus_dir, lang=lang,
                               cookies_file=cookies_file, cookies_from_browser=browser)
        if result:
            processed += 1
        else:
            errors += 1
    return {"processed": processed, "errors": errors}

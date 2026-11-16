"""YouTube Reporting API — daily bulk reports (reach and user activity).

Unlike the Analytics API, reports are only generated for report types that
have a job, and each report covers one day. YouTube may regenerate a day
later with corrected data: the newest report for a day replaces the older one.
"""

import csv
import io
import time

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# The API allows 60 requests per minute per Cloud project
MIN_INTERVAL_SECONDS = 1.1
_last_request = 0.0

# report_type_id -> job name used when the job has to be created
REPORT_TYPES = {
    'channel_reach_basic_a1': 'Reach basic',
    'channel_basic_a3': 'User activity',
}


def _call(fn):
    """Spaces requests to stay under the per-minute quota, retrying 429s."""
    global _last_request
    for attempt in range(5):
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            return fn()
        except HttpError as e:
            if e.status_code != 429 or attempt == 4:
                raise
            print("  [reporting] Rate limited, waiting 60s...")
            time.sleep(60)


def ensure_jobs(reporting):
    """Returns {report_type_id: job_id}, creating the missing jobs."""
    jobs = {}
    token = None
    while True:
        resp = _call(lambda: reporting.jobs().list(pageToken=token).execute())
        for job in resp.get('jobs', []):
            jobs[job['reportTypeId']] = job['id']
        token = resp.get('nextPageToken')
        if not token:
            break

    for report_type, name in REPORT_TYPES.items():
        if report_type not in jobs:
            job = _call(lambda: reporting.jobs().create(body={'reportTypeId': report_type, 'name': name}).execute())
            jobs[report_type] = job['id']
            print(f"  [reporting] Created job for {report_type}: {job['id']}")

    return {rt: jobs[rt] for rt in REPORT_TYPES}


def list_latest_reports(reporting, job_id):
    """Newest report per day for a job, sorted by day."""
    latest = {}
    token = None
    while True:
        resp = _call(lambda: reporting.jobs().reports().list(jobId=job_id, pageToken=token).execute())
        for rep in resp.get('reports', []):
            day = rep['startTime']
            if day not in latest or rep['createTime'] > latest[day]['createTime']:
                latest[day] = rep
        token = resp.get('nextPageToken')
        if not token:
            break

    return [latest[day] for day in sorted(latest)]


def download_report(reporting, download_url):
    """Downloads a report and returns its rows as dicts (CSV header as keys)."""
    def fetch():
        request = reporting.media().download_media(resourceName='')
        request.uri = download_url
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf

    buf = _call(fetch)
    return list(csv.DictReader(io.StringIO(buf.getvalue().decode('utf-8'))))

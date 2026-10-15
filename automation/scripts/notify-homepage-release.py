#!/usr/bin/env python3
"""Send only a validated Homepage receipt summary to the Mezon release webhook."""
import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from urllib.parse import urlsplit
import urllib.request

REPOSITORY = 'registry-gitlab.dungxbuif.com/dungxbuif/homepage'
STATUSES = frozenset(('success', 'unchanged', 'failed', 'update_rejected',
                      'recovery_required', 'rollback_conflict', 'failed_no_change',
                      'rolled_back', 'rollback_unhealthy'))
FIELDS = frozenset(('status', 'image', 'receipt', 'ci_job', 'commit', 'observed_at'))


def payload(report, task_id, now=None):
    if not isinstance(report, dict) or set(report) != FIELDS or type(task_id) is not int or task_id <= 0:
        raise ValueError('invalid receipt')
    if any(not isinstance(report[key], str) for key in FIELDS - {'ci_job'}):
        raise ValueError('invalid receipt fields')
    if report['status'] not in STATUSES or type(report['ci_job']) is not int or report['ci_job'] <= 0:
        raise ValueError('invalid release status or job')
    for key, pattern in (
        ('image', re.escape(REPOSITORY) + r'@sha256:[a-f0-9]{64}'),
        ('commit', r'[a-f0-9]{40}'), ('receipt', r'homepage-release-[A-Za-z0-9_-]{1,100}'),
    ):
        if not re.fullmatch(pattern, report[key]):
            raise ValueError('invalid release identifier')
    observed = datetime.fromisoformat(report['observed_at'])
    current = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    if observed.tzinfo is None or not 0 <= (current - observed).total_seconds() <= 900:
        raise ValueError('stale or invalid observation')
    status = report['status']
    classification = 'OK' if status == 'success' else 'UNCHANGED' if status == 'unchanged' else 'FAIL'
    text = '\n'.join([
        f'[HOMELAB DEPLOY] [{classification}] homepage: {status}',
        f'Task: {task_id}', f'Receipt: {report["receipt"]}',
        f'CI job: {report["ci_job"]}', f'Commit: {report["commit"]}',
        f'Image: {report["image"]}', f'Observed: {observed.isoformat()}',
    ])
    return {'type': 'hook', 'message': {'t': text,
            'mk': [{'type': 'pre', 's': 0, 'e': len(text)}],
            'mentions': [], 'images': [], 'hg': []}}


def validate_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc != 'webhook.mezon.ai'
            or parts.query or parts.fragment or any(c.isspace() for c in url)
            or not re.fullmatch(r'/webhooks/[0-9]+/[A-Za-z0-9_.-]+', parts.path)):
        raise ValueError('invalid webhook destination')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send(url, message, opener=None):
    validate_url(url)
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, data=json.dumps(message).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=15) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError('notification was not accepted')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-id', type=int, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read(32769)
        if len(raw.encode()) > 32768:
            raise ValueError('receipt exceeds limit')
        message = payload(json.loads(raw), args.task_id)
        if args.dry_run:
            print(json.dumps(message))
        else:
            url = os.environ.get('HOMELAB_MEZON_WEBHOOK_URL', '')
            validate_url(url)
            send(url, message)
            print(json.dumps({'notification': 'accepted', 'task_id': args.task_id}))
        return 0
    except Exception:
        # URL and exception text can contain the webhook credential.
        print('Release notification failed; inspect receipt and secret configuration', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

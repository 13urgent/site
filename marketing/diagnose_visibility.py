#!/usr/bin/env python3
"""Read-only checks of approved Buffer destinations and known publication URLs."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, urlunsplit

import pipeline

publisher = pipeline.load_module('visibility_buffer', pipeline.ROOT / 'publisher/buffer_publish.py')
LABELS = {('linkedin', 'haeckel hamri'): 'linkedin_founder',
          ('linkedin', 'chronos'): 'linkedin_company', ('tiktok', '13urgentsite'): 'tiktok'}
STATUSES = {'draft', 'error', 'needs_approval', 'scheduled', 'sending', 'sent'}


def public_url(value, kind):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    if value.startswith(('www.linkedin.com/', 'fr.linkedin.com/', 'linkedin.com/', 'www.tiktok.com/', 'tiktok.com/')):
        value = 'https://' + value
    try:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
            return None
    except ValueError:
        return None
    host = (parsed.hostname or '').lower()
    path = parsed.path
    if host in ('www.linkedin.com', 'fr.linkedin.com', 'linkedin.com'):
        valid = (path.startswith(('/in/', '/company/')) if kind == 'profile'
                 else path.startswith(('/feed/update/', '/posts/')))
    elif host in ('www.tiktok.com', 'tiktok.com'):
        pattern = r'/@[A-Za-z0-9._]+/?' if kind == 'profile' else r'/@[A-Za-z0-9._]+/(?:video|photo)/[0-9]+/?'
        valid = bool(re.fullmatch(pattern, path))
    else:
        valid = False
    if not valid or any(c in path for c in ('\\', '<', '>')):
        return None
    return urlunsplit(('https', host, path, '', ''))


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.isoformat() if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def error_bucket(error):
    if not error:
        return None
    message = str(error.get('message', '')).casefold() if isinstance(error, dict) else ''
    if any(word in message for word in ('token', 'reconnect', 'expired', 'authorization', 'permission')):
        return 'account_authorization'
    if any(word in message for word in ('video', 'processing', 'media')):
        return 'media_or_processing'
    if any(word in message for word in ('limit', 'quota', 'rate')):
        return 'network_limit'
    return 'provider_error'


class VisibilityClient(publisher.BufferClient):
    def channels(self):
        organizations = self.query('query { account { organizations { id } } }')['account']['organizations']
        approved = []
        for organization in organizations:
            oid = organization['id']
            query = ('query { channels(input: { organizationId: ' + json.dumps(oid)
                     + ' }) { id name displayName service externalLink isDisconnected isLocked isQueuePaused } }')
            for row in self.query(query)['channels']:
                labels = set()
                for name in (row.get('name'), row.get('displayName')):
                    if not isinstance(name, str):
                        continue
                    name = publisher.normal(name)
                    if name == 'chronoss':
                        name = 'chronos'
                    label = LABELS.get((publisher.normal(row['service']), name))
                    if label:
                        labels.add(label)
                if len(labels) > 1:
                    raise publisher.SafeFailure('channel_identity_ambiguous')
                if not labels:
                    continue
                self._organization_by_channel[row['id']] = oid
                approved.append({'id': row['id'], 'label': next(iter(labels)),
                                 'profile_url': public_url(row.get('externalLink'), 'profile'),
                                 'disconnected': row.get('isDisconnected') is True,
                                 'locked': row.get('isLocked') is True,
                                 'queue_paused': row.get('isQueuePaused') is True})
        return approved


def diagnose(client, state):
    if state.get('schema_version') != 1 or not isinstance(state.get('posts'), dict):
        raise publisher.SafeFailure('state_schema')
    channels = client.channels()
    by_channel = {c['id']: c for c in channels}
    observed, complete = client.verification_posts(channels)
    by_hash = {hashlib.sha256(p['id'].encode()).hexdigest(): p for p in observed}
    records = []
    for key, recorded in state['posts'].items():
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', key):
            raise publisher.SafeFailure('ledger_key_invalid')
        post = by_hash.get(recorded.get('buffer_post_fingerprint'))
        if post is None:
            records.append({'ledger_key': key, 'matched': False})
            continue
        query = ('query { post(input: { id: ' + json.dumps(post['id'])
                 + ' }) { status schedulingType dueAt sentAt externalLink channelId error { message } } }')
        detail = client.query(query).get('post')
        if not isinstance(detail, dict) or detail.get('status') not in STATUSES:
            raise publisher.SafeFailure('post_detail_schema')
        channel = by_channel.get(detail.get('channelId'))
        if channel is None:
            raise publisher.SafeFailure('post_channel_outside_approved_scope')
        mode = detail.get('schedulingType')
        if mode not in ('automatic', 'notification'):
            mode = 'unknown'
        records.append({'ledger_key': key, 'matched': True, 'target': channel['label'],
                        'profile_url': channel['profile_url'], 'provider_status': detail['status'],
                        'scheduling_type': mode, 'due_at': timestamp(detail.get('dueAt')),
                        'sent_at': timestamp(detail.get('sentAt')),
                        'public_post_url': public_url(detail.get('externalLink'), 'post'),
                        'provider_error_present': bool(detail.get('error')),
                        'error_category': error_bucket(detail.get('error')),
                        'public_visibility_confirmed': False})
    return {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'mode': 'read_only', 'new_posts_created': 0, 'scan_complete': complete,
            'destinations': [{k: v for k, v in channel.items() if k != 'id'} for channel in channels],
            'public_visibility_confirmed': False, 'posts': records}


def read_ledger():
    result = subprocess.run(['git', 'fetch', '--depth=1', 'origin', 'refs/heads/marketing-state'],
                            capture_output=True, timeout=60)
    if result.returncode:
        raise publisher.SafeFailure('ledger_fetch_failed')
    result = subprocess.run(['git', 'show', 'FETCH_HEAD:state.json'], capture_output=True, timeout=30)
    if result.returncode:
        raise publisher.SafeFailure('ledger_read_failed')
    return json.loads(result.stdout)


def main():
    report = diagnose(VisibilityClient(os.environ.get('BUFFER_API_KEY')), read_ledger())
    output = Path('.runtime/visibility-report.json')
    publisher.atomic_json(output, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, publisher.SafeFailure) else 'visibility_check_failed'
        if not re.fullmatch(r'[a-z0-9_]+', code):
            code = 'visibility_check_failed'
        print(json.dumps({'status': 'blocked', 'error': code, 'new_posts_created': 0}))
        raise SystemExit(2)

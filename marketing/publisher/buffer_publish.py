#!/usr/bin/env python3
"""Buffer publication adapter. Only explicitly named CHRONOSS channels are used.

No retries after an uncertain mutation: reconcile the saved intent in Buffer
before permitting another attempt. Persist the state file between executions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API = 'https://api.buffer.com'
ALLOWED = {('linkedin', 'haeckel hamri'), ('linkedin', 'chronos'), ('tiktok', '13urgentsite')}


class SafeFailure(Exception):
    """Only static, nonsensitive codes are carried in this exception."""


def normal(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c)).casefold().split())


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def stamp():
    return datetime.now(timezone.utc).isoformat()


class BufferClient:
    def __init__(self, key, opener=urlopen):
        if not key or not key.strip():
            raise SafeFailure('buffer_key_missing')
        self.key = key.strip()
        self.opener = opener
        self._organization_by_channel = {}

    def query(self, query):
        request = Request(API, data=json.dumps({'query': query}).encode(), method='POST', headers={
            'Authorization': 'Bearer ' + self.key,
            'Content-Type': 'application/json', 'User-Agent': '13URGENT-Publisher/1.0',
        })
        try:
            with self.opener(request, timeout=35) as response:
                if response.status != 200:
                    raise SafeFailure('buffer_http_error')
                payload = json.load(response)
        except HTTPError as error:
            raise SafeFailure('buffer_http_' + str(error.code)) from None
        except (URLError, TimeoutError, OSError):
            raise SafeFailure('buffer_network_error') from None
        except (ValueError, UnicodeError):
            raise SafeFailure('buffer_invalid_json') from None
        if not isinstance(payload, dict) or payload.get('errors') or not isinstance(payload.get('data'), dict):
            raise SafeFailure('buffer_graphql_error')
        return payload['data']

    def channels(self):
        data = self.query('query { account { organizations { id } } }')
        try:
            organizations = data['account']['organizations']
        except (KeyError, TypeError):
            raise SafeFailure('buffer_account_schema') from None
        if not isinstance(organizations, list):
            raise SafeFailure('buffer_account_schema')
        channels = []
        for organization in organizations:
            oid = organization.get('id') if isinstance(organization, dict) else None
            if not isinstance(oid, str) or not oid:
                raise SafeFailure('buffer_organization_schema')
            data = self.query('query { channels(input: { organizationId: ' + json.dumps(oid) + ' }) { id name service } }')
            rows = data.get('channels')
            if not isinstance(rows, list):
                raise SafeFailure('buffer_channels_schema')
            for row in rows:
                if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k] for k in ('id', 'name', 'service')):
                    raise SafeFailure('buffer_channels_schema')
                if (normal(row['service']), normal(row['name'])) in ALLOWED:
                    channels.append({k: row[k] for k in ('id', 'name', 'service')})
                    self._organization_by_channel[row['id']] = oid
        return channels

    def create(self, post, channel):
        values = [
            'channelId: ' + json.dumps(channel['id']),
            'text: ' + json.dumps(post['text']),
            'schedulingType: automatic', 'mode: customScheduled',
            'dueAt: ' + json.dumps(post['due_at']),
        ]
        if post.get('video_url'):
            values.append('assets: [{ video: { url: ' + json.dumps(post['video_url']) + ' } }]')
        query = 'mutation { createPost(input: { ' + ', '.join(values) + ' }) { __typename ... on PostActionSuccess { post { id dueAt status schedulingType sentAt } } ... on MutationError { message } } }'
        data = self.query(query)
        result = data.get('createPost')
        if not isinstance(result, dict):
            raise SafeFailure('buffer_mutation_schema')
        if result.get('__typename') == 'MutationError':
            # Do not log provider messages: they can echo user input.
            return {'status': 'rejected', 'error': 'buffer_mutation_rejected'}
        saved = result.get('post')
        if result.get('__typename') != 'PostActionSuccess' or not isinstance(saved, dict) or not isinstance(saved.get('id'), str) or not saved['id']:
            raise SafeFailure('buffer_mutation_uncertain')
        status = saved.get('status')
        scheduling_type = saved.get('schedulingType')
        if status not in ('draft', 'error', 'needs_approval', 'scheduled', 'sending', 'sent') or scheduling_type not in ('automatic', 'notification'):
            raise SafeFailure('buffer_scheduling_unverified')
        accepted = scheduling_type == 'automatic' and status == 'scheduled'
        try:
            requested_due = datetime.fromisoformat(post['due_at'].replace('Z', '+00:00'))
            stored_due = datetime.fromisoformat(saved['dueAt'].replace('Z', '+00:00'))
            matching_due = requested_due.utcoffset() is not None and stored_due.utcoffset() is not None and abs((requested_due-stored_due).total_seconds()) <= 1
        except (ValueError, TypeError, KeyError):
            matching_due = False
        accepted = accepted and matching_due
        result = {'status': 'scheduled' if accepted else 'provider_not_scheduled',
                  'buffer_post_id': saved['id'], 'due_at': saved.get('dueAt'),
                  'provider_status': status, 'scheduling_type': scheduling_type}
        if not accepted:
            result['error'] = 'buffer_due_at_mismatch' if not matching_due else 'buffer_automatic_schedule_not_confirmed'
        return result

    def post_status(self, post_id):
        """Read one post without writing or logging its raw Buffer identifier."""
        if not isinstance(post_id, str) or not post_id:
            raise SafeFailure('post_id_missing')
        data = self.query('query { post(input: { id: ' + json.dumps(post_id) + ' }) { status schedulingType dueAt sentAt } }')
        post = data.get('post')
        if not isinstance(post, dict) or post.get('status') not in ('draft', 'error', 'needs_approval', 'scheduled', 'sending', 'sent'):
            raise SafeFailure('buffer_post_status_schema')
        return {'provider_status': post['status'], 'scheduling_type': post.get('schedulingType'),
                'due_at': post.get('dueAt'), 'sent_at': post.get('sentAt')}

    def verification_posts(self, channels):
        """Read at most 100 posts, only for the three allowlisted channels.

        Returns records only in memory. Organization/channel/post IDs must never
        be written to an artifact or a public workflow log.
        """
        groups = {}
        for channel in channels:
            organization = self._organization_by_channel.get(channel['id'])
            if not organization:
                raise SafeFailure('buffer_channel_context_missing')
            groups.setdefault(organization, []).append(channel['id'])
        collected, pages, complete = [], 0, True
        for oid, channel_ids in groups.items():
            after = None
            while True:
                if pages >= 5:
                    complete = False
                    break
                query = ('query { posts(first: 20, '
                         + ('after: ' + json.dumps(after) + ', ' if after else '')
                         + 'input: { organizationId: ' + json.dumps(oid)
                         + ', filter: { channelIds: ' + json.dumps(channel_ids)
                         + ' }, sort: [{field: createdAt, direction: desc}] }) '
                         + '{ edges { node { id status schedulingType dueAt sentAt } } '
                         + 'pageInfo { hasNextPage endCursor } } }')
                data = self.query(query)
                result = data.get('posts')
                if not isinstance(result, dict) or not isinstance(result.get('edges'), list) or not isinstance(result.get('pageInfo'), dict):
                    raise SafeFailure('buffer_posts_status_schema')
                for edge in result['edges']:
                    post = edge.get('node') if isinstance(edge, dict) else None
                    if not isinstance(post, dict) or not isinstance(post.get('id'), str) or post.get('status') not in ('draft', 'error', 'needs_approval', 'scheduled', 'sending', 'sent'):
                        raise SafeFailure('buffer_posts_status_schema')
                    collected.append(post)
                pages += 1
                if not result['pageInfo'].get('hasNextPage'):
                    break
                next_cursor = result['pageInfo'].get('endCursor')
                if not isinstance(next_cursor, str) or not next_cursor or next_cursor == after:
                    raise SafeFailure('buffer_pagination_cursor_invalid')
                after = next_cursor
        return collected, complete


def verify_delivery(client, state_path, report_path, checkpoint=None):
    """Reconcile only known hashed IDs, without scheduling any publication."""
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    channels = client.channels()
    observations, complete = client.verification_posts(channels)
    with open(str(state_path) + '.lock', 'a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = json.loads(state_path.read_text()) if state_path.exists() else {'schema_version': 1, 'posts': {}}
        if state.get('schema_version') != 1 or not isinstance(state.get('posts'), dict):
            raise SafeFailure('state_schema')
        records = list(state['posts'].values())
        if any(not isinstance(record, dict) for record in records):
            raise SafeFailure('state_schema')
        by_hash = {record.get('buffer_post_fingerprint'): record for record in records if record.get('buffer_post_fingerprint')}
        matched = 0
        for post in observations:
            hashed_id = hashlib.sha256(post['id'].encode()).hexdigest()
            record = by_hash.get(hashed_id)
            if not record:
                continue
            status = post['status']
            matched += 1
            record.update(provider_status=status, scheduling_type=post.get('schedulingType'), last_verified_at=stamp())
            if status == 'sent':
                record.update(status='sent', sent_at=post.get('sentAt'))
                record.pop('error', None)
            elif status == 'error':
                record.update(status='delivery_error', error='buffer_delivery_failed')
            elif status in ('draft', 'needs_approval') or post.get('schedulingType') != 'automatic':
                record.update(status='provider_not_scheduled', error='buffer_automatic_schedule_not_confirmed')
            elif status in ('scheduled', 'sending'):
                record.update(status='scheduled')
                record.pop('error', None)
        if matched:
            atomic_json(state_path, state)
            if checkpoint:
                try:
                    checkpoint()
                except Exception:
                    raise SafeFailure('state_checkpoint_failed') from None
        counts = {'scheduled': 0, 'sent': 0, 'errors': 0, 'uncertain': 0}
        for record in records:
            status = record.get('status')
            if status in ('scheduled', 'sent'):
                counts[status] += 1
            elif status == 'delivery_error':
                counts['errors'] += 1
            elif status in ('intent', 'uncertain', 'rejected', 'provider_not_scheduled'):
                counts['uncertain'] += 1
        report = {'schema_version': 1, 'mode': 'verify', 'checked_at': stamp(),
                  'ok': not counts['errors'] and not counts['uncertain'],
                  'counts': counts, 'records_matched': matched,
                  'posts_inspected': len(observations), 'scan_complete': complete}
        atomic_json(report_path, report)
        return report


def validate_plan(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get('posts'), list):
        raise SafeFailure('plan_schema')
    ids = set()
    for post in plan['posts']:
        if not isinstance(post, dict):
            raise SafeFailure('plan_post_schema')
        for key in ('id', 'channel_name', 'service', 'text', 'due_at'):
            if not isinstance(post.get(key), str) or not post[key].strip():
                raise SafeFailure('plan_field_missing')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,180}', post['id']) or post['id'] in ids:
            raise SafeFailure('plan_id_invalid_or_duplicate')
        ids.add(post['id'])
        service = normal(post['service'])
        if (service, normal(post['channel_name'])) not in ALLOWED:
            raise SafeFailure('channel_not_authorized')
        if len(post['text']) > (2200 if service == 'tiktok' else 3000):
            raise SafeFailure('caption_too_long')
        try:
            due = datetime.fromisoformat(post['due_at'].replace('Z', '+00:00'))
            if due.utcoffset() is None:
                raise ValueError()
        except (ValueError, TypeError):
            raise SafeFailure('due_at_requires_timezone') from None
        video = post.get('video_url')
        if service == 'tiktok' and not video:
            raise SafeFailure('tiktok_requires_video')
        if video:
            if not isinstance(video, str):
                raise SafeFailure('video_url_invalid')
            parsed = urlparse(video)
            own = parsed.netloc == '13urgent.fr' and parsed.path.startswith('/videos/')
            raw = parsed.netloc == 'raw.githubusercontent.com' and parsed.path.startswith('/13urgent/site/gh-pages/videos/')
            if parsed.scheme != 'https' or not (own or raw) or parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path.endswith('.mp4'):
                raise SafeFailure('video_url_not_authorized')


def run(client, mode, plan, state_path, report_path, now=None, checkpoint=None):
    if mode not in ('probe', 'publish'):
        raise SafeFailure('mode_invalid')
    validate_plan(plan)
    channels = client.channels()
    # Reports/state can be persisted in a public repository: queried account
    # names, organization/channel IDs and Buffer post IDs stay only in memory.
    report = {'schema_version': 1, 'mode': mode, 'checked_at': stamp(),
              'channels': [{'service': c['service']} for c in channels], 'posts': [], 'ok': True}
    resolved = {}
    for post in plan['posts']:
        matches = [c for c in channels if (normal(c['service']), normal(c['name'])) == (normal(post['service']), normal(post['channel_name']))]
        if len(matches) != 1:
            raise SafeFailure('channel_missing_or_ambiguous')
        resolved[post['id']] = matches[0]
    if mode == 'probe':
        atomic_json(report_path, report)
        return report
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    def persist(value):
        atomic_json(state_path, value)
        if checkpoint:
            # Remote persistence failure stops the run; a saved intent blocks
            # replay after a runner crash or uncertain successful mutation.
            try:
                checkpoint()
            except Exception:
                raise SafeFailure('state_checkpoint_failed') from None
    # Serializes same-host callers. The scheduler must also provide concurrency
    # control and durably persist state before another execution is started.
    with open(str(state_path) + '.lock', 'a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = json.loads(state_path.read_text()) if state_path.exists() else {'schema_version': 1, 'posts': {}}
        if state.get('schema_version') != 1 or not isinstance(state.get('posts'), dict):
            raise SafeFailure('state_schema')
        scrubbed = False
        for record in state['posts'].values():
            if not isinstance(record, dict):
                raise SafeFailure('state_schema')
            if 'channel_id' in record:
                record.pop('channel_id')
                scrubbed = True
            if 'buffer_post_id' in record:
                raw = record.pop('buffer_post_id')
                if isinstance(raw, str) and raw:
                    record['buffer_post_fingerprint'] = hashlib.sha256(raw.encode()).hexdigest()
                scrubbed = True
        if scrubbed:
            persist(state)
        for post in plan['posts']:
            pid = post['id']
            fingerprint = hashlib.sha256(json.dumps(post, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            previous = state['posts'].get(pid)
            if previous:
                status = 'already_recorded' if previous.get('fingerprint') == fingerprint else 'id_conflict'
                report['posts'].append({'id': pid, 'status': status, 'recorded_status': previous.get('status')})
                if status == 'id_conflict' or previous.get('status') in ('intent', 'uncertain', 'rejected', 'provider_not_scheduled', 'delivery_error'):
                    report['ok'] = False
                continue
            due = datetime.fromisoformat(post['due_at'].replace('Z', '+00:00'))
            if due <= (now or datetime.now(timezone.utc)):
                report['posts'].append({'id': pid, 'status': 'skipped_past_due'})
                report['ok'] = False
                continue
            record = {'fingerprint': fingerprint, 'status': 'intent', 'created_at': stamp(), 'due_at': post['due_at']}
            state['posts'][pid] = record
            persist(state)  # Must succeed locally AND remotely BEFORE mutation.
            try:
                outcome = client.create(post, resolved[pid])
                raw_post_id = outcome.pop('buffer_post_id', None)
                if raw_post_id:
                    outcome['buffer_post_fingerprint'] = hashlib.sha256(raw_post_id.encode()).hexdigest()
                record.update(outcome)
            except SafeFailure as error:
                record.update(status='uncertain', error=str(error))
            except Exception:
                # Do not print raw exception text or retry a possible side effect.
                record.update(status='uncertain', error='unexpected_mutation_error')
            record['updated_at'] = stamp()
            persist(state)
            report['posts'].append({'id': pid, **{k: record[k] for k in ('status', 'provider_status', 'scheduling_type', 'buffer_post_fingerprint', 'due_at', 'error') if k in record}})
            if record['status'] != 'scheduled':
                report['ok'] = False
        atomic_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--mode', choices=('probe', 'publish', 'verify'), default='probe')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint-command', help='Trusted fixed argv command, without shell interpolation; called after every durable state write')
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text()) if args.plan else {'posts': []}
        checkpoint = None
        if args.checkpoint_command:
            command = shlex.split(args.checkpoint_command)
            if not command:
                raise SafeFailure('checkpoint_command_empty')
            def checkpoint():
                subprocess.run(command, check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = BufferClient(os.environ.get('BUFFER_API_KEY'))
        if args.mode == 'verify':
            result = verify_delivery(client, args.state, args.output, checkpoint=checkpoint)
            print(json.dumps({'ok': result['ok'], 'mode': args.mode, 'counts': result['counts'], 'scan_complete': result['scan_complete']}))
        else:
            result = run(client, args.mode, plan, args.state, args.output, checkpoint=checkpoint)
            print(json.dumps({'ok': result['ok'], 'mode': args.mode, 'channels_found': len(result['channels']), 'post_results': [{'id': p['id'], 'status': p['status']} for p in result['posts']]}))
        return 0 if result['ok'] else 2
    except SafeFailure as error:
        atomic_json(args.output, {'ok': False, 'mode': args.mode, 'error': str(error)})
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 2
    except Exception:
        # A plan/state filesystem or format failure must never expose the key.
        atomic_json(args.output, {'ok': False, 'mode': args.mode, 'error': 'local_input_or_state_error'})
        print('{"ok":false,"error":"local_input_or_state_error"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

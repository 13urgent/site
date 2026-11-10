#!/usr/bin/env python3
"""Read-only monitoring of delivery reports and replies linked to sent campaigns."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
import hashlib
import imaplib
import json
from pathlib import Path
import re
import ssl

import commercial_agent as agent
import delivery_status
import run_campaign

OWN_ID = re.compile(r'<([0-9a-f]{64})@13urgent\.fr>', re.I)


def record_index(state):
    index = {}
    for records in state.get('campaigns', {}).values():
        for record in records.values():
            fingerprint = record.get('fingerprint', '')
            if re.fullmatch('[0-9a-f]{64}', fingerprint):
                index.setdefault(fingerprint, []).append(record)
    return index


def recipient_matches(record, address):
    # Every existing sender has one external addressee and the fixed owner CC.
    if not address or address.lower() in (agent.SENDER, agent.COPY):
        return False
    expected = record.get('recipient_fingerprint')
    return expected is None or expected == hashlib.sha256(address.lower().encode()).hexdigest()


def explicit_stop(message):
    for part in message.walk():
        if part.get_content_type() != 'text/plain' or part.get_content_disposition() == 'attachment':
            continue
        try:
            text = part.get_content()
        except (LookupError, UnicodeError):
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # An exact first line avoids attributing the quoted campaign footer.
            return bool(re.fullmatch(r'STOP[.!]?', line, re.I))
    return False


def process_message(raw, index, checked_at):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    sender = parseaddr(str(message.get('From', '')))[1].lower()
    failures_matched = replies_matched = oppositions_matched = 0
    fingerprints, failures = delivery_status.report_failures(raw)
    for fingerprint in fingerprints:
        for record in index.get(fingerprint, []):
            for address, code in failures:
                if not recipient_matches(record, address):
                    continue
                if record.get('delivery_status') != 'hard_bounced' or record.get('delivery_code') != code:
                    record.update(delivery_status='hard_bounced', delivery_code=code,
                                  blocked_for_resend=True, bounce_source='matched_delivery_report',
                                  bounce_checked_at=checked_at)
                    failures_matched += 1
    sender_local = sender.split('@', 1)[0]
    if (not sender or sender in (agent.SENDER, agent.COPY)
            or sender_local in ('mailer-daemon', 'postmaster')
            or message.get_content_type() == 'multipart/report'
            or str(message.get('Auto-Submitted', 'no')).strip().lower() != 'no'
            or str(message.get('Precedence', '')).strip().lower() in ('bulk', 'list', 'junk')
            or message.get('X-Autoreply') or message.get('X-Autorespond')):
        return failures_matched, 0, 0
    referenced = set(OWN_ID.findall(str(message.get('In-Reply-To', '')) + ' ' + str(message.get('References', ''))))
    for fingerprint in referenced:
        for record in index.get(fingerprint.lower(), []):
            if not recipient_matches(record, sender):
                continue
            if not record.get('response_received_to_qualify'):
                record.update(response_received_to_qualify=True, response_checked_at=checked_at)
                replies_matched += 1
            if explicit_stop(message) and not record.get('opted_out'):
                record.update(opted_out=True, blocked_for_resend=True, opposition_checked_at=checked_at)
                oppositions_matched += 1
    return failures_matched, replies_matched, oppositions_matched


def scan_since(state, now):
    earliest = now
    for records in state.get('campaigns', {}).values():
        for record in records.values():
            try:
                created = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00'))
                if created.utcoffset() is not None:
                    earliest = min(earliest, created)
            except (KeyError, ValueError, TypeError):
                pass
    return max(earliest, now - timedelta(days=14)).strftime('%d-%b-%Y')


def monitor(state_path, password, checkpoint, imap_factory=None, now=None):
    if not password:
        raise agent.CampaignError('mail_access_not_connected')
    state_path = Path(state_path)
    state = json.loads(state_path.read_text())
    if state.get('schema_version') != 1:
        raise agent.CampaignError('state_schema')
    index = record_index(state)
    now = now or datetime.now(timezone.utc)
    checked_at = now.isoformat()
    totals = [0, 0, 0]
    client = imap_factory() if imap_factory else imaplib.IMAP4_SSL(
        'ssl0.ovh.net', 993, ssl_context=ssl.create_default_context(), timeout=25)
    ids = []
    candidates = []
    examined = 0
    try:
        client.login(agent.SENDER, password)
        status, _ = client.select('INBOX', readonly=True)
        if status != 'OK':
            raise agent.CampaignError('monitor_folder_not_accessible')
        status, data = client.uid('SEARCH', None, 'SINCE', scan_since(state, now))
        if status != 'OK':
            raise agent.CampaignError('monitor_search_failed')
        ids = b' '.join(x for x in data or [] if isinstance(x, bytes)).split()
        selected = ids[-500:]
        if selected:
            query = '(UID BODY.PEEK[HEADER.FIELDS (FROM IN-REPLY-TO REFERENCES AUTO-SUBMITTED PRECEDENCE CONTENT-TYPE)])'
            status, headers = client.uid('FETCH', b','.join(selected), query)
            if status != 'OK':
                raise agent.CampaignError('monitor_headers_failed')
            for part in headers or []:
                if not isinstance(part, tuple) or len(part) != 2 or not isinstance(part[1], bytes):
                    continue
                match = re.search(rb'\bUID (\d+)\b', part[0])
                if not match:
                    continue
                examined += 1
                message = BytesParser(policy=policy.default).parsebytes(part[1])
                sender = parseaddr(str(message.get('From', '')))[1].lower()
                references = set(OWN_ID.findall(str(message.get('In-Reply-To', '')) + ' ' + str(message.get('References', ''))))
                report = message.get_content_type() == 'multipart/report' or sender.split('@', 1)[0] in ('mailer-daemon', 'postmaster')
                if report or any(fp.lower() in index for fp in references):
                    candidates.append(match.group(1))
            for uid in candidates[-100:]:
                status, data = client.uid('FETCH', uid, '(BODY.PEEK[]<0.262144>)')
                if status != 'OK':
                    continue
                raw = b''.join(x[1] for x in data or [] if isinstance(x, tuple) and len(x) == 2 and isinstance(x[1], bytes))
                changes = process_message(raw, index, checked_at)
                totals = [a + b for a, b in zip(totals, changes)]
    finally:
        try:
            client.logout()
        except Exception:
            pass
        if any(totals):
            agent.save(state_path, state)
            checkpoint()
    records = [r for group in state['campaigns'].values() for r in group.values()]
    return {'status': 'commercial_results_checked', 'headers_examined': examined,
            'matching_failures_new': totals[0], 'responses_to_qualify_new': totals[1],
            'oppositions_new': totals[2], 'hard_bounced_total': sum(r.get('delivery_status') == 'hard_bounced' for r in records),
            'responses_to_qualify_total': sum(r.get('response_received_to_qualify') is True for r in records),
            'opted_out_total': sum(r.get('opted_out') is True for r in records),
            'scan_limited': len(ids) > 500 or len(candidates) > 100,
            'emails_sent': 0, 'customer_or_revenue_confirmation': False}


def main():
    _, state_dir = run_campaign.pipeline.setup_runtime()
    print(json.dumps(monitor(state_dir / 'mail-state.json', __import__('os').environ.get('CONTACT_MAIL_PASSWORD'),
                             lambda: run_campaign.checkpoint(state_dir))))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        candidate = str(error)
        code = candidate if isinstance(error, agent.CampaignError) and re.fullmatch('[a-z0-9_]+', candidate) else 'commercial_monitor_failed'
        print(json.dumps({'status': 'blocked', 'error': code, 'emails_sent': 0}))
        raise SystemExit(2)

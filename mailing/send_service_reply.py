#!/usr/bin/env python3
"""Deliver an explicitly requested service reply from a sealed, transient request."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime, parseaddr
import hashlib
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
import subprocess
import time

import commercial_agent as agent
import run_campaign

REQUEST_ID = re.compile(r'[a-z0-9-]{1,80}')
DIGEST = re.compile(r'[0-9a-f]{64}')


def settings():
    request_id = os.environ.get('REQUEST_ID', '')
    digest = os.environ.get('PAYLOAD_SHA256', '')
    if not REQUEST_ID.fullmatch(request_id) or not DIGEST.fullmatch(digest):
        raise agent.CampaignError('invalid_request_metadata')
    directory = Path(os.environ['RUNNER_TEMP']) / 'service-reply' / request_id
    return request_id, digest, directory


def openssl(*args):
    result = subprocess.run(['openssl', *map(str, args)], capture_output=True, timeout=60)
    if result.returncode:
        raise agent.CampaignError('sealed_request_operation_failed')
    return result.stdout


def prepare(directory):
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    private = directory / 'private.key'
    if private.exists():
        raise agent.CampaignError('ephemeral_key_already_exists')
    openssl('req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '1',
            '-subj', '/CN=13URGENT-service-reply', '-keyout', private,
            '-out', directory / 'public.crt')
    private.chmod(0o600)


def validate_payload(raw, request_id, digest):
    if len(raw) > 20000 or hashlib.sha256(raw).hexdigest() != digest:
        raise agent.CampaignError('request_digest_mismatch')
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise agent.CampaignError('invalid_request_payload') from None
    if not isinstance(value, dict) or set(value) != {'request_id', 'to', 'subject', 'body'}:
        raise agent.CampaignError('invalid_request_fields')
    if value['request_id'] != request_id:
        raise agent.CampaignError('request_identity_mismatch')
    address = value['to']
    if (not isinstance(address, str) or len(address) > 254 or '\r' in address or '\n' in address
            or parseaddr(address)[1] != address
            or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", address)):
        raise agent.CampaignError('invalid_service_recipient')
    subject = value['subject']
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 200 or '\r' in subject or '\n' in subject:
        raise agent.CampaignError('invalid_service_subject')
    if not isinstance(value['body'], str) or not value['body'].strip() or len(value['body']) > 12000 or '\x00' in value['body']:
        raise agent.CampaignError('invalid_service_body')
    return value


def fetch_payload(request_id, directory, wait=time.sleep):
    repo = run_campaign.pipeline.REPO
    for _ in range(60):
        fetch = subprocess.run(['git', '-C', str(repo), 'fetch', '--depth=1', 'origin',
                                'refs/heads/mail-replies'], capture_output=True, timeout=30)
        if fetch.returncode == 0:
            result = subprocess.run(['git', '-C', str(repo), 'show',
                                     f'FETCH_HEAD:requests/{request_id}.cms'],
                                    capture_output=True, timeout=30)
            if result.returncode == 0:
                if len(result.stdout) > 50000:
                    raise agent.CampaignError('sealed_request_too_large')
                sealed = directory / 'request.cms'
                sealed.write_bytes(result.stdout)
                return openssl('cms', '-decrypt', '-binary', '-inform', 'DER', '-in', sealed,
                               '-recip', directory / 'public.crt', '-inkey', directory / 'private.key')
        wait(5)
    raise agent.CampaignError('sealed_request_not_received')


def build_message(payload, digest, date):
    mail = EmailMessage(policy=policy.SMTP)
    mail['From'] = 'CHRONOSS — 13 URGENT <' + agent.SENDER + '>'
    mail['To'] = payload['to']
    mail['Cc'] = agent.COPY
    mail['Reply-To'] = agent.SENDER
    mail['Subject'] = payload['subject']
    mail['Date'] = date
    mail['Message-ID'] = '<' + digest + '@13urgent.fr>'
    mail.set_content(payload['body'])
    return mail


def deliver(payload, digest, state_path, password, checkpoint, smtp_factory=None, archive_factory=None):
    if not password:
        raise agent.CampaignError('mail_access_not_connected')
    state_path = Path(state_path)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'schema_version': 1, 'campaigns': {}, 'suppressed': []}
    if state.get('schema_version') != 1:
        raise agent.CampaignError('state_schema')
    records = state['campaigns'].setdefault('service-replies-v1', {})
    record = records.get(payload['request_id'])
    if record and record.get('fingerprint') != digest:
        raise agent.CampaignError('request_content_conflict')
    if record and record['status'] == 'accepted_and_archived':
        return {'status': 'already_recorded', 'emails_sent': 0, 'copy_saved_in_sent': True}
    if record and record['status'] not in ('intent', 'accepted_archive_pending'):
        return {'status': 'blocked_previous_uncertain_result', 'emails_sent': 0, 'copy_saved_in_sent': record.get('archived_in_sent', False)}
    date = record['message_date'] if record else format_datetime(datetime.now(timezone.utc))
    mail = build_message(payload, digest, date)
    archive = archive_factory() if archive_factory else agent.SentArchive(password)
    smtp = None
    def persist():
        agent.save(state_path, state)
        checkpoint()
    try:
        if record:
            if record['status'] == 'intent':
                if not archive.contains(mail['Message-ID']):
                    return {'status': 'blocked_previous_intent', 'emails_sent': 0, 'copy_saved_in_sent': False}
            else:
                archive.append(mail)
            record.update(status='accepted_and_archived', archived_in_sent=True)
            persist()
            return {'status': 'archive_reconciled_without_resend', 'emails_sent': 0, 'copy_saved_in_sent': True}
        smtp = smtp_factory() if smtp_factory else smtplib.SMTP_SSL('ssl0.ovh.net', 465, timeout=30, context=ssl.create_default_context())
        smtp.login(agent.SENDER, password)
        record = {'fingerprint': digest, 'status': 'intent', 'message_date': date,
                  'created_at': datetime.now(timezone.utc).isoformat()}
        records[payload['request_id']] = record
        persist()
        try:
            refused = smtp.send_message(mail, from_addr=agent.SENDER, to_addrs=[payload['to'], agent.COPY])
        except Exception:
            record['status'] = 'uncertain_do_not_retry'
            persist()
            return {'status': 'uncertain_do_not_retry', 'emails_sent': 0, 'copy_saved_in_sent': False}
        record['status'] = 'partial_acceptance' if refused else 'accepted_archive_pending'
        # Persist the accepted outcome before attempting the independent IMAP copy.
        persist()
        try:
            archive.append(mail)
            record['archived_in_sent'] = True
        except Exception:
            record['archived_in_sent'] = False
        if not refused and record['archived_in_sent']:
            record['status'] = 'accepted_and_archived'
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        persist()
        return {'status': record['status'], 'emails_sent': 0 if payload['to'] in refused else 1,
                'copy_saved_in_sent': record['archived_in_sent'], 'delivery_to_recipient_not_verified': True}
    finally:
        if smtp:
            try: smtp.quit()
            except Exception: pass
        archive.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'send'])
    args = parser.parse_args()
    request_id, digest, directory = settings()
    if args.mode == 'prepare':
        prepare(directory)
        print(json.dumps({'status': 'ephemeral_public_certificate_ready'}))
        return 0
    try:
        raw = fetch_payload(request_id, directory)
        payload = validate_payload(raw, request_id, digest)
        _, state_dir = run_campaign.pipeline.setup_runtime()
        result = deliver(payload, digest, state_dir / 'mail-state.json', os.environ.get('CONTACT_MAIL_PASSWORD'),
                         lambda: run_campaign.checkpoint(state_dir))
        print(json.dumps(result))
        return 0 if result['status'] in ('accepted_and_archived', 'already_recorded', 'archive_reconciled_without_resend') else 2
    finally:
        for name in ('private.key', 'request.cms'):
            (directory / name).unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        candidate = str(error)
        code = candidate if isinstance(error, agent.CampaignError) and re.fullmatch('[a-z0-9_]+', candidate) else 'service_reply_execution_failed'
        print(json.dumps({'status': 'blocked', 'error': code, 'emails_sent_in_this_step_not_confirmed': True}))
        raise SystemExit(2)

#!/usr/bin/env python3
"""Execute a verified, explicitly authorized campaign received as sealed CMS data."""
from __future__ import annotations
import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re

import commercial_agent as agent
import run_campaign
import send_service_reply as sealed


def validate_payload(raw, request_id, digest):
    # The shared CMS receiver caps ciphertext at 50 kB.
    if len(raw) > 44000 or hashlib.sha256(raw).hexdigest() != digest:
        raise agent.CampaignError('campaign_digest_mismatch')
    try:
        campaign = json.loads(raw)
    except (ValueError, UnicodeError):
        raise agent.CampaignError('invalid_campaign_payload') from None
    if not isinstance(campaign, dict) or campaign.get('campaign_id') != request_id:
        raise agent.CampaignError('campaign_identity_mismatch')
    rows = agent.campaign_rows(campaign)
    if not rows:
        raise agent.CampaignError('empty_campaign')
    try:
        start = datetime.fromisoformat(campaign['send_not_before'].replace('Z', '+00:00'))
    except (ValueError, TypeError, KeyError, AttributeError):
        raise agent.CampaignError('invalid_campaign_date') from None
    if start.utcoffset() is None:
        raise agent.CampaignError('timezone_required')
    # Validate all deliverable messages before allowing the first SMTP mutation.
    for row in rows:
        if not isinstance(row, dict):
            raise agent.CampaignError('invalid_campaign_recipient')
        if agent.recipient(row):
            try:
                date.fromisoformat(row['verified_on'])
            except (ValueError, TypeError):
                raise agent.CampaignError('invalid_verification_date') from None
            agent.message(row, campaign['campaign_id'])
    return campaign


def recipient_hash(address):
    return hashlib.sha256(address.lower().encode()).hexdigest()


def deliver(campaign, state_path, password, checkpoint, **kwargs):
    state_path = Path(state_path)
    old = json.loads(state_path.read_text()) if state_path.exists() else {'schema_version': 1, 'campaigns': {}}
    if old.get('schema_version') != 1:
        raise agent.CampaignError('state_schema')
    prior = {row.get('recipient_fingerprint') for cid, records in old['campaigns'].items()
             if cid != campaign['campaign_id'] for row in records.values()}
    retained, held = [], []
    for row in campaign['recipients']:
        address = agent.recipient(row)
        if address and recipient_hash(address) in prior:
            held.append({'id': row['id'], 'status': 'held_previous_contact'})
        else:
            retained.append(row)
    current = {**campaign, 'recipients': retained}
    fingerprints = {row['id']: recipient_hash(agent.recipient(row))
                    for row in retained if agent.recipient(row)}

    def durable_checkpoint():
        # Persist opaque recipient hashes with the intent, before SMTP. This
        # protects future sealed campaigns; legacy campaigns need caller exclusion.
        state = json.loads(state_path.read_text())
        for row_id, record in state['campaigns'].get(campaign['campaign_id'], {}).items():
            if row_id in fingerprints:
                record['recipient_fingerprint'] = fingerprints[row_id]
        agent.save(state_path, state)
        checkpoint()

    result = agent.run(current, state_path, execute=True, password=password,
                       checkpoint=durable_checkpoint, **kwargs)
    return held + result


def summary(rows):
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    uncertain = {'intent', 'accepted_archive_pending', 'partial_acceptance',
                 'uncertain_do_not_retry', 'content_conflict'}
    issues = any(row['status'] in uncertain or row.get('recorded_status') in uncertain for row in rows)
    return {'status': 'needs_attention' if issues else 'campaign_processed',
            'counts': counts,
            'copies_saved_in_sent': sum(counts.get(key, 0) for key in
                 ('accepted_and_archived', 'archive_repaired_without_resend', 'reconciled_from_sent_without_resend')),
            'delivery_to_recipient_not_verified': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'send'])
    args = parser.parse_args()
    request_id, digest, directory = sealed.settings()
    if args.mode == 'prepare':
        sealed.prepare(directory)
        print(json.dumps({'status': 'ephemeral_public_certificate_ready'}))
        return 0
    try:
        campaign = validate_payload(sealed.fetch_payload(request_id, directory), request_id, digest)
        _, state_dir = run_campaign.pipeline.setup_runtime()
        rows = deliver(campaign, state_dir / 'mail-state.json', os.environ.get('CONTACT_MAIL_PASSWORD'),
                       lambda: run_campaign.checkpoint(state_dir))
        result = summary(rows)
        print(json.dumps(result))
        return 0 if result['status'] == 'campaign_processed' else 2
    finally:
        for name in ('private.key', 'request.cms'):
            (directory / name).unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        candidate = str(error)
        code = candidate if isinstance(error, agent.CampaignError) and re.fullmatch('[a-z0-9_]+', candidate) else 'sealed_campaign_execution_failed'
        print(json.dumps({'status': 'blocked', 'error': code, 'emails_sent_in_this_step_not_confirmed': True}))
        raise SystemExit(2)

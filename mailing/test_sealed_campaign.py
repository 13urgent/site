import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import send_sealed_campaign as sealed
from test_commercial_agent import ROW, SMTP, Archive


class SealedCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'state.json'
        self.campaign = {'campaign_id': 'sealed-test-1', 'send_not_before': '2026-11-09T00:00:00Z',
                         'recipients': [copy.deepcopy(ROW)]}
        self.smtp, self.archive = SMTP(), Archive()
        self.now = datetime(2026, 11, 10, tzinfo=timezone.utc)

    def validate(self, campaign=None, request_id='sealed-test-1'):
        raw = json.dumps(campaign or self.campaign).encode()
        return sealed.validate_payload(raw, request_id, hashlib.sha256(raw).hexdigest())

    def execute(self, campaign=None):
        return sealed.deliver(campaign or self.campaign, self.state, 'test', lambda: None,
                              smtp_factory=lambda: self.smtp, archive_factory=lambda: self.archive,
                              now=self.now, wait=lambda _: None)

    def test_digest_and_identity_mismatch_fail_before_execution(self):
        with self.assertRaisesRegex(sealed.agent.CampaignError, 'campaign_digest_mismatch'):
            sealed.validate_payload(b'{}', 'sealed-test-1', '0' * 64)
        with self.assertRaisesRegex(sealed.agent.CampaignError, 'campaign_identity_mismatch'):
            self.validate(request_id='another-campaign')

    def test_malformed_date_scope_and_headers_rejected(self):
        for change in ({'send_not_before': 'bad'}, {'recipients': []},
                       {'recipients': [copy.deepcopy(ROW)] * 31}):
            with self.assertRaises(sealed.agent.CampaignError): self.validate({**self.campaign, **change})
        changed = copy.deepcopy(self.campaign)
        changed['recipients'][0]['subject'] += '\nBcc: other@example.net'
        with self.assertRaises(sealed.agent.CampaignError): self.validate(changed)

    def test_missing_verified_address_is_held_without_connection(self):
        self.campaign['recipients'][0]['email_status'] = 'missing'
        self.validate()
        self.assertEqual(self.execute()[0]['status'], 'held_missing_verified_address')
        self.assertEqual(self.smtp.calls, [])

    def test_send_is_deduplicated_archived_and_private(self):
        self.validate()
        self.assertEqual(self.execute()[0]['status'], 'accepted_and_archived')
        self.assertEqual(self.execute()[0]['status'], 'already_recorded')
        self.assertEqual(len(self.smtp.calls), 1)
        self.assertEqual(len(self.archive.calls), 1)
        self.assertIn('STOP', self.smtp.calls[0][0].get_content())
        self.assertNotIn(ROW['to'], self.state.read_text())
        self.assertNotIn(ROW['subject'], self.state.read_text())
        self.assertIn('recipient_fingerprint', self.state.read_text())

    def test_cross_campaign_repeat_is_held(self):
        self.execute()
        changed = {**self.campaign, 'campaign_id': 'sealed-test-2'}
        self.assertEqual(self.execute(changed)[0]['status'], 'held_previous_contact')
        self.assertEqual(len(self.smtp.calls), 1)

    def test_archive_repair_does_not_resend(self):
        self.archive.fail = True
        self.assertEqual(self.execute()[0]['status'], 'accepted_archive_pending')
        self.archive.fail = False
        self.assertEqual(self.execute()[0]['status'], 'archive_repaired_without_resend')
        self.assertEqual(len(self.smtp.calls), 1)

    def test_uncertain_send_is_not_retried(self):
        self.smtp.fail = True
        self.assertEqual(self.execute()[0]['status'], 'uncertain_do_not_retry')
        self.assertEqual(self.execute()[0]['recorded_status'], 'uncertain_do_not_retry')
        self.assertEqual(len(self.smtp.calls), 1)


if __name__ == '__main__': unittest.main()

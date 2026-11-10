import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import send_service_reply as reply
from test_commercial_agent import SMTP, Archive


class ServiceReplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'mail-state.json'
        self.payload = {'request_id': 'service-test-1', 'to': 'person@example.net',
                        'subject': 'Precisions concernant votre demande', 'body': 'Bonjour,\nMerci de preciser les adresses.\nCHRONOSS'}
        self.raw = json.dumps(self.payload).encode()
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def send(self, smtp, archive, checkpoint=lambda: None):
        return reply.deliver(self.payload, self.digest, self.state, 'test', checkpoint,
                             smtp_factory=lambda: smtp, archive_factory=lambda: archive)

    def test_digest_and_header_injection_rejected(self):
        with self.assertRaisesRegex(reply.agent.CampaignError, 'request_digest_mismatch'):
            reply.validate_payload(self.raw, self.payload['request_id'], '0' * 64)
        for key in ('to', 'subject'):
            changed = {**self.payload, key: self.payload[key] + '\nBcc: other@example.net'}
            raw = json.dumps(changed).encode()
            with self.assertRaises(reply.agent.CampaignError):
                reply.validate_payload(raw, self.payload['request_id'], hashlib.sha256(raw).hexdigest())

    def test_send_and_archive_are_idempotent_and_private(self):
        smtp, archive = SMTP(), Archive()
        self.assertEqual(self.send(smtp, archive)['status'], 'accepted_and_archived')
        self.assertEqual(self.send(smtp, archive)['status'], 'already_recorded')
        self.assertEqual(len(smtp.calls), 1)
        self.assertEqual(len(archive.calls), 1)
        self.assertNotIn('person@example.net', self.state.read_text())
        self.assertNotIn('STOP', smtp.calls[0][0].get_content())

    def test_archive_repair_never_resends(self):
        smtp, archive = SMTP(), Archive(fail=True)
        self.assertEqual(self.send(smtp, archive)['status'], 'accepted_archive_pending')
        archive.fail = False
        self.assertEqual(self.send(smtp, archive)['status'], 'archive_reconciled_without_resend')
        self.assertEqual(len(smtp.calls), 1)

    def test_uncertain_send_never_retried(self):
        smtp, archive = SMTP(fail=True), Archive()
        self.assertEqual(self.send(smtp, archive)['status'], 'uncertain_do_not_retry')
        self.assertEqual(self.send(smtp, archive)['status'], 'blocked_previous_uncertain_result')
        self.assertEqual(len(smtp.calls), 1)

    def test_checkpoint_failure_prevents_send(self):
        smtp, archive = SMTP(), Archive()
        def fail(): raise RuntimeError('checkpoint failed')
        with self.assertRaises(RuntimeError): self.send(smtp, archive, checkpoint=fail)
        self.assertEqual(len(smtp.calls), 0)


if __name__ == '__main__':
    unittest.main()

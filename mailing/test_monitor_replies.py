from datetime import datetime, timezone
from email.message import EmailMessage
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import monitor_replies as monitor
from test_delivery_status import dsn


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.fp = 'a' * 64
        self.address = 'commercial@example.net'
        self.record = {'fingerprint': self.fp, 'recipient_fingerprint': hashlib.sha256(self.address.encode()).hexdigest(),
                       'status': 'accepted_and_archived', 'archived_in_sent': True, 'created_at': '2026-11-09T15:00:00+00:00'}
        self.index = {self.fp: [self.record]}
        self.checked = '2026-11-10T09:15:00+00:00'

    def reply(self, body='Bonjour, précisons notre besoin.', sender=None, **headers):
        message = EmailMessage()
        message['From'] = sender or self.address
        message['In-Reply-To'] = '<' + self.fp + '@13urgent.fr>'
        for key, value in headers.items(): message[key.replace('_', '-')] = value
        message.set_content(body)
        return message.as_bytes()

    def process(self, raw): return monitor.process_message(raw, self.index, self.checked)

    def test_exact_dsn_matches_but_unrelated_and_owner_copy_do_not(self):
        self.assertEqual(self.process(dsn('<' + self.fp + '@13urgent.fr>', self.address)), (1, 0, 0))
        self.assertTrue(self.record['blocked_for_resend'])
        self.assertEqual(self.process(dsn('<' + 'b' * 64 + '@13urgent.fr>', self.address)), (0, 0, 0))
        self.assertEqual(self.process(dsn('<' + self.fp + '@13urgent.fr>', monitor.agent.COPY)), (0, 0, 0))

    def test_mismatched_failed_recipient_not_attributed(self):
        self.assertEqual(self.process(dsn('<' + self.fp + '@13urgent.fr>', 'other@example.net')), (0, 0, 0))
        self.assertNotIn('delivery_status', self.record)

    def test_reply_flag_is_qualification_only_and_idempotent(self):
        self.assertEqual(self.process(self.reply()), (0, 1, 0))
        self.assertTrue(self.record['response_received_to_qualify'])
        self.assertEqual(self.process(self.reply()), (0, 0, 0))
        self.assertNotIn('customer', self.record)

    def test_owner_copies_and_auto_responses_excluded(self):
        self.assertEqual(self.process(self.reply(sender=monitor.agent.COPY)), (0, 0, 0))
        self.assertEqual(self.process(self.reply(Auto_Submitted='auto-replied')), (0, 0, 0))
        self.assertEqual(self.process(self.reply(Precedence='bulk')), (0, 0, 0))

    def test_explicit_stop_blocks_but_quoted_footer_does_not(self):
        self.assertEqual(self.process(self.reply('Bonjour, nous allons regarder.\n\n> Répondez STOP.')), (0, 1, 0))
        self.assertNotIn('opted_out', self.record)
        self.assertEqual(self.process(self.reply('STOP\n\n> Message original')), (0, 0, 1))
        self.assertTrue(self.record['opted_out'])
        self.assertTrue(self.record['blocked_for_resend'])

    def test_readonly_bounded_scan_and_no_private_ledger_content(self):
        raw = self.reply('STOP')
        class IMAP:
            readonly = False
            query = None
            def login(self, *args): pass
            def select(inner, folder, readonly=False): inner.readonly = readonly; return 'OK', []
            def uid(inner, command, *args):
                if command == 'SEARCH': inner.query = args; return 'OK', [b'1']
                self.assertIn('PEEK', args[1])
                return 'OK', [(b'1 (UID 1 BODY[] {100}', raw)]
            def logout(self): pass
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            path.write_text(json.dumps({'schema_version': 1, 'campaigns': {'test': {'1': self.record}}, 'suppressed': []}))
            client = IMAP()
            result = monitor.monitor(path, 'fake', lambda: None, imap_factory=lambda: client,
                                     now=datetime(2026, 11, 10, tzinfo=timezone.utc))
            self.assertTrue(client.readonly)
            self.assertIn('09-Nov-2026', client.query)
            self.assertEqual(result['oppositions_new'], 1)
            self.assertEqual(result['emails_sent'], 0)
            self.assertNotIn(self.address, path.read_text())
            self.assertNotIn('STOP', path.read_text())

    def test_scan_never_goes_beyond_fourteen_days(self):
        self.record['created_at'] = '2026-01-01T00:00:00+00:00'
        state = {'campaigns': {'test': {'1': self.record}}}
        self.assertEqual(monitor.scan_since(state, datetime(2026, 11, 10, tzinfo=timezone.utc)), '27-Oct-2026')


if __name__ == '__main__': unittest.main()

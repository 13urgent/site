import hashlib
import json
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import incoming_quotes as incoming
from test_commercial_agent import SMTP, Archive

NOW = datetime(2026, 11, 10, 14, tzinfo=timezone.utc)


def mail(body='Merci de nous faire votre offre de transport : 3 palettes Tandoori, 100 kg.\nTest Client',
         sender='Test Client <customer@example.net>', message_id='<request-1@example.net>', **headers):
    message = EmailMessage(); message['From'] = sender; message['To'] = incoming.agent.SENDER
    message['Subject'] = 'Demande de transport'; message['Message-ID'] = message_id
    message['Date'] = NOW.strftime('%a, %d %b %Y %H:%M:%S +0000')
    for key, value in headers.items(): message[key.replace('_', '-')] = value
    message.set_content(body); return message


class IncomingTests(unittest.TestCase):
    def setUp(self):
        self.signature = patch.object(incoming, 'TARGET_SIGNATURE_HASH', hashlib.sha256(b'client').hexdigest())
        self.signature.start(); self.addCleanup(self.signature.stop)

    def test_two_target_types_selected_latest_original_and_not_pickup_body_address(self):
        first = mail('Offre de transport : 3 palettes Tandoori 100 kg.\nContact enlèvement: pickup@example.org\nTest Client')
        newer = mail(message_id='<request-new@example.net>')
        cooler = mail('Merci de nous faire votre offre de transport : refroidisseur de bouteilles BE-200, 96 KG.\nTest Client', message_id='<cooler@example.net>')
        rows = incoming.select_requests([(first.as_bytes(), NOW-timedelta(hours=1)), (newer.as_bytes(), NOW), (cooler.as_bytes(), NOW)], 'probe_requests')
        self.assertEqual([r['kind'] for r in rows], ['pallets_uk', 'equipment_be_fr'])
        self.assertEqual(rows[0]['message_id'], '<request-new@example.net>')
        self.assertEqual(rows[0]['recipient'], 'customer@example.net')

    def test_own_messages_bulk_stop_and_external_reply_to_are_excluded(self):
        cases = [mail(sender=incoming.agent.SENDER), mail(Precedence='bulk'), mail(Auto_Submitted='auto-replied'),
                 mail('STOP'), mail(Reply_To='other@attacker.example')]
        for item in cases: self.assertIsNone(incoming.describe(item.as_bytes(), NOW))
        self.assertIsNone(incoming.single_address('person@example.net\nBcc: x@example.org'))
        self.assertIsNone(incoming.single_address('a@example.org, b@example.org'))

    def test_own_reference_blocks_followup_reply_and_original_quote_not_selected(self):
        reply = mail(In_Reply_To='<'+'a'*64+'@13urgent.fr>')
        request = incoming.describe(reply.as_bytes(), NOW)
        self.assertTrue(request['follows_own'])
        self.assertEqual(incoming.select_requests([(reply.as_bytes(), NOW)], 'reply_requests'), [])
        forwarded = mail('Bonjour\n\nFrom: Test Client\nMerci offre transport 3 palettes Tandoori 100 kg.\nTest Client')
        self.assertIsNone(incoming.describe(forwarded.as_bytes(), NOW))
        short = mail('Mardi, hayon oui.', In_Reply_To='<'+'a'*64+'@13urgent.fr>')
        short_request = incoming.describe(short.as_bytes(), NOW)
        self.assertEqual(short_request['kind'], 'linked_followup')
        self.assertTrue(short_request['follows_own'])

    def test_automatic_activation_gate_and_missing_fields(self):
        old = mail(message_id='<old@example.net>')
        rows = incoming.select_requests([(old.as_bytes(), incoming.ACTIVATED_AT-timedelta(seconds=1)), (mail().as_bytes(), NOW)], 'automatic', NOW)
        self.assertEqual(len(rows), 1)
        self.assertIn('dates', incoming.missing_fields(rows[0]))
        self.assertNotIn('weight', incoming.missing_fields(rows[0]))

    def test_threaded_service_reply_has_no_marketing_footer_or_price(self):
        request = incoming.describe(mail().as_bytes(), NOW); payload = incoming.payload_for(request)
        message = incoming.message_builder(request)(payload, 'a'*64, NOW.isoformat())
        self.assertEqual(message['In-Reply-To'], request['message_id'])
        self.assertEqual(message['Auto-Submitted'], 'auto-replied')
        self.assertEqual(message['To'], 'customer@example.net')
        self.assertEqual(message['Cc'], incoming.agent.COPY)
        self.assertNotIn('STOP', message.get_content())
        self.assertNotIn('€', message.get_content())

    def test_delivery_deduplication_archive_repair_and_private_ledger(self):
        request = incoming.describe(mail().as_bytes(), NOW); payload = incoming.payload_for(request)
        digest = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        smtp, archive = SMTP(), Archive(fail=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'mail-state.json'
            def send():
                return incoming.service.deliver(payload, digest, path, 'test', lambda:None,
                    smtp_factory=lambda:smtp, archive_factory=lambda:archive, message_builder=incoming.message_builder(request))
            self.assertEqual(send()['status'], 'accepted_archive_pending')
            archive.fail=False
            self.assertEqual(send()['status'], 'archive_reconciled_without_resend')
            self.assertEqual(send()['status'], 'already_recorded')
            self.assertEqual(len(smtp.calls), 1)
            text=path.read_text(); self.assertNotIn('customer@example.net', text); self.assertNotIn(request['message_id'], text)

    def test_uncertainty_and_checkpoint_failure_never_send_twice(self):
        request = incoming.describe(mail().as_bytes(), NOW); payload=incoming.payload_for(request)
        digest='a'*64; smtp, archive=SMTP(fail=True),Archive()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            def send(checkpoint=lambda:None):
                return incoming.service.deliver(payload,digest,path,'test',checkpoint,
                    smtp_factory=lambda:smtp,archive_factory=lambda:archive,message_builder=incoming.message_builder(request))
            self.assertEqual(send()['status'],'uncertain_do_not_retry')
            self.assertEqual(send()['status'],'blocked_previous_uncertain_result')
            self.assertEqual(len(smtp.calls),1)
        smtp.calls.clear()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            def fail(): raise RuntimeError('checkpoint')
            with self.assertRaises(RuntimeError):
                incoming.service.deliver(payload,digest,path,'test',fail,smtp_factory=lambda:smtp,
                    archive_factory=lambda:archive,message_builder=incoming.message_builder(request))
            self.assertEqual(len(smtp.calls),0)

    def test_attachment_is_held_without_external_send(self):
        item=mail('Merci de votre offre de transport pour 2 palettes de materiel, 100 kg, adresse TEST.'); item.add_attachment(b'test',maintype='application',subtype='pdf',filename='test.pdf')
        request=incoming.describe(item.as_bytes(),NOW); self.assertTrue(request['attachments'])
        with tempfile.TemporaryDirectory() as directory:
            client=type('Client',(),{'select':lambda *a:('NO',[]),'create':lambda *a:('NO',[])})()
            with patch.object(incoming,'private_task',return_value=False):
                result=incoming.process([request],Path(directory)/'state.json','test',lambda:None,client,
                                       deliver=lambda *a,**k:self.fail('must not send'))
            self.assertEqual(result['counts'],{'attachments_need_review':1})


if __name__ == '__main__': unittest.main()

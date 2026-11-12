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
        explicit = incoming.select_requests([(reply.as_bytes(), NOW)], 'reply_requests')
        self.assertEqual(len(explicit), 1)
        self.assertTrue(explicit[0]['explicitly_requested_reply'])
        probe = incoming.select_requests([(reply.as_bytes(), NOW)], 'probe_requests')
        self.assertFalse(probe[0]['explicitly_requested_reply'])
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

    def test_automatic_filters_completed_requests_before_thirty_item_limit(self):
        messages = [(mail(message_id='<request-'+str(i)+'@example.net>').as_bytes(), NOW) for i in range(32)]
        requests = incoming.select_requests(messages, 'automatic', NOW)
        self.assertEqual(len(requests), 32)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            completed = {r['source_hash']: {'workflow_status': 'accepted_and_archived', 'task_archive_saved': True} for r in requests[:31]}
            path.write_text(json.dumps({'schema_version':1,'campaigns':{'inbound-requests-v1':completed},'suppressed':[]}))
            sent = []
            def send(payload, *args, **kwargs):
                sent.append(payload['request_id'])
                return {'status':'accepted_and_archived','emails_sent':1,'copy_saved_in_sent':True}
            with patch.object(incoming,'private_task',return_value=True):
                result = incoming.process(requests,path,'test',lambda:None,object(),deliver=send,automatic=True)
            self.assertEqual(result['already_processed_skipped'],31)
            self.assertEqual(sent,['inbound-'+requests[31]['source_hash']])

    def test_pending_archive_repairs_and_failed_task_copies_are_not_skipped(self):
        request=incoming.describe(mail().as_bytes(),NOW)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            for record in ({'workflow_status':'accepted_archive_pending','task_archive_saved':True},
                           {'workflow_status':'accepted_and_archived','task_archive_saved':False}):
                path.write_text(json.dumps({'campaigns':{'inbound-requests-v1':{request['source_hash']:record}}}))
                selected,skipped=incoming.unprocessed_requests([request],path)
                self.assertEqual(selected,[request]);self.assertEqual(skipped,0)

    def test_only_explicit_targeted_selection_may_reply_to_prior_outreach_thread(self):
        raw=mail(In_Reply_To='<'+'a'*64+'@13urgent.fr>').as_bytes()
        explicit=incoming.select_requests([(raw,NOW)],'reply_requests',NOW)
        automatic=incoming.select_requests([(raw,NOW)],'automatic',NOW)
        with tempfile.TemporaryDirectory() as directory, patch.object(incoming,'private_task',return_value=True):
            calls=[]
            def send(payload,*args,**kwargs):
                calls.append(payload['request_id'])
                return {'status':'accepted_and_archived','emails_sent':1,'copy_saved_in_sent':True}
            result=incoming.process(explicit,Path(directory)/'explicit.json','test',lambda:None,object(),deliver=send)
            self.assertEqual(result['emails_sent'],1)
            result=incoming.process(automatic,Path(directory)/'automatic.json','test',lambda:None,object(),deliver=send,automatic=True)
            self.assertEqual(result['counts'],{'followup_needs_review':1})
            self.assertEqual(len(calls),1)

    def followup_state(self):
        source = hashlib.sha256(b'<original@example.net>').hexdigest()
        return {'schema_version': 1, 'suppressed': [], 'campaigns': {
            'inbound-requests-v1': {source: {'inquiry_kind': 'equipment_be_fr'}},
            'service-replies-v1': {'inbound-'+source: {'fingerprint': 'b'*64,
                                                      'status': 'accepted_and_archived'}}}}

    def photo_followup(self):
        message = mail('Bonjour, le colis est prêt pour enlèvement immédiat. '
                       'La photo est jointe. Prévoir un camion avec hayon au déchargement.',
                       message_id='<photo-reply@example.net>', In_Reply_To='<'+'b'*64+'@13urgent.fr>')
        message.add_attachment(b'x'*400000, maintype='image', subtype='jpeg', filename='photo.jpg')
        return message

    def test_photo_larger_than_read_limit_keeps_text_for_private_triage(self):
        raw = self.photo_followup().as_bytes()[:262144]
        client = type('Client', (), {'select': lambda *a, **k: ('OK', []),
            'uid': lambda self, cmd, *args: ('OK', [b'7']) if cmd == 'SEARCH' else
                ('OK', [(b'7 (INTERNALDATE "12-Nov-2026 11:00:00 +0000")', raw)])})()
        messages, _ = incoming.read_messages(client, 'automatic', NOW)
        self.assertEqual(len(messages), 1)
        request = incoming.describe(*messages[0])
        self.assertTrue(request['source_truncated'])
        self.assertTrue(request['attachments'])
        self.assertIn('hayon', request['text'])
        with tempfile.TemporaryDirectory() as directory, patch.object(incoming, 'private_task', return_value=True):
            result = incoming.process([request], Path(directory)/'state.json', 'test', lambda:None,
                object(), deliver=lambda *a, **k:self.fail('partial automatic message must not send'))
        self.assertEqual(result['counts'], {'partial_message_needs_review': 1})

    def test_target_followup_requires_exact_sender_and_known_parent(self):
        raw = self.photo_followup().as_bytes()[:262144]
        target = hashlib.sha256(b'customer@example.net').hexdigest()
        selected = incoming.select_followup([(raw, NOW)], self.followup_state(), target)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['parent_kind'], 'equipment_be_fr')
        self.assertTrue(selected[0]['source_truncated'])
        self.assertFalse(incoming.select_followup([(raw, NOW)], self.followup_state(), '0'*64))
        self.assertFalse(incoming.select_followup([(raw, NOW)], {'campaigns': {}}, target))
        audit = {}
        incoming.select_followup([(raw, NOW)], {'campaigns': {}}, target, audit=audit)
        self.assertEqual(audit, {'target_sender_messages_seen': 1,
                                'target_ready_candidates_seen': 1, 'linked_candidates_seen': 0})
        with self.assertRaises(incoming.agent.CampaignError):
            incoming.select_followup([(raw, NOW)], self.followup_state(), 'not-a-hash')

    def test_original_reference_resolves_parent_but_other_quote_does_not(self):
        target = hashlib.sha256(b'customer@example.net').hexdigest()
        related = mail('Le colis est prêt, hayon nécessaire.', In_Reply_To='<original@example.net>')
        self.assertEqual(incoming.select_followup([(related.as_bytes(), NOW)], self.followup_state(), target)[0]['parent_kind'], 'equipment_be_fr')
        unrelated = mail('Le colis est prêt, hayon nécessaire.', In_Reply_To='<unknown@example.net>')
        self.assertFalse(incoming.select_followup([(unrelated.as_bytes(), NOW)], self.followup_state(), target))

    def test_followup_reply_stays_threaded_deduplicated_and_has_no_price(self):
        raw = self.photo_followup().as_bytes()[:262144]
        target = hashlib.sha256(b'customer@example.net').hexdigest()
        state = self.followup_state()
        request = incoming.select_followup([(raw, NOW)], state, target)
        smtp, archive = SMTP(), Archive()
        def deliver(payload, digest, path, password, checkpoint, **kwargs):
            return incoming.service.deliver(payload, digest, path, password, checkpoint,
                smtp_factory=lambda:smtp, archive_factory=lambda:archive, **kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(incoming, 'private_task', return_value=True):
            path = Path(directory)/'state.json';path.write_text(json.dumps(state))
            first = incoming.process_followup(request, path, 'test', lambda:None, object(), deliver=deliver)
            second = incoming.process_followup(request, path, 'test', lambda:None, object(), deliver=deliver)
            self.assertEqual(first['status'], 'accepted_and_archived')
            self.assertEqual(second['status'], 'already_recorded')
            self.assertNotIn('customer@example.net', path.read_text())
        self.assertEqual(len(smtp.calls), 1)
        message = smtp.calls[0][0]
        self.assertEqual(message['In-Reply-To'], '<photo-reply@example.net>')
        self.assertNotIn('€', message.get_content())
        self.assertNotIn('douani', message.get_content())
        self.assertIn('horaires exacts', message.get_content())

    def test_delayed_followup_reconfirms_availability_instead_of_assuming_still_ready(self):
        request = {'parent_kind': 'equipment_be_fr', 'received_at': NOW}
        from datetime import timedelta
        fresh = incoming.followup_body(request, now=NOW)
        delayed = incoming.followup_body(request, now=NOW+timedelta(days=2))
        self.assertNotIn('toujours disponible', fresh)
        self.assertIn('toujours disponible', delayed)
        self.assertIn('excuser pour le délai', delayed)
        self.assertIn('au déchargement est bien pris en compte', delayed)
        self.assertNotIn('€', delayed)


if __name__ == '__main__': unittest.main()

import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
import test_incoming_quotes as fixtures
mail=fixtures.mail
NOW=fixtures.NOW
from test_commercial_agent import SMTP,Archive
import thread_receipts as module


class ThreadReceiptTests(unittest.TestCase):
    def test_latest_reply_is_selected_without_photo_keywords_and_old_mail_is_held(self):
        state=fixtures.IncomingTests().followup_state();target=hashlib.sha256(b'customer@example.net').hexdigest()
        old=mail('Colis prêt, hayon.',In_Reply_To='<original@example.net>')
        new=mail('Les horaires sont de 8h à 17h.',message_id='<latest@example.net>',In_Reply_To='<original@example.net>')
        rows=module.latest_replies([(old.as_bytes(),NOW-timedelta(days=2)),(new.as_bytes(),NOW)],state,target,NOW)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['message_id'],'<latest@example.net>')
        self.assertFalse(module.latest_replies([(old.as_bytes(),NOW-timedelta(days=2))],state,target,NOW))

    def test_receipt_is_threaded_accepted_once_and_owner_alert_failure_prevents_false_ack(self):
        state=fixtures.IncomingTests().followup_state();request=module.latest_replies([(mail('Les horaires sont de 8h à 17h.',In_Reply_To='<original@example.net>').as_bytes(),NOW)],state,hashlib.sha256(b'customer@example.net').hexdigest(),NOW)[0]
        smtp,archive=SMTP(),Archive()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state.json';path.write_text(json.dumps(state))
            def deliver(payload,digest,*args,**kw):return module.incoming.service.deliver(payload,digest,*args,smtp_factory=lambda:smtp,archive_factory=lambda:archive,**kw)
            with patch.object(module,'owner_notice',return_value=True),patch.object(module.incoming,'private_task',return_value=True):
                first=module.process([request],path,'test',lambda:None,object(),deliver=deliver)
                second=module.process([request],path,'test',lambda:None,object(),deliver=deliver)
            self.assertEqual(first[0]['status'],'accepted_and_archived');self.assertEqual(second[0]['status'],'already_recorded');self.assertEqual(len(smtp.calls),1)
            msg=smtp.calls[0][0];self.assertEqual(msg['In-Reply-To'],request['message_id']);self.assertIn('bien reçu',msg.get_content());self.assertNotIn('€',msg.get_content())
            self.assertNotIn('customer@example.net',path.read_text())
            with patch.object(module,'owner_notice',return_value=False):
                result=module.process([request],path,'test',lambda:None,object(),deliver=lambda *a,**k:self.fail('no receipt before owner alert'))
            self.assertEqual(result[0]['status'],'owner_alert_failed')


if __name__=='__main__':unittest.main()

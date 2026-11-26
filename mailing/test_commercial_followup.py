import unittest,copy,json,tempfile,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from email.message import EmailMessage
import commercial_followup as f
NOW=datetime(2026,12,4,10,tzinfo=timezone.utc)
class FollowupTests(unittest.TestCase):
 def record(self):return {'status':'accepted_and_archived','fingerprint':'a'*64,'recipient_fingerprint':hashlib.sha256(b'contact@example.test').hexdigest(),'followup_allowed':True,'followup_count':0,'created_at':'2026-11-26T18:00:00+00:00','followup_due_at':'2026-12-03T18:00:00+00:00','service_category':'urgent'}
 def state(self,r=None):return {'schema_version':1,'campaigns':{'direction-test':{'p1':r or self.record()}},'suppressed_hashes':[]}
 def test_only_due_authorized_and_confirmed_initial_messages(self):
  self.assertEqual(len(f.eligible(self.state(),NOW)),1)
  for change in [{'response_received_to_qualify':True},{'opted_out':True},{'blocked_for_resend':True},{'delivery_status':'hard_bounced'},{'followup_count':1},{'status':'uncertain_do_not_retry'},{'followup_allowed':False}]:self.assertEqual(f.eligible(self.state({**self.record(),**change}),NOW),[])
  self.assertEqual(f.eligible(self.state(),NOW-timedelta(days=2)),[])
  s=self.state();s['suppressed_hashes']=[self.record()['recipient_fingerprint']];self.assertEqual(f.eligible(s,NOW),[])
 def execute_twice(self,send_status):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'state.json';p.write_text(json.dumps(self.state()));calls=[]
   class Archive:
    def close(self):pass
   def send(payload,*a,**kw):calls.append(payload);return {'status':send_status,'emails_sent':int(send_status=='accepted_and_archived')}
   with patch.object(f,'original',return_value=('contact@example.test','Sujet','<'+('a'*64)+'@13urgent.fr>')),patch.object(f.agent,'verified_pdf',return_value=(b'%PDF-FAKE','presentation.pdf','b'*64)):
    f.execute(p,'test',lambda:None,NOW,send,Archive);f.execute(p,'test',lambda:None,NOW,send,Archive)
   self.assertEqual(len(calls),1);self.assertEqual(json.loads(p.read_text())['campaigns']['direction-test']['p1']['followup_count'],1);self.assertNotIn('@',p.read_text());self.assertIn('STOP',calls[0]['body'])
 def test_single_followup_never_repeats(self):self.execute_twice('accepted_and_archived')
 def test_uncertain_followup_never_repeats(self):self.execute_twice('uncertain_do_not_retry')
 def test_sent_recipient_must_match_original_fingerprint(self):
  m=EmailMessage();m['From']='contact@13urgent.fr';m['To']='other@example.test';m['Message-ID']='<'+('a'*64)+'@13urgent.fr>';m.set_content('FICTIF')
  class Client:
   def uid(self,action,*args):return ('OK',[b'1']) if action=='SEARCH' else ('OK',[(b'1',m.as_bytes())])
  class Archive:client=Client()
  with self.assertRaisesRegex(f.agent.CampaignError,'original_sent_recipient_mismatch'):f.original(Archive(),self.record())

import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
import commercial_agent as a
ROW={'id':'prospect-1','company':'Entreprise exemple','to':'contact@entreprise-exemple.fr','email_status':'verified','source_url':'https://entreprise-exemple.fr/contact','verified_on':'2026-11-06','subject':'Votre transport professionnel','body':'Bonjour,\nDécouvrez 13 URGENT : https://13urgent.fr/\nÉquipe commerciale — CHRONOSS'}
class SMTP:
 def __init__(self,fail=False):self.calls=[];self.fail=fail
 def login(self,u,p):assert u==a.SENDER
 def send_message(self,msg,from_addr,to_addrs):
  self.calls.append((msg,from_addr,to_addrs))
  if self.fail:raise TimeoutError()
  return {}
 def quit(self):pass
class Archive:
 def __init__(self,fail=False):self.calls=[];self.ids=set();self.fail=fail
 def contains(self,mid):return mid in self.ids
 def append(self,msg):
  if self.fail:raise a.CampaignError('sent_archive_failed')
  self.calls.append(msg);self.ids.add(msg['Message-ID'])
 def close(self):pass
class IMAP:
 def __init__(self,rows):self.rows=rows;self.append_calls=[];self.found=False
 def login(self,u,p):pass
 def list(self):return 'OK',self.rows
 def select(self,f):self.folder=f;return 'OK',[b'0']
 def uid(self,*args):return 'OK',[b'1' if self.found else b'']
 def append(self,*args):self.append_calls.append(args);self.found=True;return 'OK',[b'APPENDUID']
 def logout(self):pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.state=Path(self.tmp.name)/'state.json';self.campaign={'campaign_id':'novembre2026','send_not_before':'2026-11-09T08:30:00+01:00','recipients':[copy.deepcopy(ROW)]};self.now=datetime(2026,11,9,9,tzinfo=timezone.utc)
 def execute(self,smtp,archive,**kwargs):return a.run(self.campaign,self.state,True,lambda:smtp,'test-secret',self.now,wait=lambda s:None,archive_factory=lambda:archive,**kwargs)
 def test_preview_never_connects_and_sets_contact_sender_copy_optout(self):
  rows=a.run(self.campaign,self.state,smtp_factory=lambda:(_ for _ in ()).throw(Exception()))
  self.assertEqual(rows[0]['status'],'ready_preview');text=rows[0]['message'];self.assertIn(a.COPY,text);self.assertIn(a.SENDER,text);self.assertNotIn('commercial@13urgent.fr',text);self.assertIn('STOP',text);self.assertFalse(self.state.exists())
 def test_send_archives_in_sent_and_deduplicates_on_rerun(self):
  smtp=SMTP();archive=Archive();r=self.execute(smtp,archive)
  self.assertEqual(r[0]['status'],'accepted_and_archived');self.assertEqual(smtp.calls[0][2],[ROW['to'],a.COPY]);self.assertEqual(smtp.calls[0][1],'contact@13urgent.fr');self.assertEqual(len(archive.calls),1)
  self.assertEqual(self.execute(smtp,archive)[0]['status'],'already_recorded');self.assertEqual(len(smtp.calls),1);self.assertNotIn('test-secret',self.state.read_text())
 def test_archive_failure_repaired_without_second_external_send(self):
  smtp=SMTP();archive=Archive(fail=True)
  self.assertEqual(self.execute(smtp,archive)[0]['status'],'accepted_archive_pending');archive.fail=False
  self.assertEqual(self.execute(smtp,archive)[0]['status'],'archive_repaired_without_resend');self.assertEqual(len(smtp.calls),1);self.assertEqual(len(archive.calls),1)
 def test_missing_sent_prevents_external_send(self):
  smtp=SMTP()
  def fail():raise a.CampaignError('sent_folder_missing_or_ambiguous')
  with self.assertRaises(a.CampaignError):a.run(self.campaign,self.state,True,lambda:smtp,'x',self.now,archive_factory=fail)
  self.assertEqual(smtp.calls,[]);self.assertFalse(self.state.exists())
 def test_timeout_not_retried_or_falsely_archived(self):
  smtp=SMTP(fail=True);archive=Archive();self.assertEqual(self.execute(smtp,archive)[0]['status'],'uncertain_do_not_retry');r=self.execute(smtp,archive);self.assertEqual(r[0]['recorded_status'],'uncertain_do_not_retry');self.assertEqual(len(smtp.calls),1);self.assertEqual(archive.calls,[])
 def test_remote_checkpoint_fails_before_send(self):
  smtp=SMTP();archive=Archive()
  def fail():raise RuntimeError('checkpoint')
  with self.assertRaises(RuntimeError):self.execute(smtp,archive,checkpoint=fail)
  self.assertEqual(smtp.calls,[])
 def test_imap_special_sent_and_idempotent_copy(self):
  server=IMAP([b'(\\HasNoChildren) "." "INBOX"',b'(\\HasNoChildren \\Sent) "." "INBOX.Sent"'])
  archive=a.SentArchive('fake',imap_factory=lambda:server);m,_=a.message(ROW,'test');archive.append(m);archive.append(m)
  self.assertEqual(server.folder,'"INBOX.Sent"');self.assertEqual(len(server.append_calls),1)
 def test_french_singular_sent_folder(self):
  server=IMAP([b'(\\HasNoChildren) "." "INBOX.Envoy&AOk-"'])
  archive=a.SentArchive('fake',imap_factory=lambda:server)
  self.assertEqual(archive.folder,'"INBOX.Envoy&AOk-"')
 def test_literal_french_folder_response(self):
  server=IMAP([(b'(\\HasNoChildren) "." {11}',b'Envoy&AOk-s')])
  archive=a.SentArchive('fake',imap_factory=lambda:server)
  self.assertEqual(archive.folder,'"Envoy&AOk-s"')
 def test_only_visible_subscribed_sent_selected(self):
  server=IMAP([b'() "." "Sent"',b'() "." "INBOX.Sent"'])
  server.lsub=lambda:('OK',[b'() "." "INBOX.Sent"'])
  archive=a.SentArchive('fake',imap_factory=lambda:server)
  self.assertEqual(archive.folder,'"INBOX.Sent"')
 def test_missing_dpo_and_header_injection_are_held(self):
  for change in [{'email_status':'missing'},{'to':'dpo@entreprise-exemple.fr'},{'to':'x@entreprise-exemple.fr\nBcc: attacker@example.fr'}]:self.assertIsNone(a.recipient({**ROW,**change}))
 def test_no_sends_before_monday_or_without_access(self):
  with self.assertRaisesRegex(a.CampaignError,'before_campaign_date'):a.run(self.campaign,self.state,True,password='x',now=datetime(2026,11,6,tzinfo=timezone.utc))
  with self.assertRaisesRegex(a.CampaignError,'mail_access_not_connected'):a.run(self.campaign,self.state,True,now=self.now)
if __name__=='__main__':unittest.main()

import hashlib,json,tempfile,unittest
from pathlib import Path
import commercial_agent as agent
import delivery_status as delivery

ROW={'id':'prospect-1','company':'Entreprise exemple','to':'contact@entreprise-exemple.fr','email_status':'verified','source_url':'https://entreprise-exemple.fr/contact','verified_on':'2026-11-06','subject':'Transport professionnel','body':'Bonjour, découvrez 13 URGENT. Répondez STOP pour arrêter.'}

def dsn(mid,address,code='5.1.1',action='failed'):
 return ('From: Mail Delivery System <MAILER-DAEMON@example.invalid>\r\nMIME-Version: 1.0\r\nContent-Type: multipart/report; report-type=delivery-status; boundary="report"\r\n\r\n'
 '--report\r\nContent-Type: text/plain\r\n\r\nDelivery report\r\n'
 '--report\r\nContent-Type: message/delivery-status\r\n\r\nReporting-MTA: dns; example.invalid\r\n\r\n'
 'Final-Recipient: rfc822; '+address+'\r\nAction: '+action+'\r\nStatus: '+code+'\r\n\r\n'
 '--report\r\nContent-Type: text/rfc822-headers\r\n\r\nMessage-ID: '+mid+'\r\n\r\n--report--\r\n').encode()
class IMAP:
 def __init__(self,reports):self.reports=reports;self.readonly=None
 def login(self,u,p):pass
 def select(self,folder,readonly=False):self.readonly=readonly;return 'OK',[b'0']
 def search(self,*args):return 'OK',[b' '.join(str(i+1).encode() for i in range(len(self.reports)))]
 def fetch(self,mid,part):
  assert 'PEEK' in part
  return 'OK',[(b'data',self.reports[int(mid)-1])]
 def logout(self):pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'mail-state.json'
  self.campaign={'campaign_id':'test','send_not_before':'2026-11-09T08:30:00+01:00','recipients':[ROW]}
  mail,self.fp=agent.message(ROW,'test');self.mid=mail['Message-ID']
  self.path.write_text(json.dumps({'schema_version':1,'campaigns':{'test':{'prospect-1':{'fingerprint':self.fp,'status':'accepted_and_archived','archived_in_sent':True}}},'suppressed':[]}))
 def check(self,reports,reported=None):
  client=IMAP(reports);result=delivery.verify(self.campaign,self.path,'fake',lambda:None,imap_factory=lambda:client,reported_id=reported);self.assertTrue(client.readonly);return result
 def test_matches_only_campaign_id_and_failed_recipient(self):
  r=self.check([dsn(self.mid,ROW['to'])]);self.assertEqual(r['hard_bounced'],1);self.assertEqual(r['emails_sent'],0);self.assertEqual(r['accepted_and_archived'],1);self.assertEqual(r['delivery_not_confirmed'],0)
  state=json.loads(self.path.read_text());record=state['campaigns']['test']['prospect-1'];self.assertTrue(record['blocked_for_resend']);self.assertTrue(record['archived_in_sent']);self.assertNotIn(ROW['to'],self.path.read_text())
 def test_unrelated_or_copy_bounce_not_attributed_to_prospect(self):
  r=self.check([dsn('<'+'a'*64+'@13urgent.fr>',ROW['to']),dsn(self.mid,agent.COPY)]);self.assertEqual(r['hard_bounced'],0)
 def test_delayed_notice_is_not_permanent_failure(self):
  r=self.check([dsn(self.mid,ROW['to'],'4.2.2','delayed')]);self.assertEqual(r['hard_bounced'],0)
 def test_owner_report_is_recorded_without_sending(self):
  r=self.check([],reported='prospect-1');self.assertEqual(r['hard_bounced'],1);self.assertEqual(r['emails_sent'],0)
 def test_known_hard_bounce_never_resent(self):
  self.check([],reported='prospect-1')
  result=agent.run(self.campaign,self.path,True,password='fake',now=__import__('datetime').datetime(2026,11,9,12,tzinfo=__import__('datetime').timezone.utc),smtp_factory=lambda:(_ for _ in ()).throw(AssertionError('must not send')))
  self.assertEqual(result[0]['status'],'blocked_hard_bounce')
if __name__=='__main__':unittest.main()

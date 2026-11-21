import base64,hashlib,json,tempfile,unittest
from pathlib import Path
import send_owner_media as media
from test_commercial_agent import SMTP,Archive
class OwnerMediaTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.state=Path(self.tmp.name)/'state.json';self.raw=b'\x00\x00\x00\x18ftypisom'+b'FAKE VIDEO TEST ONLY'
  self.payload={'request_id':'owner-media-test','to':media.agent.SENDER,'subject':'Videos fictives','body':'Fichiers de test, pas un envoi reel.','attachments':[{'filename':n,'sha256':hashlib.sha256(self.raw).hexdigest(),'content_base64':base64.b64encode(self.raw).decode()}for n in sorted(media.FILENAMES)]}
 def validate(self,p):
  raw=json.dumps(p).encode();return media.validate_payload(raw,p['request_id'],hashlib.sha256(raw).hexdigest())
 def test_foreign_recipient_and_modified_content_are_blocked(self):
  self.assertEqual(self.validate(self.payload)['to'],media.agent.SENDER)
  with self.assertRaises(media.agent.CampaignError):self.validate({**self.payload,'to':'other@example.invalid'})
  changed=json.loads(json.dumps(self.payload));changed['attachments'][0]['sha256']='0'*64
  with self.assertRaises(media.agent.CampaignError):self.validate(changed)
 def test_filename_duplicate_and_nonvideo_content_are_rejected(self):
  for change in ('../secret.mp4','config.env',next(iter(media.FILENAMES))):
   p=json.loads(json.dumps(self.payload));p['attachments'][1]['filename']=change
   if change in media.FILENAMES:p['attachments'][0]['filename']=change
   with self.assertRaises(media.agent.CampaignError):self.validate(p)
  p=json.loads(json.dumps(self.payload));p['attachments'][0].update(content_base64=base64.b64encode(b'NOT AN MP4 FILE').decode(),sha256=hashlib.sha256(b'NOT AN MP4 FILE').hexdigest())
  with self.assertRaises(media.agent.CampaignError):self.validate(p)
 def test_exact_two_private_attachments_sent_once_and_archived(self):
  p=self.validate(self.payload);digest=hashlib.sha256(json.dumps(p).encode()).hexdigest();smtp,archive=SMTP(),Archive()
  def send():return media.sealed.deliver(p,digest,self.state,'FAKE',lambda:None,smtp_factory=lambda:smtp,archive_factory=lambda:archive,message_builder=media.build_message)
  self.assertEqual(send()['status'],'accepted_and_archived');self.assertEqual(send()['status'],'already_recorded');self.assertEqual(len(smtp.calls),1);self.assertEqual(smtp.calls[0][2],[media.agent.SENDER]);self.assertEqual(len(archive.calls),1)
  attachments=list(smtp.calls[0][0].iter_attachments());self.assertEqual({f.get_filename()for f in attachments},media.FILENAMES)
  for f in attachments:self.assertEqual(f.get_content(),self.raw);self.assertEqual(f.get_content_type(),'video/mp4')
  self.assertNotIn('content_base64',self.state.read_text())
 def test_archive_failure_never_causes_a_duplicate_send(self):
  smtp,archive=SMTP(),Archive(fail=True)
  def send():return media.sealed.deliver(self.payload,'a'*64,self.state,'FAKE',lambda:None,smtp_factory=lambda:smtp,archive_factory=lambda:archive,message_builder=media.build_message)
  self.assertEqual(send()['status'],'accepted_archive_pending');archive.fail=False;self.assertEqual(send()['status'],'archive_reconciled_without_resend');self.assertEqual(len(smtp.calls),1)
 def test_unknown_fields_and_oversize_are_rejected(self):
  with self.assertRaises(media.agent.CampaignError):self.validate({**self.payload,'public_url':'https://example.invalid'})
  from unittest.mock import patch
  with patch.object(media,'MAX_FILES_BYTES',1):
   with self.assertRaises(media.agent.CampaignError):self.validate(self.payload)
if __name__=='__main__':unittest.main()

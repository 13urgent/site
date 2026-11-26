import unittest,copy,hashlib,io
from unittest.mock import patch
import commercial_agent as a
from test_commercial_agent import ROW
class AttachmentTests(unittest.TestCase):
 def tearDown(self):a.verified_pdf.cache_clear()
 def response(self,raw,url):
  r=io.BytesIO(raw);r.url=url;return r
 def test_pdf_is_attached_and_part_of_message_identity(self):
  row={**ROW,'pdf_attachment':'urgent'};raw=b'%PDF-1.4\nFAKE FIXTURE';digest=hashlib.sha256(raw).hexdigest()
  with patch.object(a,'verified_pdf',return_value=(raw,'presentation.pdf',digest)):
   m,fp=a.message(row,'test');self.assertEqual(list(m.iter_attachments())[0].get_payload(decode=True),raw);self.assertIn('STOP',m.get_body(('plain',)).get_content());self.assertNotEqual(fp,a.message(ROW,'test')[1])
 def test_unknown_attachment_cannot_fetch_arbitrary_url(self):
  with patch.object(a,'urlopen') as fetch:
   with self.assertRaisesRegex(a.CampaignError,'attachment_not_authorized'):a.verified_pdf('https://external.example/private')
   fetch.assert_not_called()
 def test_wrong_hash_or_redirect_fails_before_any_message(self):
  url=a.PDF_ATTACHMENTS['urgent'][0]
  with patch.object(a,'urlopen',return_value=self.response(b'%PDF-1.4 WRONG',url)):
   with self.assertRaisesRegex(a.CampaignError,'attachment_integrity_failed'):a.verified_pdf('urgent')
  with patch.object(a,'urlopen',return_value=self.response(b'%PDF-1.4','https://elsewhere.test')):
   with self.assertRaisesRegex(a.CampaignError,'attachment_redirect_not_authorized'):a.verified_pdf('urgent')

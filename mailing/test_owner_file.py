import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import send_owner_file as owner
from test_commercial_agent import SMTP,Archive


class OwnerFileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.state=Path(self.temp.name)/'state.json'
        file=io.BytesIO()
        with zipfile.ZipFile(file,'w') as z:z.writestr('chronoss-ecmr/README.md','Fichier fictif de test')
        self.file=file.getvalue()
        self.payload={'request_id':'owner-file-test','to':owner.agent.SENDER,'subject':'Pilote de test','body':'Livraison de test explicite.','attachment':{'filename':owner.FILENAME,'sha256':hashlib.sha256(self.file).hexdigest(),'content_base64':base64.b64encode(self.file).decode()}}

    def validate(self,payload):
        raw=json.dumps(payload).encode();return owner.validate_payload(raw,payload['request_id'],hashlib.sha256(raw).hexdigest())

    def test_only_owner_and_intact_zip_are_accepted(self):
        self.assertEqual(self.validate(self.payload)['to'],owner.agent.SENDER)
        with self.assertRaises(owner.agent.CampaignError):self.validate({**self.payload,'to':'other@example.net'})
        changed={**self.payload,'attachment':{**self.payload['attachment'],'sha256':'0'*64}}
        with self.assertRaises(owner.agent.CampaignError):self.validate(changed)

    def test_private_files_and_path_traversal_are_rejected(self):
        for name in ('../escape.py','chronoss-ecmr/private-data/seal.key'):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:z.writestr(name,'TEST')
            data=b.getvalue();p={**self.payload,'attachment':{**self.payload['attachment'],'content_base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}
            with self.assertRaises(owner.agent.CampaignError):self.validate(p)

    def test_exact_attachment_sent_once_to_owner_and_archived(self):
        payload=self.validate(self.payload);digest=hashlib.sha256(json.dumps(payload).encode()).hexdigest();smtp,archive=SMTP(),Archive()
        def send():return owner.sealed.deliver(payload,digest,self.state,'test',lambda:None,smtp_factory=lambda:smtp,archive_factory=lambda:archive,message_builder=owner.build_message)
        self.assertEqual(send()['status'],'accepted_and_archived');self.assertEqual(send()['status'],'already_recorded')
        self.assertEqual(len(smtp.calls),1);self.assertEqual(smtp.calls[0][2],[owner.agent.SENDER]);self.assertEqual(len(archive.calls),1)
        self.assertEqual(list(smtp.calls[0][0].iter_attachments())[0].get_content(),self.file)
        self.assertNotIn('content_base64',self.state.read_text());self.assertNotIn(owner.agent.SENDER,self.state.read_text())

    def test_archive_failure_repairs_copy_without_second_send(self):
        smtp,archive=SMTP(),Archive(fail=True)
        def send():return owner.sealed.deliver(self.payload,'a'*64,self.state,'test',lambda:None,smtp_factory=lambda:smtp,archive_factory=lambda:archive,message_builder=owner.build_message)
        self.assertEqual(send()['status'],'accepted_archive_pending');archive.fail=False
        self.assertEqual(send()['status'],'archive_reconciled_without_resend');self.assertEqual(len(smtp.calls),1)

    def test_changed_payload_is_rejected_before_any_send(self):
        raw=json.dumps(self.payload).encode()
        with self.assertRaises(owner.agent.CampaignError):owner.validate_payload(raw,self.payload['request_id'],'0'*64)

    def test_planning_archive_keeps_its_distinct_filename(self):
        payload={**self.payload,'attachment':{**self.payload['attachment'],'filename':'CHRONOSS-PLANNING-V5.zip'}}
        checked=self.validate(payload)
        message=owner.build_message(checked,'a'*64,'Fri, 13 Nov 2026 10:00:00 +0000')
        attachment=list(message.iter_attachments())[0]
        self.assertEqual(attachment.get_filename(),'CHRONOSS-PLANNING-V5.zip')
        self.assertEqual(attachment.get_content(),self.file)

    def test_other_attachment_names_remain_rejected(self):
        for name in ('another.zip','../CHRONOSS-PLANNING-V5.zip',['CHRONOSS-PLANNING-V5.zip']):
            payload={**self.payload,'attachment':{**self.payload['attachment'],'filename':name}}
            with self.assertRaises(owner.agent.CampaignError):self.validate(payload)


if __name__=='__main__':unittest.main()

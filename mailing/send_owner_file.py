#!/usr/bin/env python3
"""Mail an explicitly requested ZIP only to the owner, through a sealed request."""
import argparse
import base64
import binascii
from email import policy
from email.message import EmailMessage
import hashlib
import io
import json
import os
import re
from pathlib import PurePosixPath
import zipfile
import commercial_agent as agent
import run_campaign
import send_service_reply as sealed

MAX_RAW=3_000_000
MAX_ZIP=2_000_000
FILENAME='CHRONOSS-ECMR-pilote-Windows.zip'
ALLOWED_FILENAMES={FILENAME,'CHRONOSS-PLANNING-V5.zip'}


def validate_payload(raw,request_id,digest):
    if len(raw)>MAX_RAW or hashlib.sha256(raw).hexdigest()!=digest:raise agent.CampaignError('owner_file_digest_mismatch')
    try:value=json.loads(raw)
    except (ValueError,UnicodeError):raise agent.CampaignError('owner_file_payload_invalid') from None
    if not isinstance(value,dict) or set(value)!={'request_id','to','subject','body','attachment'}:raise agent.CampaignError('owner_file_fields_invalid')
    base={key:value[key] for key in ('request_id','to','subject','body')}
    canonical=json.dumps(base).encode();sealed.validate_payload(canonical,request_id,hashlib.sha256(canonical).hexdigest())
    if value['to']!=agent.SENDER:raise agent.CampaignError('owner_file_recipient_not_owner')
    file=value['attachment']
    if not isinstance(file,dict) or set(file)!={'filename','sha256','content_base64'} or not isinstance(file['filename'],str) or file['filename'] not in ALLOWED_FILENAMES:raise agent.CampaignError('owner_file_attachment_invalid')
    try:
        data=base64.b64decode(file['content_base64'],validate=True)
    except (ValueError,TypeError,binascii.Error):raise agent.CampaignError('owner_file_attachment_invalid') from None
    if not data or len(data)>MAX_ZIP or hashlib.sha256(data).hexdigest()!=file['sha256']:raise agent.CampaignError('owner_file_attachment_mismatch')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if len(z.infolist())>200 or sum(x.file_size for x in z.infolist())>20_000_000:raise ValueError()
            for item in z.infolist():
                path=PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in item.filename:raise ValueError()
                if any(piece in item.filename for piece in ('private-data/','.sqlite','seal.key','push.key','.env','test-access.json')):raise ValueError()
            if z.testzip() is not None:raise ValueError()
    except (ValueError,zipfile.BadZipFile,RuntimeError):raise agent.CampaignError('owner_file_archive_invalid') from None
    return value


def build_message(payload,digest,date):
    mail=EmailMessage(policy=policy.SMTP)
    mail['From']='CHRONOSS <'+agent.SENDER+'>';mail['To']=agent.SENDER
    mail['Reply-To']=agent.SENDER;mail['Subject']=payload['subject'];mail['Date']=date;mail['Message-ID']='<'+digest+'@13urgent.fr>'
    mail.set_content(payload['body'])
    mail.add_attachment(base64.b64decode(payload['attachment']['content_base64']),maintype='application',subtype='zip',filename=payload['attachment']['filename'])
    return mail


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','send']);args=parser.parse_args()
    request_id,digest,directory=sealed.settings()
    if args.mode=='prepare':sealed.prepare(directory);print(json.dumps({'status':'owner_file_public_certificate_ready'}));return 0
    try:
        raw=sealed.fetch_payload(request_id,directory,max_sealed_bytes=MAX_RAW+10000)
        payload=validate_payload(raw,request_id,digest)
        _,state_dir=run_campaign.pipeline.setup_runtime()
        result=sealed.deliver(payload,digest,state_dir/'mail-state.json',os.environ.get('CONTACT_MAIL_PASSWORD'),lambda:run_campaign.checkpoint(state_dir),message_builder=build_message)
        print(json.dumps(result))
        return 0 if result['status'] in ('accepted_and_archived','already_recorded','archive_reconciled_without_resend') else 2
    finally:
        for name in ('private.key','request.cms'):(directory/name).unlink(missing_ok=True)


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        code=str(error) if isinstance(error,agent.CampaignError) and re.fullmatch('[a-z0-9_]+',str(error)) else 'owner_file_delivery_failed'
        print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

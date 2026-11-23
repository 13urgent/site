#!/usr/bin/env python3
"""Private, sealed delivery of the two owner-requested narration-only videos.

Only the configured owner can receive them. No media is uploaded to a public
website. Reuses the existing durable send ledger and independent Sent archive.
"""
import argparse,base64,binascii,hashlib,json,os,re,io,zipfile
from email import policy
from email.message import EmailMessage
import commercial_agent as agent
import run_campaign
import send_service_reply as sealed
MAX_RAW=10_000_000
MAX_FILES_BYTES=7_000_000
MAX_MIME_BYTES=9_500_000
FILENAMES={'13URGENT-VOIX-OFF-SEULE.mp4','MON-EXPLOIT-VOIX-OFF-SEULE.mp4'}
DOCUMENT_FILENAMES={'Kling-complet.zip','Guide-Kling.pdf'}
MIME={'Kling-complet.zip':('application','zip'),'Guide-Kling.pdf':('application','pdf')}

def validate_payload(raw,request_id,digest):
 if len(raw)>MAX_RAW or hashlib.sha256(raw).hexdigest()!=digest:raise agent.CampaignError('owner_media_digest_mismatch')
 try:value=json.loads(raw)
 except (ValueError,UnicodeError):raise agent.CampaignError('owner_media_invalid')from None
 if not isinstance(value,dict)or set(value)!={'request_id','to','subject','body','attachments'}:raise agent.CampaignError('owner_media_fields_invalid')
 base={k:value[k]for k in ('request_id','to','subject','body')};data=json.dumps(base).encode();sealed.validate_payload(data,request_id,hashlib.sha256(data).hexdigest())
 if value['to']!=agent.SENDER or agent.COPY!=agent.SENDER:raise agent.CampaignError('owner_media_recipient_not_owner')
 files=value['attachments']
 if not isinstance(files,list)or len(files)!=2:raise agent.CampaignError('owner_media_files_invalid')
 names=set();total=0
 for file in files:
  if not isinstance(file,dict)or set(file)!={'filename','sha256','content_base64'}:raise agent.CampaignError('owner_media_file_invalid')
  name=file['filename']
  if not isinstance(name,str)or name not in FILENAMES|DOCUMENT_FILENAMES or name in names:raise agent.CampaignError('owner_media_filename_invalid')
  names.add(name)
  try:content=base64.b64decode(file['content_base64'],validate=True)
  except (ValueError,TypeError,binascii.Error):raise agent.CampaignError('owner_media_file_invalid')from None
  if hashlib.sha256(content).hexdigest()!=file['sha256']:raise agent.CampaignError('owner_media_content_mismatch')
  if name in FILENAMES and (len(content)<12 or content[4:8]!=b'ftyp'):raise agent.CampaignError('owner_media_content_mismatch')
  if name=='Guide-Kling.pdf' and not content.startswith(b'%PDF-'):raise agent.CampaignError('owner_media_content_mismatch')
  if name=='Kling-complet.zip':
   if not zipfile.is_zipfile(io.BytesIO(content)):raise agent.CampaignError('owner_media_content_mismatch')
   with zipfile.ZipFile(io.BytesIO(content)) as archive:
    if any(n.startswith('/') or '..' in n.split('/') for n in archive.namelist()):raise agent.CampaignError('owner_media_content_mismatch')
  total+=len(content)
 if names not in (FILENAMES,DOCUMENT_FILENAMES):raise agent.CampaignError('owner_media_files_invalid')
 if total>MAX_FILES_BYTES:raise agent.CampaignError('owner_media_too_large')
 return value

def build_message(payload,digest,date):
 mail=EmailMessage(policy=policy.SMTP);mail['From']='CHRONOSS <'+agent.SENDER+'>';mail['To']=agent.SENDER;mail['Reply-To']=agent.SENDER;mail['Subject']=payload['subject'];mail['Date']=date;mail['Message-ID']='<'+digest+'@13urgent.fr>';mail.set_content(payload['body'])
 for file in payload['attachments']:
  maintype,subtype=MIME.get(file['filename'],('video','mp4'));mail.add_attachment(base64.b64decode(file['content_base64']),maintype=maintype,subtype=subtype,filename=file['filename'])
 if len(mail.as_bytes())>MAX_MIME_BYTES:raise agent.CampaignError('owner_media_mime_too_large')
 return mail

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','send']);args=parser.parse_args();request_id,digest,directory=sealed.settings()
 if args.mode=='prepare':sealed.prepare(directory);print(json.dumps({'status':'owner_media_public_certificate_ready'}));return 0
 try:
  raw=sealed.fetch_payload(request_id,directory,max_sealed_bytes=MAX_RAW+10000);payload=validate_payload(raw,request_id,digest)
  _,state=run_campaign.pipeline.setup_runtime()
  result=sealed.deliver(payload,digest,state/'mail-state.json',os.environ.get('CONTACT_MAIL_PASSWORD'),lambda:run_campaign.checkpoint(state),message_builder=build_message)
  print(json.dumps(result));return 0 if result['status']in('accepted_and_archived','already_recorded','archive_reconciled_without_resend')else 2
 finally:
  for name in ('private.key','request.cms'):(directory/name).unlink(missing_ok=True)
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as error:
  code=str(error)if isinstance(error,agent.CampaignError)and re.fullmatch('[a-z0-9_]+',str(error))else'owner_media_delivery_failed'
  print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

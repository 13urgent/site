#!/usr/bin/env python3
"""Private targeted email campaign with durable dedup and IMAP Sent copies."""
from __future__ import annotations
import argparse,base64,hashlib,imaplib,json,os,re,smtplib,ssl,tempfile,time,unicodedata
from datetime import datetime,timezone
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime,parseaddr
from pathlib import Path

SENDER='contact@13urgent.fr'
COPY='contact@13urgent.fr'
BLOCKED_ROLES={'dpo','rgpd','privacy','rh','recrutement','sav','webmaster','abuse','postmaster','noreply','no-reply'}
class CampaignError(Exception):pass

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def recipient(row):
    value=row.get('to')
    if row.get('email_status')!='verified' or not isinstance(value,str):return None
    if '\r' in value or '\n' in value or parseaddr(value)[1]!=value:return None
    if not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',value):return None
    local,domain=value.lower().rsplit('@',1)
    if domain in ('13urgent.fr','chronoss.fr') or local in BLOCKED_ROLES:return None
    if not isinstance(row.get('source_url'),str) or not row['source_url'].startswith('https://') or not row.get('verified_on'):return None
    return value

def message(row,campaign_id,message_date=None):
    address=recipient(row)
    if not address:raise CampaignError('recipient_not_verified')
    subject=row.get('subject');body=row.get('body')
    if not isinstance(subject,str) or not subject.strip() or '\r' in subject or '\n' in subject:raise CampaignError('subject_invalid')
    if not isinstance(body,str) or not body.strip():raise CampaignError('body_invalid')
    if 'STOP' not in body:body+='\n\nSi vous ne souhaitez plus recevoir nos messages, répondez STOP.'
    m=EmailMessage(policy=policy.SMTP);m['From']='13 URGENT — Équipe commerciale <'+SENDER+'>';m['To']=address;m['Cc']=COPY;m['Reply-To']=SENDER
    m['Subject']=subject;m['Date']=message_date or format_datetime(datetime.now(timezone.utc))
    digest=hashlib.sha256((campaign_id+'\n'+SENDER+'\n'+address.lower()+'\n'+subject+'\n'+body).encode()).hexdigest()
    m['Message-ID']='<'+digest+'@13urgent.fr>';m['List-Unsubscribe']='<mailto:'+SENDER+'?subject=STOP>'
    m.set_content(body)
    return m,digest

def mailbox_rows(rows):
    result=[]
    for row in rows or []:
        literal=None
        if isinstance(row,tuple) and len(row)==2:row,literal=row
        if not isinstance(row,bytes):continue
        match=re.fullmatch(rb'\(([^)]*)\)\s+(?:"([^"\r\n]*)"|NIL)\s+(.*)',row)
        if not match:continue
        flags,delimiter,raw=match.groups()
        if literal is not None:raw=literal
        elif raw.startswith(b'"') and raw.endswith(b'"'):raw=raw[1:-1].replace(b'\\"',b'"').replace(b'\\\\',b'\\')
        try:name=raw.decode('ascii')
        except (UnicodeDecodeError,AttributeError):continue
        if any(c in name for c in '\r\n'):continue
        result.append((flags.lower().split(),delimiter.decode('ascii') if delimiter else None,name))
    return result

def mailbox_label(name):
    def utf7(match):
        value=match.group(1)
        if not value:return '&'
        try:return base64.b64decode(value.replace(',','/')+'='*((-len(value))%4)).decode('utf-16-be')
        except (ValueError,UnicodeError):return match.group(0)
    name=re.sub(r'&([^-]*)-',utf7,name)
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c)).casefold().split())

class SentArchive:
    def __init__(self,password,imap_factory=None):
        self.client=imap_factory() if imap_factory else imaplib.IMAP4_SSL('ssl0.ovh.net',993,ssl_context=ssl.create_default_context(),timeout=30)
        try:
            self.client.login(SENDER,password)
            status,rows=self.client.list()
            if status!='OK':raise CampaignError('sent_folder_list_failed')
            special=[];known=[]
            for flags,delimiter,name in mailbox_rows(rows):
                if b'\\noselect' in flags:continue
                label=mailbox_label(name)
                for prefix in ('inbox.','inbox/'):
                    if label.startswith(prefix):label=label[len(prefix):];break
                if b'\\sent' in flags:special.append(name)
                if label in ('sent','sent items','sent messages','envoye','envoyes','messages envoyes','elements envoyes'):known.append(name)
            candidates=list(dict.fromkeys(special or known))
            # Match Roundcube's visible subscribed folder when old clients left
            # multiple conventional Sent folders. No personal labels are logged.
            if len(candidates)>1 and hasattr(self.client,'lsub'):
                status,subscribed=self.client.lsub()
                if status=='OK':
                    names={name for _,_,name in mailbox_rows(subscribed)}
                    visible=[name for name in candidates if name in names]
                    if len(visible)==1:candidates=visible
            if not candidates:raise CampaignError('sent_folder_not_found')
            if len(candidates)!=1:raise CampaignError('sent_folder_ambiguous')
            self.folder='"'+candidates[0].replace('\\','\\\\').replace('"','\\"')+'"'
            status,_=self.client.select(self.folder)
            if status!='OK':raise CampaignError('sent_folder_not_accessible')
        except Exception:
            try:self.client.logout()
            except Exception:pass
            raise
    def contains(self,message_id):
        if not re.fullmatch(r'<[0-9a-f]{64}@13urgent\.fr>',message_id):raise CampaignError('message_id_invalid')
        status,rows=self.client.uid('SEARCH',None,'HEADER','Message-ID','"'+message_id+'"')
        if status!='OK':raise CampaignError('sent_search_failed')
        return any(row.strip() for row in rows or [] if isinstance(row,bytes))
    def append(self,mail):
        if self.contains(mail['Message-ID']):return
        status,_=self.client.append(self.folder,'(\\Seen)',imaplib.Time2Internaldate(time.time()),mail.as_bytes())
        if status!='OK':raise CampaignError('sent_archive_failed')
    def close(self):
        try:self.client.logout()
        except Exception:pass

def campaign_rows(campaign):
    rows=campaign.get('recipients')
    if not isinstance(rows,list) or len(rows)>30:raise CampaignError('campaign_scope_invalid')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',campaign.get('campaign_id','')):raise CampaignError('campaign_id_invalid')
    ids=[x.get('id') for x in rows]
    if any(not isinstance(x,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',x) for x in ids) or len(set(ids))!=len(ids):raise CampaignError('recipient_id_invalid')
    return rows

def run(campaign,state_path,execute=False,smtp_factory=None,password=None,now=None,wait=time.sleep,archive_factory=None,checkpoint=None):
    rows=campaign_rows(campaign);state_path=Path(state_path)
    state=json.loads(state_path.read_text()) if state_path.exists() else {'schema_version':1,'campaigns':{},'suppressed':[]}
    if state.get('schema_version')!=1:raise CampaignError('state_schema')
    cid=campaign['campaign_id'];records=state['campaigns'].setdefault(cid,{})
    not_before=datetime.fromisoformat(campaign['send_not_before'].replace('Z','+00:00'))
    if not_before.utcoffset() is None:raise CampaignError('timezone_required')
    if execute and (now or datetime.now(timezone.utc))<not_before:raise CampaignError('before_campaign_date')
    if execute and not password:raise CampaignError('mail_access_not_connected')
    results=[];seen=set();connection=None;archive=None
    def persist():
        save(state_path,state)
        if checkpoint:checkpoint()
    def get_archive():
        nonlocal archive
        if archive is None:archive=archive_factory() if archive_factory else SentArchive(password)
        return archive
    try:
        for row in rows:
            address=recipient(row)
            if not address:results.append({'id':row['id'],'status':'held_missing_verified_address'});continue
            normalized=address.lower()
            if normalized in seen:results.append({'id':row['id'],'status':'held_duplicate_address'});continue
            seen.add(normalized)
            if normalized in {v.lower() for v in state.get('suppressed',[])}:results.append({'id':row['id'],'status':'suppressed'});continue
            previous=records.get(row['id']);mail,fingerprint=message(row,cid,previous.get('message_date') if previous else None)
            if previous:
                if previous.get('fingerprint')!=fingerprint:results.append({'id':row['id'],'status':'content_conflict'});continue
                if execute and previous.get('status')=='accepted_archive_pending':
                    try:get_archive().append(mail);previous['status']='accepted_and_archived';persist()
                    except Exception:results.append({'id':row['id'],'status':'accepted_archive_pending'});break
                    results.append({'id':row['id'],'status':'archive_repaired_without_resend'});continue
                if execute and previous.get('status')=='intent':
                    if get_archive().contains(mail['Message-ID']):
                        previous['status']='accepted_and_archived';persist();results.append({'id':row['id'],'status':'reconciled_from_sent_without_resend'});continue
                results.append({'id':row['id'],'status':'already_recorded','recorded_status':previous.get('status')});continue
            if not execute:results.append({'id':row['id'],'status':'ready_preview','message':mail.as_string()});continue
            # Require a usable Sent folder BEFORE sending to any prospect.
            get_archive()
            if connection is None:
                connection=smtp_factory() if smtp_factory else smtplib.SMTP_SSL('ssl0.ovh.net',465,timeout=30,context=ssl.create_default_context())
                connection.login(SENDER,password)
            record={'status':'intent','fingerprint':fingerprint,'message_date':str(mail['Date']),'created_at':datetime.now(timezone.utc).isoformat()}
            records[row['id']]=record;persist()
            try:
                refused=connection.send_message(mail,from_addr=SENDER,to_addrs=[address,COPY])
            except Exception:
                record['status']='uncertain_do_not_retry';persist();results.append({'id':row['id'],'status':record['status']});break
            record['status']='partial_acceptance' if refused else 'accepted_archive_pending'
            try:get_archive().append(mail);record['archived_in_sent']=True
            except Exception:record['archived_in_sent']=False
            if not refused and record['archived_in_sent']:record['status']='accepted_and_archived'
            record['updated_at']=datetime.now(timezone.utc).isoformat();persist();results.append({'id':row['id'],'status':record['status']})
            if record['status']!='accepted_and_archived':break
            wait(2)
    finally:
        if connection:
            try:connection.quit()
            except Exception:pass
        if archive:archive.close()
    return results

def probe(password):
    if not password:raise CampaignError('mail_access_not_connected')
    archive=SentArchive(password)
    try:
        smtp=smtplib.SMTP_SSL('ssl0.ovh.net',465,timeout=30,context=ssl.create_default_context())
        try:smtp.login(SENDER,password)
        finally:
            try:smtp.quit()
            except Exception:pass
    finally:archive.close()
    return {'connection_ok':True,'sent_folder_accessible':True,'emails_sent':0}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--preview-dir',type=Path)
    args=parser.parse_args();campaign=json.loads(args.campaign.read_text())
    result=run(campaign,args.state,execute=args.execute,password=os.environ.get('CONTACT_MAIL_PASSWORD'))
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True,exist_ok=True)
        for row in result:
            if row.get('message'):(args.preview_dir/(row['id']+'.eml')).write_text(row['message'])
    counts={}
    for row in result:counts[row['status']]=counts.get(row['status'],0)+1
    print(json.dumps({'execute':args.execute,'counts':counts,'delivery_to_recipient_not_verified':True}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        code=str(e) if isinstance(e,CampaignError) else 'campaign_failed'
        print(json.dumps({'ok':False,'error':code}));raise SystemExit(2)

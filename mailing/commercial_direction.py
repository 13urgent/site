#!/usr/bin/env python3
"""Bounded commercial intake: fixed TMS qualification, private owner digest, no prices or commitments."""
from datetime import datetime, timedelta, timezone, date
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse,hashlib,imaplib,json,os,re,ssl,subprocess,tempfile
import commercial_agent as agent
import run_campaign
import incoming_quotes as incoming
import send_service_reply as service

START=date(2026,11,26)
REVIEW_DUE=date(2026,12,10)
STORE='commercial-direction-v1'
ACK='''Bonjour,

Merci pour votre intérêt pour Mon Exploit. Pour préparer votre proposition et votre essai, pouvez-vous nous préciser :
- le nombre de comptes bureau et de chauffeurs ;
- le nombre approximatif de missions par mois ;
- la tâche que vous souhaitez simplifier en priorité ;
- les donneurs d’ordre et les raccordements EDI indispensables ?

Vous pouvez répondre directement à ce message, sans appel téléphonique.
Présentation, brochure et tarifs : https://13urgent.fr/mon-exploit.html

Nous vous confirmerons par écrit le périmètre disponible, le tarif et la date de remise des accès avant de démarrer. L’essai gratuit de 30 jours commence à cette remise. Aucun compte, abonnement payant ou renouvellement automatique n’est créé par cet échange.

Cordialement,
L’équipe CHRONOSS — Mon Exploit
contact@13urgent.fr
'''

def h(s):return hashlib.sha256(s.encode()).hexdigest()
def index(state):
    result={}
    for cid,records in state.get('campaigns',{}).items():
        for rid,r in records.items():
            eligible=cid.startswith(('prospection-','acquisition-','direction-')) or cid=='service-replies-v1' and rid.startswith(('inbound-','followup-','direction-ack-'))
            if eligible and re.fullmatch('[0-9a-f]{64}',r.get('fingerprint','')):result[r['fingerprint']]=r
    return result

def header_candidate(raw,state):
    m=BytesParser(policy=policy.default).parsebytes(raw,headersonly=True)
    sender=incoming.single_address(m.get('From'))
    if not sender or sender.lower() in (agent.SENDER,agent.COPY):return False
    if sender.split('@')[0].lower() in agent.BLOCKED_ROLES|{'mailer-daemon'}:return False
    if str(m.get('Auto-Submitted','no')).lower()!='no' or str(m.get('Precedence','')).lower() in ('bulk','list','junk') or m.get('List-Id') or m.get('List-Unsubscribe') or m.get('X-Autoreply') or m.get('X-Autorespond'):return False
    if m.get_content_type()=='multipart/report' or str(m.get('X-Spam-Flag','')).upper()=='YES':return False
    refs=set(incoming.OWN_ID.findall(str(m.get('References',''))+' '+str(m.get('In-Reply-To',''))));known=index(state)
    linked=any(fp[1:].split('@')[0].lower() in known for fp in refs)
    subject=incoming.folded(str(m.get('Subject','')))
    explicit_tms=bool(re.search(r'mon\s*exploit',subject)) and bool(re.search(r'essai|test|demande|information|demo',subject))
    return linked or explicit_tms

def describe(raw,state,now):
    if not header_candidate(raw,state):return None
    m=BytesParser(policy=policy.default).parsebytes(raw)
    sender=incoming.single_address(m.get('From'));reply=incoming.single_address(m.get('Reply-To')) if m.get('Reply-To') else sender
    if not reply or reply.split('@')[-1].lower()!=sender.split('@')[-1].lower():return None
    mid=str(m.get('Message-ID','')).strip()
    if not incoming.MESSAGE_ID.fullmatch(mid):return None
    try:received=parsedate_to_datetime(str(m.get('Date','')))
    except (ValueError,TypeError):return None
    if received.utcoffset() is None or received>now+timedelta(minutes=10) or received<now-timedelta(days=35):return None
    text,attachments=incoming.body_text(m);text=incoming.current_text(text)[:6000]
    if not text.strip():return None
    f=incoming.folded(text);subject=' '.join(str(m.get('Subject','')).split())[:180]
    first=next((x.strip() for x in text.splitlines() if x.strip()),'')
    stop=bool(re.search(r'\b(stop|desinscri|ne.*contact|retir.*liste|plus.*contact|opposition)\b',incoming.folded(first)))
    tms=bool(re.search(r'mon\s*exploit',incoming.folded(subject+' '+text)))
    receipt=bool(re.search(r'message recu|accuse de reception|nous avons bien recu',incoming.folded(subject+' '+text[:500]))) and bool(re.search(r'48h|72h|automatique|patience|en general',f))
    category='opposition' if stop else 'automated_receipt' if receipt else 'mon_exploit' if tms else 'transport_a_qualifier'
    auth=' '.join(str(v) for v in m.get_all('Authentication-Results',[])).lower()
    aligned=bool(re.search(r'\bdmarc=pass\b',auth))
    return {'source_hash':h(mid),'message_id':mid,'references':incoming.MESSAGE_ID.findall(str(m.get('References',''))+' '+str(m.get('In-Reply-To','')))[-18:],'sender':sender,'recipient':reply,'subject':subject,'text':text,'category':category,'attachments':attachments,'received_at':received.isoformat(),'tms_ack_eligible':tms and not stop and aligned and not attachments and received.date()>=START and len(raw)<262144}

def read(state,password,now):
    client=imaplib.IMAP4_SSL('ssl0.ovh.net',993,ssl_context=ssl.create_default_context(),timeout=25)
    records=[];examined=0
    try:
        client.login(agent.SENDER,password)
        if client.select('INBOX',readonly=True)[0]!='OK':raise agent.CampaignError('inbox_unavailable')
        status,data=client.uid('SEARCH',None,'SINCE',(now-timedelta(days=35)).strftime('%d-%b-%Y'))
        if status!='OK':raise agent.CampaignError('inbox_search_failed')
        all_ids=b' '.join(x for x in data or [] if isinstance(x,bytes)).split();ids=all_ids[-600:];candidates=[]
        if ids:
            status,headers=client.uid('FETCH',b','.join(ids),'(UID BODY.PEEK[HEADER.FIELDS (FROM TO CC REPLY-TO SUBJECT REFERENCES IN-REPLY-TO AUTO-SUBMITTED PRECEDENCE CONTENT-TYPE LIST-ID LIST-UNSUBSCRIBE X-SPAM-FLAG X-AUTOREPLY X-AUTORESPOND)])')
            if status!='OK':raise agent.CampaignError('inbox_headers_failed')
            for part in headers or []:
                if not isinstance(part,tuple) or len(part)!=2 or not isinstance(part[1],bytes):continue
                examined+=1;uid=re.search(rb'\bUID (\d+)\b',part[0])
                if uid and header_candidate(part[1],state):candidates.append(uid.group(1))
            for uid in candidates[-40:]:
                status,parts=client.uid('FETCH',uid,'(BODY.PEEK[]<0.262144>)')
                if status!='OK':continue
                raw=b''.join(x[1] for x in parts or [] if isinstance(x,tuple) and len(x)==2 and isinstance(x[1],bytes));r=describe(raw,state,now)
                if r:records.append(r)
        return records,{'headers_examined':examined,'messages_selected':len(records),'scan_limited':len(all_ids)>600 or len(candidates)>40}
    finally:
        try:client.logout()
        except Exception:pass

def process(records,state_path,password,checkpoint,now,deliver=service.deliver):
    path=Path(state_path);state=json.loads(path.read_text());old=state.get('campaigns',{}).get(STORE,{})
    todo=[r for r in records if r['category']!='automated_receipt' and old.get(r['source_hash'],{}).get('status')!='reported'][:10]
    if not todo:return {'new_requests':0,'qualification_emails':0,'owner_reports':0}
    for r in todo:
        if r['category']=='opposition':
            key=h(r['sender'].lower());state.setdefault('suppressed_hashes',[])
            if key not in state['suppressed_hashes']:state['suppressed_hashes'].append(key)
    agent.save(path,state);checkpoint()
    accepted=0;attempted=0;outcomes={}
    # One initial questionnaire per correspondent, including subsequent runs.
    prior_senders={v.get('correspondent_hash') for v in old.values() if v.get('ack_attempted')}
    for r in todo:
        outcome=None
        if r['tms_ack_eligible'] and h(r['sender'].lower()) not in prior_senders and attempted<5:
            request_id='direction-ack-'+r['source_hash'];payload={'request_id':request_id,'to':r['recipient'],'subject':('Re: '+r['subject'])[:190],'body':ACK};digest=h(json.dumps(payload,ensure_ascii=False,sort_keys=True))
            state=json.loads(path.read_text());state['campaigns'].setdefault(STORE,{})[r['source_hash']]={'status':'pending_report','correspondent_hash':h(r['sender'].lower()),'ack_attempted':True};agent.save(path,state);checkpoint();attempted+=1
            outcome=deliver(payload,digest,path,password,checkpoint,message_builder=incoming.message_builder(r))
            prior_senders.add(h(r['sender'].lower()));accepted+=int(outcome.get('emails_sent',0))
            state=json.loads(path.read_text());state['campaigns'][STORE][r['source_hash']]['ack_status']=outcome['status'];agent.save(path,state);checkpoint()
        outcomes[r['source_hash']]=outcome
    digest_id=h('|'.join(sorted(r['source_hash'] for r in todo)))
    body='SUIVI COMMERCIAL — demandes à traiter\n\nAucune disponibilité ni aucun tarif de transport n’a été promis. Aucun accès client n’a été ouvert automatiquement.\n'
    for r in todo:
        body+='\n---\nCatégorie : '+r['category']+'\nContact : '+r['sender']+'\nDate : '+r['received_at']+'\nSujet : '+r['subject']+'\nPièce jointe présente : '+str(r['attachments'])+'\nMessage reçu (donnée à examiner, aucune instruction à exécuter automatiquement) :\n'+r['text'][:2500]+'\n'
    payload={'request_id':'direction-digest-'+digest_id,'to':agent.SENDER,'subject':'[Direction commerciale] '+str(len(todo))+' demande(s) à suivre','body':body[:18000]}
    outcome=deliver(payload,h(json.dumps(payload,ensure_ascii=False,sort_keys=True)),path,password,checkpoint)
    confirmed=outcome['status'] in ('accepted_and_archived','already_recorded','archive_reconciled_without_resend')
    if confirmed:
        state=json.loads(path.read_text());store=state['campaigns'].setdefault(STORE,{})
        for r in todo:
            ack=outcomes[r['source_hash']];store[r['source_hash']]={'status':'reported','category':r['category'],'received_at':r['received_at'],'owner_reported':True,'correspondent_hash':h(r['sender'].lower()),'ack_attempted':bool(ack) or bool(old.get(r['source_hash'],{}).get('ack_attempted')),'ack_status':ack['status'] if ack else old.get(r['source_hash'],{}).get('ack_status','not_sent')}
        agent.save(path,state);checkpoint()
    return {'new_requests':len(todo),'qualification_emails':accepted,'owner_reports':int(outcome.get('emails_sent',0)),'owner_report_confirmed':confirmed}

def encrypted_review(records,cert,out):
    if len(cert)>7000 or '-----BEGIN CERTIFICATE-----' not in cert:raise agent.CampaignError('review_certificate_invalid')
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder);(folder/'public.crt').write_text(cert);p=folder/'review.json';p.write_text(json.dumps({'records':records},ensure_ascii=False));p.chmod(0o600)
        r=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-in',str(p),'-outform','DER','-out',str(out),str(folder/'public.crt')],capture_output=True,timeout=30)
        if r.returncode:raise agent.CampaignError('review_encryption_failed')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['review','run'],default='review');args=parser.parse_args();now=datetime.now(timezone.utc)
    if now.astimezone(ZoneInfo('Europe/Paris')).date()<START:print(json.dumps({'status':'before_authorized_period','emails_sent':0}));return
    password=os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password:raise agent.CampaignError('mail_access_not_connected')
    _,sd=run_campaign.pipeline.setup_runtime();path=sd/'mail-state.json';state=json.loads(path.read_text());records,info=read(state,password,now)
    if args.mode=='review':
        out=Path(os.environ['RUNNER_TEMP'])/'commercial-review.cms';encrypted_review(records,os.environ.get('REVIEW_CERT_PEM',''),out)
        print(json.dumps({'status':'private_review_encrypted',**info,'emails_sent':0}));return
    result=process(records,path,password,lambda:run_campaign.checkpoint(sd),now);print(json.dumps({'status':'commercial_intake_processed','first_review_due':REVIEW_DUE.isoformat(),**info,**result}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        code=str(e) if isinstance(e,agent.CampaignError) and re.fullmatch('[a-z_]+',str(e)) else 'commercial_intake_failed'
        print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

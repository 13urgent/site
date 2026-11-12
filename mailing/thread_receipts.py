#!/usr/bin/env python3
"""Acknowledge fresh replies in known transport threads and alert the owner privately."""
import argparse
from datetime import datetime,timedelta,timezone
from email import policy
from email.message import EmailMessage
import hashlib
import imaplib
import json
import os
from pathlib import Path
import re
import ssl
import incoming_quotes as incoming
import commercial_agent as agent
import run_campaign


def latest_replies(messages,state,sender_hash,now):
    if not re.fullmatch(r'[0-9a-f]{64}',sender_hash or ''):raise agent.CampaignError('followup_sender_hash_invalid')
    latest={}
    for raw,received in messages:
        request=incoming.describe(raw,received,allow_followup=True)
        if not request or hashlib.sha256(request['sender'].lower().encode()).hexdigest()!=sender_hash:continue
        parent=incoming.parent_inquiry(request,state)
        if not parent or not request['references'] or now-request['received_at']>timedelta(days=1):continue
        if parent not in latest or request['received_at']>latest[parent]['received_at']:latest[parent]={**request,'parent_kind':parent}
    return list(latest.values())


def owner_notice(client,request):
    if client.select('INBOX')[0]!='OK':return False
    key='owner-followup-'+request['source_hash']
    code,rows=client.uid('SEARCH',None,'HEADER','X-13URGENT-Alert-ID','"'+key+'"')
    if code!='OK':return False
    if any(x.strip() for x in rows or [] if isinstance(x,bytes)):return True
    mail=EmailMessage(policy=policy.SMTP);mail['From']=agent.SENDER;mail['To']=agent.SENDER
    mail['Subject']='[13URGENT — CLIENT À TRAITER] '+request['subject'];mail['X-13URGENT-Alert-ID']=key
    mail['Message-ID']='<'+hashlib.sha256(key.encode()).hexdigest()+'@13urgent.fr>';mail['Auto-Submitted']='auto-generated'
    mail.set_content('Réponse client reçue le '+request['received_at'].isoformat()+'\nCorrespondant : '+request['sender']+'\n\nAction : prendre connaissance des précisions et préparer la proposition de transport.\n\nTexte reçu :\n'+request['text'])
    return client.append('INBOX',None,imaplib.Time2Internaldate(__import__('time').time()),mail.as_bytes())[0]=='OK'


def process(requests,state_path,password,checkpoint,client,deliver=incoming.service.deliver):
    results=[]
    for request in requests:
        if not owner_notice(client,request):results.append({'status':'owner_alert_failed','emails_sent':0});continue
        if not incoming.private_task(client,request,'REPONSE_CLIENT_A_TRAITER'):results.append({'status':'private_task_failed','emails_sent':0});continue
        payload=incoming.payload_for(request);payload['request_id']='receipt-'+request['source_hash']
        payload['body']='Bonjour,\n\nMerci pour votre retour. Nous avons bien reçu vos précisions et les avons transmises à l’exploitation pour préparer notre proposition de transport.\n\nLe tarif et la disponibilité seront précisés dans notre offre.\n\nCordialement,\nL’équipe CHRONOSS — 13 URGENT\ncontact@13urgent.fr'
        digest=hashlib.sha256(json.dumps({'payload':payload,'parent':request['message_id']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result=deliver(payload,digest,state_path,password,checkpoint,message_builder=incoming.message_builder(request))
        incoming.note(state_path,request,result['status'],checkpoint,True)
        results.append({**result,'parent_kind':request['parent_kind'],'owner_notice_saved':True})
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['probe','send'],default='probe');args=parser.parse_args()
    password=os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password:raise agent.CampaignError('mail_access_not_connected')
    client=imaplib.IMAP4_SSL('ssl0.ovh.net',993,ssl_context=ssl.create_default_context(),timeout=30)
    try:
        client.login(agent.SENDER,password);now=datetime.now(timezone.utc)
        messages,limited=incoming.read_messages(client,'probe_followup',now)
        _,state_dir=run_campaign.pipeline.setup_runtime();path=state_dir/'mail-state.json'
        requests=latest_replies(messages,json.loads(path.read_text()),os.environ.get('TARGET_SENDER_SHA256',''),now)
        if args.mode=='probe':print(json.dumps({'requests_found':len(requests),'received_at':[r['received_at'].isoformat() for r in requests],'parent_kinds':[r['parent_kind'] for r in requests],'emails_sent':0}));return 0
        results=process(requests,path,password,lambda:run_campaign.checkpoint(state_dir),client)
        print(json.dumps({'status':'client_receipts_processed','results':results,'scan_limited':limited,'price_or_booking_confirmed':False}))
        return 0 if all(r['status'] in ('accepted_and_archived','already_recorded','archive_reconciled_without_resend') for r in results) else 2
    finally:
        try:client.logout()
        except Exception:pass


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        code=str(error) if isinstance(error,agent.CampaignError) and re.fullmatch('[a-z0-9_]+',str(error)) else 'thread_receipt_failed'
        print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

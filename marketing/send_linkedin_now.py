#!/usr/bin/env python3
"""Publish one explicitly authorized LinkedIn video. Never retry a mutation."""
from datetime import datetime,timezone
import hashlib,json,os,re,time
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import pipeline

ROOT=Path(__file__).resolve().parent
PUBLISHER=pipeline.load_module('oneoff_buffer',ROOT/'publisher/buffer_publish.py')
CAMPAIGN='linkedin-network-20261106-v1'
VIDEO='https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/quotidien/2026-11-07/13urgent-deposer-transport-20261107.mp4'
TEXT=('Vous expédiez des marchandises et cherchez un transporteur ? 🚚\n'
      'Découvrez 13 URGENT, développé par CHRONOSS.\n\n'
      'Déposez votre besoin, échangez avec les transporteurs et attribuez votre transport. '
      'Confirmation d’affrètement et lettre de voiture personnalisée intégrées.\n\n'
      '👉 https://13urgent.fr/?utm_source=linkedin&utm_medium=organic_social&utm_campaign=lancement_novembre\n'
      '#Transport #Logistique #Affrètement')


def public_link(value):
    if not isinstance(value,str):return None
    parsed=urlsplit(value)
    if parsed.scheme!='https' or parsed.hostname not in ('linkedin.com','www.linkedin.com') or parsed.username or parsed.password:return None
    if not parsed.path.startswith(('/feed/update/','/posts/')):return None
    return urlunsplit(('https',parsed.netloc,parsed.path,'',''))


def send(client,state_path,checkpoint,wait=time.sleep,max_polls=48):
    state_path=Path(state_path)
    state=json.loads(state_path.read_text())
    if state.get('schema_version')!=1 or not isinstance(state.get('posts'),dict):raise PUBLISHER.SafeFailure('state_schema')
    fingerprint=hashlib.sha256(json.dumps({'text':TEXT,'video':VIDEO,'target':'linkedin_founder','mode':'shareNow'},sort_keys=True).encode()).hexdigest()
    previous=state['posts'].get(CAMPAIGN)
    def persist():
        PUBLISHER.atomic_json(state_path,state)
        checkpoint()
    post_id=None
    if previous:
        if previous.get('fingerprint')!=fingerprint:raise PUBLISHER.SafeFailure('oneoff_content_conflict')
        if previous.get('status')=='sent':return {'status':'sent','already_recorded':True,'external_link':public_link(previous.get('external_link'))}
        hashed=previous.get('buffer_post_fingerprint')
        if not hashed:raise PUBLISHER.SafeFailure('oneoff_intent_requires_reconciliation')
        channels=client.channels()
        rows,_=client.verification_posts(channels)
        match=[r for r in rows if hashlib.sha256(r['id'].encode()).hexdigest()==hashed]
        if len(match)!=1:raise PUBLISHER.SafeFailure('oneoff_pending_requires_reconciliation')
        post_id=match[0]['id'];record=previous
    else:
        channels=client.channels()
        selected=[c for c in channels if PUBLISHER.normal(c['service'])=='linkedin' and PUBLISHER.normal(c['name'])=='haeckel hamri']
        if len(selected)!=1:raise PUBLISHER.SafeFailure('linkedin_profile_missing_or_ambiguous')
        record={'fingerprint':fingerprint,'status':'intent','created_at':datetime.now(timezone.utc).isoformat()}
        state['posts'][CAMPAIGN]=record
        persist()  # Remote checkpoint succeeds BEFORE any mutation.
        mutation=('mutation { createPost(input: { channelId: '+json.dumps(selected[0]['id'])
          +', text: '+json.dumps(TEXT)+', schedulingType: automatic, mode: shareNow, '
          +'assets: [{ video: { url: '+json.dumps(VIDEO)+' } }] }) '
          +'{ __typename ... on PostActionSuccess { post { id status schedulingType sentAt externalLink } } '
          +'... on MutationError { message } } }')
        try:
            result=client.query(mutation).get('createPost')
            if not isinstance(result,dict) or result.get('__typename')!='PostActionSuccess':
                raise PUBLISHER.SafeFailure('oneoff_creation_not_confirmed')
            saved=result.get('post')
            if not isinstance(saved,dict) or not isinstance(saved.get('id'),str) or not saved['id']:
                raise PUBLISHER.SafeFailure('oneoff_creation_uncertain')
            post_id=saved['id']
            record.update(buffer_post_fingerprint=hashlib.sha256(post_id.encode()).hexdigest(),status='scheduled',provider_status=saved.get('status'),scheduling_type=saved.get('schedulingType'))
            if saved.get('schedulingType')!='automatic':raise PUBLISHER.SafeFailure('oneoff_not_automatic')
        except Exception:
            record.update(status='uncertain',error='oneoff_creation_uncertain')
            persist()
            raise PUBLISHER.SafeFailure('oneoff_creation_uncertain') from None
        persist()
    # Read-only polling. Creation is NEVER repeated when processing is slow.
    query='query { post(input: { id: '+json.dumps(post_id)+' }) { status schedulingType sentAt externalLink } }'
    for attempt in range(max_polls):
        post=client.query(query).get('post')
        if not isinstance(post,dict):raise PUBLISHER.SafeFailure('oneoff_status_schema')
        status=post.get('status')
        record.update(provider_status=status,scheduling_type=post.get('schedulingType'),last_verified_at=datetime.now(timezone.utc).isoformat())
        if status=='sent':
            record.update(status='sent',sent_at=post.get('sentAt'))
            link=public_link(post.get('externalLink'))
            if link:record['external_link']=link
            record.pop('error',None);persist()
            return {'status':'sent','already_recorded':bool(previous),'external_link':link}
        if status in ('error','draft','needs_approval') or post.get('schedulingType')!='automatic':
            record.update(status='delivery_error',error='oneoff_publication_not_confirmed');persist()
            raise PUBLISHER.SafeFailure('oneoff_publication_not_confirmed')
        if status not in ('scheduled','sending'):raise PUBLISHER.SafeFailure('oneoff_unknown_provider_status')
        if attempt+1<max_polls:wait(5)
    persist()
    return {'status':'processing','already_recorded':bool(previous),'external_link':None}


def main():
    client=PUBLISHER.BufferClient(os.environ.get('BUFFER_API_KEY'))
    pipeline.verify_public_media(VIDEO)
    _,state=pipeline.setup_runtime()
    result=send(client,state/'state.json',lambda:pipeline.checkpoint(state))
    pipeline.write_summary(result)
    return 0 if result['status']=='sent' else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        candidate=str(error)
        code=candidate if error.__class__.__name__ in ('SafeFailure','Failure') and re.fullmatch('[a-z0-9_]+',candidate) else 'oneoff_failed'
        pipeline.write_summary({'status':'not_confirmed','error':code})
        raise SystemExit(2)

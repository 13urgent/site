#!/usr/bin/env python3
"""One authorized TikTok; no change to automatic TikTok publication holds."""
from datetime import datetime, timezone
import hashlib,json,os,re,time
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import pipeline

ROOT=Path(__file__).resolve().parent
PUBLISHER=pipeline.load_module('tiktok_oneoff_buffer',ROOT/'publisher/buffer_publish.py')
CAMPAIGN='tiktok-monexploit-testers-20261123-approved-v1'
VIDEO='https://raw.githubusercontent.com/13urgent/site/gh-pages/videos/monexploit-20261123/13urgent-monexploit-testeurs-30jours-20s.mp4'
TEXT='''🚛 Patron d’une entreprise de transport ? Nous cherchons des transporteurs pour tester Mon Exploit Mobile gratuitement pendant 30 jours !

📲 Planning, missions, signatures eCMR, photos et récépissés sur smartphone.

Le but : faciliter les échanges entre tes chauffeurs et le bureau.

Pas de paiement ni de renouvellement automatique. On t’accompagne pour la prise en main et tu nous donnes ton avis terrain.

👇 Commente « TEST » ou contacte-moi en message privé, en précisant ton nombre de chauffeurs.

#Transporteur #TransportRoutier #Logistique #TMS #MonExploit'''


def public_link(value):
    if not isinstance(value,str):return None
    p=urlsplit(value)
    if p.scheme!='https' or p.hostname not in ('tiktok.com','www.tiktok.com','vm.tiktok.com','vt.tiktok.com') or p.username or p.password:return None
    if p.hostname in ('tiktok.com','www.tiktok.com') and not re.match(r'^/@[^/]+/video/\d+',p.path):return None
    return urlunsplit(('https',p.netloc,p.path,'',''))


def select_channel(client):
    data=client.query('query { account { organizations { id } } }')
    organizations=data.get('account',{}).get('organizations')
    if not isinstance(organizations,list):raise PUBLISHER.SafeFailure('tiktok_organizations_schema')
    selected=[]
    for org in organizations:
        oid=org.get('id')
        if not isinstance(oid,str):raise PUBLISHER.SafeFailure('tiktok_organizations_schema')
        query=('query { channels(input:{organizationId:'+json.dumps(oid)+'}) '
               +'{ id name displayName service isDisconnected isLocked isQueuePaused metadata { __typename ... on TiktokMetadata { defaultToReminders } } } }')
        channels=client.query(query).get('channels')
        if not isinstance(channels,list):raise PUBLISHER.SafeFailure('tiktok_channels_schema')
        for row in channels:
            if row.get('service')!='tiktok':continue
            names=[row.get('name'),row.get('displayName')]
            if not any(isinstance(name,str) and PUBLISHER.normal(name)=='13urgentsite' for name in names):continue
            if row.get('isDisconnected') or row.get('isLocked'):raise PUBLISHER.SafeFailure('tiktok_connection_not_ready')
            if not isinstance(row.get('id'),str):raise PUBLISHER.SafeFailure('tiktok_channel_schema')
            row['organization_id']=oid;selected.append(row)
    if len(selected)!=1:raise PUBLISHER.SafeFailure('tiktok_channel_missing_or_ambiguous')
    schema=client.query('query { __type(name:"TikTokPostMetadataInput") { inputFields { name } } }').get('__type')
    fields=[field['name'] for field in (schema or {}).get('inputFields',[]) if isinstance(field,dict) and isinstance(field.get('name'),str)]
    if 'isAiGenerated' not in fields:raise PUBLISHER.SafeFailure('tiktok_ai_disclosure_unavailable')
    commercial=[field for field in fields if any(word in field.lower() for word in ('commercial','brand','promotion','sponsor'))]
    if commercial:raise PUBLISHER.SafeFailure('tiktok_commercial_fields_require_review')
    return selected[0],fields


def find_duplicate(client,channel):
    after=None;matches=[]
    for _ in range(5):
        query=('query { posts(first:20,'+('after:'+json.dumps(after)+',' if after else '')
               +'input:{organizationId:'+json.dumps(channel['organization_id'])+',filter:{channelIds:['+json.dumps(channel['id'])
               +']},sort:[{field:createdAt,direction:desc}]}) { edges { node { id text status schedulingType sentAt externalLink assets { source } } } pageInfo { hasNextPage endCursor } } }')
        data=client.query(query).get('posts')
        if not isinstance(data,dict) or not isinstance(data.get('edges'),list) or not isinstance(data.get('pageInfo'),dict):raise PUBLISHER.SafeFailure('tiktok_duplicate_schema')
        for edge in data['edges']:
            post=edge.get('node') if isinstance(edge,dict) else None
            if not isinstance(post,dict):raise PUBLISHER.SafeFailure('tiktok_duplicate_schema')
            same=' '.join((post.get('text') or '').split())==' '.join(TEXT.split())
            same_media=any(isinstance(a,dict) and a.get('source')==VIDEO for a in post.get('assets',[]))
            if same or same_media:matches.append(post)
        if not data['pageInfo'].get('hasNextPage'):
            if len(matches)>1:raise PUBLISHER.SafeFailure('tiktok_existing_duplicates_require_review')
            return matches[0] if matches else None
        cursor=data['pageInfo'].get('endCursor')
        if not isinstance(cursor,str) or not cursor or cursor==after:raise PUBLISHER.SafeFailure('tiktok_duplicate_cursor_invalid')
        after=cursor
    raise PUBLISHER.SafeFailure('tiktok_duplicate_scan_incomplete')


def send(client,state_path,checkpoint,wait=time.sleep,max_polls=48):
    state_path=Path(state_path);state=json.loads(state_path.read_text())
    if state.get('schema_version')!=1 or not isinstance(state.get('posts'),dict):raise PUBLISHER.SafeFailure('state_schema')
    fingerprint=hashlib.sha256(json.dumps({'text':TEXT,'video':VIDEO,'target':'tiktok_13urgentsite','mode':'shareNow','isAiGenerated':True},sort_keys=True).encode()).hexdigest()
    previous=state['posts'].get(CAMPAIGN)
    def persist():
        PUBLISHER.atomic_json(state_path,state);checkpoint()
    if previous:
        if previous.get('fingerprint')!=fingerprint:raise PUBLISHER.SafeFailure('tiktok_oneoff_content_conflict')
        if previous.get('status')=='sent':return {'status':'sent','already_recorded':True,'external_link':public_link(previous.get('external_link')),'ai_disclosure':previous.get('is_ai_generated')}
        # An uncertain attempt is never recreated. The owner can reconcile it in Buffer.
        raise PUBLISHER.SafeFailure('tiktok_existing_intent_requires_reconciliation')
    channel,fields=select_channel(client)
    metadata=channel.get('metadata') or {}
    pipeline.write_summary({'status':'tiktok_oneoff_preflight','ai_disclosure_available':True,'commercial_disclosure_api_available':False,'queue_paused':bool(channel.get('isQueuePaused')),'default_to_reminders':metadata.get('defaultToReminders'),'automatic_campaign_hold_unchanged':True})
    duplicate=find_duplicate(client,channel)
    if duplicate:
        if duplicate.get('status')!='sent':raise PUBLISHER.SafeFailure('tiktok_existing_post_requires_reconciliation')
        record={'fingerprint':fingerprint,'status':'sent','provider_status':'sent','sent_at':duplicate.get('sentAt'),'buffer_post_fingerprint':hashlib.sha256(duplicate['id'].encode()).hexdigest(),'existing_post_reconciled':True}
        link=public_link(duplicate.get('externalLink'))
        if link:record['external_link']=link
        state['posts'][CAMPAIGN]=record;persist()
        return {'status':'sent','already_recorded':True,'external_link':link}
    record={'fingerprint':fingerprint,'status':'intent','created_at':datetime.now(timezone.utc).isoformat(),'ai_disclosure_requested':True,'commercial_disclosure_api_available':False,'queue_paused_before':bool(channel.get('isQueuePaused'))}
    state['posts'][CAMPAIGN]=record;persist()
    mutation=('mutation { createPost(input:{channelId:'+json.dumps(channel['id'])+',text:'+json.dumps(TEXT)
              +',schedulingType:automatic,mode:shareNow,assets:[{video:{url:'+json.dumps(VIDEO)+'}}],metadata:{tiktok:{isAiGenerated:true}}}) '
              +'{ __typename ... on PostActionSuccess { post { id status schedulingType sentAt externalLink metadata { ... on TiktokPostMetadata { isAiGenerated } } } } ... on MutationError { message } } }')
    try:
        result=client.query(mutation).get('createPost')
        if not isinstance(result,dict) or result.get('__typename')!='PostActionSuccess':
            error_type=result.get('__typename') if isinstance(result,dict) else None
            record.update(status='rejected',error='tiktok_creation_rejected')
            if isinstance(error_type,str) and re.fullmatch('[A-Za-z]+Error',error_type):record['provider_error_type']=error_type
            persist();raise PUBLISHER.SafeFailure('tiktok_creation_rejected')
        saved=result.get('post')
        if not isinstance(saved,dict) or not isinstance(saved.get('id'),str) or not saved['id']:raise PUBLISHER.SafeFailure('tiktok_creation_uncertain')
        post_id=saved['id'];record.update(buffer_post_fingerprint=hashlib.sha256(post_id.encode()).hexdigest(),status='scheduled',provider_status=saved.get('status'),scheduling_type=saved.get('schedulingType'),is_ai_generated=(saved.get('metadata') or {}).get('isAiGenerated'))
        persist()
    except PUBLISHER.SafeFailure:
        if record.get('status')=='intent':record.update(status='uncertain',error='tiktok_creation_uncertain');persist()
        raise
    except Exception:
        record.update(status='uncertain',error='tiktok_creation_uncertain');persist()
        raise PUBLISHER.SafeFailure('tiktok_creation_uncertain') from None
    query=('query { post(input:{id:'+json.dumps(post_id)+'}) { status schedulingType sentAt externalLink metadata { ... on TiktokPostMetadata { isAiGenerated } } } }')
    for attempt in range(max_polls):
        post=client.query(query).get('post')
        if not isinstance(post,dict):raise PUBLISHER.SafeFailure('tiktok_status_schema')
        status=post.get('status');record.update(provider_status=status,scheduling_type=post.get('schedulingType'),last_verified_at=datetime.now(timezone.utc).isoformat(),is_ai_generated=(post.get('metadata') or {}).get('isAiGenerated'))
        if status=='sent':
            record.update(status='sent',sent_at=post.get('sentAt'))
            link=public_link(post.get('externalLink'))
            if link:record['external_link']=link
            persist();return {'status':'sent','already_recorded':False,'external_link':link,'ai_disclosure':record.get('is_ai_generated'),'commercial_disclosure_api_available':False,'automatic_campaign_hold_unchanged':True}
        if status in ('draft','needs_approval') or post.get('schedulingType')=='notification':
            record.update(status='manual_completion_required',error='tiktok_manual_completion_required');persist()
            return {'status':'manual_completion_required','provider_status':status,'scheduling_type':post.get('schedulingType'),'next_step':'open_existing_post_in_Buffer_and_complete_in_TikTok','automatic_campaign_hold_unchanged':True}
        if status=='error':
            record.update(status='delivery_error',error='tiktok_publication_failed');persist()
            raise PUBLISHER.SafeFailure('tiktok_publication_failed')
        if status not in ('scheduled','sending'):raise PUBLISHER.SafeFailure('tiktok_unknown_provider_status')
        if attempt+1<max_polls:wait(5)
    persist();return {'status':'processing','provider_status':record.get('provider_status'),'already_recorded':False,'external_link':None,'automatic_campaign_hold_unchanged':True}


def main():
    pipeline.verify_public_media(VIDEO)
    _,state=pipeline.setup_runtime()
    result=send(PUBLISHER.BufferClient(os.environ.get('BUFFER_API_KEY')),state/'state.json',lambda:pipeline.checkpoint(state))
    pipeline.write_summary(result)
    return 0 if result['status']=='sent' else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        candidate=str(error)
        code=candidate if error.__class__.__name__ in ('SafeFailure','Failure') and re.fullmatch('[a-z0-9_]+',candidate) else 'tiktok_oneoff_failed'
        pipeline.write_summary({'status':'not_confirmed','error':code,'automatic_campaign_hold_unchanged':True})
        raise SystemExit(2)

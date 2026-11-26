#!/usr/bin/env python3
"""Four authorized organic posts; audit calendar first, never retry mutations."""
from datetime import datetime,timedelta,date,time,timezone
import argparse,hashlib,json,os
from pathlib import Path
from zoneinfo import ZoneInfo
import pipeline

PARIS=ZoneInfo('Europe/Paris')
ROOT=Path(__file__).resolve().parent
PUBLISHER=pipeline.load_module('commercial_scheduler_buffer',ROOT/'publisher/buffer_publish.py')
MIN_GAP=timedelta(hours=18)
TARGETS={('linkedin','haeckel hamri'):'linkedin_founder',('tiktok','13urgentsite'):'tiktok'}


def parsed(value):
    if not isinstance(value,str):return None
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result if result.utcoffset() is not None else None
    except ValueError:return None


class Client(PUBLISHER.BufferClient):
    def channels(self):
        organizations=self.query('query { account { organizations { id } } }').get('account',{}).get('organizations')
        if not isinstance(organizations,list):raise PUBLISHER.SafeFailure('calendar_account_schema')
        approved=[];self.context={}
        for org in organizations:
            oid=org.get('id')
            if not isinstance(oid,str):raise PUBLISHER.SafeFailure('calendar_account_schema')
            rows=self.query('query { channels(input:{organizationId:'+json.dumps(oid)+'}) { id name displayName service isDisconnected isLocked isQueuePaused } }').get('channels')
            if not isinstance(rows,list):raise PUBLISHER.SafeFailure('calendar_channels_schema')
            for row in rows:
                roles=set()
                for name in (row.get('name'),row.get('displayName')):
                    if isinstance(name,str):
                        role=TARGETS.get((PUBLISHER.normal(row.get('service','')),PUBLISHER.normal(name)))
                        if role:roles.add(role)
                if not roles:continue
                if len(roles)!=1 or not isinstance(row.get('id'),str):raise PUBLISHER.SafeFailure('calendar_channel_ambiguous')
                if row.get('isDisconnected') or row.get('isLocked') or row.get('isQueuePaused'):raise PUBLISHER.SafeFailure('calendar_channel_not_ready')
                role=next(iter(roles));name='Haeckel Hamri' if role=='linkedin_founder' else '13urgentsite'
                c={'id':row['id'],'name':name,'service':row['service']};approved.append(c)
                self.context[role]={'channel':c,'organization':oid}
        if any(sum(1 for c in approved if c['name']==name)!=1 for name in ('Haeckel Hamri','13urgentsite')):raise PUBLISHER.SafeFailure('calendar_target_missing_or_ambiguous')
        return approved

    def calendar(self):
        self.channels();rows=[]
        for role,ctx in self.context.items():
            after=None
            for page in range(5):
                q=('query { posts(first:50,'+('after:'+json.dumps(after)+',' if after else '')
                   +'input:{organizationId:'+json.dumps(ctx['organization'])+',filter:{channelIds:['+json.dumps(ctx['channel']['id'])
                   +']},sort:[{field:createdAt,direction:desc}]}) { edges { node { id text status dueAt sentAt schedulingType externalLink } } pageInfo { hasNextPage endCursor } } }')
                data=self.query(q).get('posts')
                if not isinstance(data,dict) or not isinstance(data.get('edges'),list) or not isinstance(data.get('pageInfo'),dict):raise PUBLISHER.SafeFailure('calendar_posts_schema')
                for edge in data['edges']:
                    p=edge.get('node') if isinstance(edge,dict) else None
                    if not isinstance(p,dict) or not isinstance(p.get('id'),str):raise PUBLISHER.SafeFailure('calendar_posts_schema')
                    rows.append({'role':role,'post':p})
                if not data['pageInfo'].get('hasNextPage'):break
                after=data['pageInfo'].get('endCursor')
                if not isinstance(after,str) or not after:raise PUBLISHER.SafeFailure('calendar_cursor_invalid')
            else:raise PUBLISHER.SafeFailure('calendar_scan_incomplete')
        return rows

    def create(self,post,channel):
        if post['service']!='tiktok':return super().create(post,channel)
        q=('mutation { createPost(input:{channelId:'+json.dumps(channel['id'])+',text:'+json.dumps(post['text'])
           +',schedulingType:automatic,mode:customScheduled,dueAt:'+json.dumps(post['due_at'])
           +',assets:[{video:{url:'+json.dumps(post['video_url'])+'}}],metadata:{tiktok:{isAiGenerated:true}}}) '
           +'{ __typename ... on PostActionSuccess { post { id status dueAt schedulingType metadata { ... on TiktokPostMetadata { isAiGenerated } } } } ... on MutationError { message } } }')
        result=self.query(q).get('createPost')
        saved=result.get('post') if isinstance(result,dict) else None
        if not isinstance(result,dict) or result.get('__typename')!='PostActionSuccess' or not isinstance(saved,dict) or not isinstance(saved.get('id'),str):raise PUBLISHER.SafeFailure('tiktok_schedule_uncertain')
        expected,actual=parsed(post['due_at']),parsed(saved.get('dueAt'))
        accepted=saved.get('status')=='scheduled' and saved.get('schedulingType')=='automatic' and expected and actual and abs((expected-actual).total_seconds())<=1
        ai=(saved.get('metadata') or {}).get('isAiGenerated')
        return {'status':'scheduled' if accepted and ai is True else 'provider_not_scheduled','provider_status':saved.get('status'),'scheduling_type':saved.get('schedulingType'),'buffer_post_id':saved['id'],'due_at':saved.get('dueAt'),'is_ai_generated':ai}


def public_calendar(rows,now):
    result=[]
    for row in rows:
        post=row['post'];due=parsed(post.get('dueAt'))
        if not due or due<now-timedelta(days=2) or due>now+timedelta(days=18):continue
        text=post.get('text') or ''
        topic='mon_exploit' if 'Mon Exploit' in text else 'chronoss' if 'demander-un-devis' in text else '13_urgent'
        result.append({'target':row['role'],'status':post.get('status'),'due_at':due.isoformat(),'topic':topic,'post_fingerprint':hashlib.sha256(post['id'].encode()).hexdigest()})
    return sorted(result,key=lambda r:r['due_at'])


def build_plan(requested,rows,settings,now):
    occupied={'linkedin_founder':[],'tiktok':[]}
    for row in rows:
        post=row['post']
        if post.get('status') not in ('scheduled','sending','sent'):continue
        instant=parsed(post.get('dueAt')) or parsed(post.get('sentAt'))
        if instant:occupied[row['role']].append(instant)
    account=next(a for a in settings['accounts'] if a.get('caption_key')=='linkedin_founder')
    auto_days=set(account['weekdays']) if settings.get('enabled') and not settings.get('publication_holds',{}).get('linkedin') else set()
    auto_hour=time.fromisoformat(account['hour'])
    # Include known future automatic cadence, even before the daily job creates
    # those posts. This avoids collisions that a snapshot of Buffer alone misses.
    for offset in range(19):
        day=now.astimezone(PARIS).date()+timedelta(days=offset)
        if day.weekday() in auto_days:occupied['linkedin_founder'].append(datetime.combine(day,auto_hour,PARIS))
    selected=[];adjustments=[]
    for request in requested['posts']:
        role=request['target'];day=date.fromisoformat(request['requested_date']);hour=time.fromisoformat(request['hour'])
        candidates=([day,date(2026,11,30)] if role=='tiktok' else [day+timedelta(days=i) for i in range(8)])
        chosen=None
        for candidate in dict.fromkeys(candidates):
            if role=='linkedin_founder' and candidate.weekday() in auto_days:continue
            instant=datetime.combine(candidate,hour,PARIS)
            if instant<=now+timedelta(hours=1):continue
            if any(abs(instant-other)<MIN_GAP or instant.astimezone(PARIS).date()==other.astimezone(PARIS).date() for other in occupied[role]):continue
            chosen=instant;break
        if chosen is None:raise PUBLISHER.SafeFailure('no_spaced_calendar_slot')
        occupied[role].append(chosen)
        selected.append({'id':request['id'],'channel_name':'Haeckel Hamri' if role=='linkedin_founder' else '13urgentsite','service':'linkedin' if role=='linkedin_founder' else 'tiktok','text':request['text'],'video_url':request.get('video_url'),'due_at':chosen.astimezone(timezone.utc).isoformat().replace('+00:00','Z')})
        adjustments.append({'id':request['id'],'target':role,'requested_date':request['requested_date'],'chosen_paris':chosen.isoformat(),'date_adjusted':chosen.date()!=day,'reason':'existing_calendar_and_future_automatic_cadence' if chosen.date()!=day else 'spaced_slot_available'})
    return {'posts':selected},adjustments


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['audit','publish'],default='audit');args=parser.parse_args()
    request=json.loads((ROOT/'commercial_plan_20261126.json').read_text());settings=pipeline.config();now=datetime.now(timezone.utc)
    client=Client(os.environ.get('BUFFER_API_KEY'));rows=client.calendar()
    plan,adjustments=build_plan(request,rows,settings,now);PUBLISHER.validate_plan(plan)
    report={'mode':args.mode,'checked_at':now.isoformat(),'minimum_spacing_hours':18,'calendar':public_calendar(rows,now),'selected_slots':adjustments,'new_posts_created':0,'automatic_tiktok_hold_preserved':bool(settings.get('publication_holds',{}).get('tiktok'))}
    output=pipeline.REPO/'.runtime/commercial-planning-report.json';output.parent.mkdir(parents=True,exist_ok=True)
    if args.mode=='audit':
        PUBLISHER.atomic_json(output,report);print(json.dumps(report,ensure_ascii=False));return 0
    # Resolve unknown schema settings BEFORE any creation.
    schema=client.query('query { __type(name:"TikTokPostMetadataInput") { inputFields { name } } }').get('__type')
    fields=[f.get('name') for f in (schema or {}).get('inputFields',[])]
    if 'isAiGenerated' not in fields:raise PUBLISHER.SafeFailure('tiktok_ai_disclosure_unavailable')
    for post in plan['posts']:
        if post.get('video_url'):pipeline.verify_public_media(post['video_url'])
    _,state_dir=pipeline.setup_runtime();state_path=state_dir/'state.json';state=json.loads(state_path.read_text())
    # Content is compared in memory only; reports never contain queried text.
    new_posts=[];existing=[]
    for post in plan['posts']:
        record=state['posts'].get(post['id'])
        if record:
            # Never let a calendar change cause recreation of a previous id.
            if record.get('status') not in ('scheduled','sent'):raise PUBLISHER.SafeFailure('existing_intent_requires_reconciliation')
            existing.append({'id':post['id'],'status':record['status'],'due_at':record.get('due_at'),'already_recorded':True});continue
        role='linkedin_founder' if post['service']=='linkedin' else 'tiktok'
        if any(row['role']==role and ' '.join((row['post'].get('text') or '').split())==' '.join(post['text'].split()) for row in rows):raise PUBLISHER.SafeFailure('matching_content_already_exists')
        new_posts.append(post)
    delivery=PUBLISHER.run(client,'publish',{'posts':new_posts},state_path,pipeline.REPO/'.runtime/commercial-publisher-report.json',checkpoint=lambda:pipeline.checkpoint(state_dir))
    report['results']=existing+delivery['posts'];report['new_posts_created']=sum(p.get('status')=='scheduled' for p in delivery['posts']);report['ok']=delivery['ok']
    # Read the known posts back by hashes, keeping raw Buffer ids only in memory.
    refreshed=client.calendar();current=json.loads(state_path.read_text());verified=[]
    by_hash={hashlib.sha256(r['post']['id'].encode()).hexdigest():r['post'] for r in refreshed}
    for post in plan['posts']:
        record=current['posts'].get(post['id'],{});observed=by_hash.get(record.get('buffer_post_fingerprint'))
        if not observed:raise PUBLISHER.SafeFailure('scheduled_post_readback_missing')
        # Scheduled posts do not yet have a public platform publication URL.
        verified.append({'id':post['id'],'provider_status':observed.get('status'),'scheduling_type':observed.get('schedulingType'),'due_at':observed.get('dueAt'),'public_post_url':None,'post_fingerprint':record.get('buffer_post_fingerprint')})
        if observed.get('status')!='scheduled' or observed.get('schedulingType')!='automatic':report['ok']=False
    report['verified_posts']=verified
    PUBLISHER.atomic_json(output,report);print(json.dumps(report,ensure_ascii=False))
    return 0 if report['ok'] else 2


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        code=str(error) if error.__class__.__name__ in ('SafeFailure','Failure') else 'commercial_planning_failed'
        if not code.replace('_','').isalnum():code='commercial_planning_failed'
        print(json.dumps({'status':'blocked','error':code,'no_automatic_retry':True}));raise SystemExit(2)

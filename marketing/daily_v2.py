#!/usr/bin/env python3
"""Owner-authorized 2/day/channel rotation, with a bounded free Buffer queue."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
import pipeline
from cadence_v2_api import Client,P,hashed,moment,same_time,desired

ROOT=Path(__file__).resolve().parent
PARIS=ZoneInfo('Europe/Paris')
PREFIX='daily2-'

def settings():
    value=pipeline.config()
    if not value.get('daily_v2',{}).get('enabled'):raise P.SafeFailure('daily2_disabled')
    return value

def catalogue():
    value=json.loads((ROOT/'rotation_catalogue.json').read_text())
    topics=value.get('topics',[])
    if len(topics)!=62 or len({t.get('id') for t in topics})!=62 or len({t.get('hook') for t in topics})!=62:raise P.SafeFailure('daily2_catalogue_invalid')
    for topic in topics:
        if topic.get('service') not in ('urgent','mon_exploit','chronoss') or not topic.get('cta_url','').startswith('https://13urgent.fr/'):raise P.SafeFailure('daily2_topic_not_authorized')
        if any(not isinstance(topic.get(key),str) or not topic[key].strip() for key in ('linkedin','tiktok','hook','body')):raise P.SafeFailure('daily2_topic_incomplete')
    return topics

def overrides():return json.loads((ROOT/'cadence_v2_overrides.json').read_text())

def topic_for(day,slot,topics,config):
    start=date.fromisoformat(config['daily_v2']['starts_on'])
    return topics[((day-start).days%31)*2+slot]

def media_url(day,slot,topic,config):
    filename=config['daily_v2']['asset_revision']+'-'+topic['id']+'-s'+str(slot)+'.mp4'
    path=Path(config['daily_v2']['media_prefix'])/day.isoformat()/filename
    return 'https://raw.githubusercontent.com/13urgent/site/'+config['media_branch']+'/'+str(path)

def entry(day,slot,service,topics,config):
    topic=topic_for(day,slot,topics,config)
    account=next(a for a in config['accounts'] if a['service']==service)
    hour,minute=map(int,account['hours'][slot].split(':'))
    due=datetime.combine(day,datetime.min.time(),PARIS).replace(hour=hour,minute=minute)
    text=topic['linkedin' if service=='linkedin' else 'tiktok']
    for override in overrides():
        if (override['date'],override['slot'],override['service'])==(day.isoformat(),slot,service):text=override['text'];break
    return {'id':PREFIX+day.strftime('%Y%m%d')+'-s'+str(slot)+'-'+service,
            'channel_name':account['name'],'service':service,'text':text,
            'video_url':media_url(day,slot,topic,config),
            'due_at':due.astimezone(timezone.utc).isoformat().replace('+00:00','Z')}

def horizon(begin,days,topics,config,now=None):
    posts=[]
    for delta in range(days):
        day=begin+timedelta(days=delta)
        for slot in (0,1):
            for service in ('linkedin','tiktok'):
                post=entry(day,slot,service,topics,config)
                if now is None or moment(post['due_at'])>now+timedelta(minutes=2):posts.append(post)
    P.validate_plan({'posts':posts});return posts

def fingerprint(post):return hashlib.sha256(json.dumps(post,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def persist(state_path,state):
    P.atomic_json(state_path,state);pipeline.checkpoint(state_path.parent)

def push_media(media):
    pipeline.git(media,'add',settings()['daily_v2']['media_prefix'])
    if pipeline.git(media,'diff','--cached','--quiet',allowed=(0,1)).returncode==0:return
    pipeline.git(media,'commit','-m','Prepare approved voiced and music-backed daily presentations')
    branch=settings()['media_branch']
    for attempt in range(3):
        result=subprocess.run(['git','-C',str(media),'push','origin','HEAD:refs/heads/'+branch],capture_output=True,text=True,timeout=120)
        if result.returncode==0:return
        # Only ordinary concurrent new commits are rebased. Never force push or
        # change authentication after an access denial.
        if attempt==2 or not any(word in result.stderr.lower() for word in ('non-fast-forward','fetch first','rejected')):raise P.SafeFailure('daily2_media_push_failed')
        if '403' in result.stderr or 'permission' in result.stderr.lower():raise P.SafeFailure('daily2_media_push_denied')
        pipeline.git(media,'fetch','origin','refs/heads/'+branch+':refs/remotes/origin/'+branch)
        pipeline.git(media,'rebase','origin/'+branch)

def prepare_media(keys,media,topics,config):
    renderer=pipeline.load_module('daily2_renderer',ROOT/'render_rotation.py')
    os.environ.setdefault('MARKETING_MEDIA_CACHE',str(pipeline.REPO/'.runtime/approved-sources'))
    os.environ.setdefault('MARKETING_FONT_DIR',str(ROOT/'video/assets/fonts'))
    os.environ['MARKETING_MUSIC_URL']=config['daily_v2']['music_url']
    written=[]
    for day,slot in sorted(set(keys)):
        topic=topic_for(day,slot,topics,config);url=media_url(day,slot,topic,config)
        relative=Path(config['daily_v2']['media_prefix'])/day.isoformat()/url.rsplit('/',1)[-1]
        target=media/relative
        if target.exists():continue  # Immutable media, never overwrite a used URL.
        out=pipeline.REPO/'.runtime/output'/(day.isoformat()+'-s'+str(slot))
        rendered=renderer.render(topic,day,slot,out)
        manifest=json.loads(Path(rendered['manifest']).read_text())
        if not manifest.get('voice',{}).get('present') or not manifest.get('music',{}).get('ducked_under_speech') or manifest.get('audio_metrics',{}).get('mean_db',-100)<-35:raise P.SafeFailure('daily2_voice_and_music_not_verified')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(rendered['video'],target)
        base=target.with_suffix('');shutil.copyfile(rendered['manifest'],str(base)+'.manifest.json');shutil.copyfile(rendered['cover'],str(base)+'.jpg')
        written.append(relative)
    if written:push_media(media)
    for day,slot in sorted(set(keys)):pipeline.verify_public_media(media_url(day,slot,topic_for(day,slot,topics,config),config))
    return len(written)

def migration_items(topics,config):
    return [(override,entry(date.fromisoformat(override['date']),override['slot'],override['service'],topics,config)) for override in overrides()]

def migrate(client,state_path,topics,config):
    state=json.loads(state_path.read_text())
    if state.get('daily2_migration',{}).get('status')=='completed':return {'status':'already_completed','edited':0,'recreated':0,'company_drafted':0}
    client.check_edit_schema();rows=client.scan();by_hash={hashed(row['id']):row for row in rows};fallback=[];edited=0;drafted=0
    state.setdefault('daily2_edits',{})
    # Retire only known automation posts on the old company page; preserve their
    # content as drafts. Unknown manual posts are surfaced, never silently erased.
    start=datetime.combine(date.fromisoformat(config['daily_v2']['starts_on']),datetime.min.time(),PARIS)
    for row in rows:
        if row['role']!='company' or row.get('status')!='scheduled' or not moment(row.get('dueAt')) or moment(row['dueAt'])<start:continue
        known=[(key,r) for key,r in state['posts'].items() if r.get('buffer_post_fingerprint')==hashed(row['id'])]
        if not known:raise P.SafeFailure('unknown_company_page_post_requires_review')
        key,record=known[0];record['retirement_intent']=True;persist(state_path,state)
        result=client.edit(row['id'],draft=True)
        check=client.post(row['id'])
        if check.get('status')!='draft':raise P.SafeFailure('company_page_draft_not_confirmed')
        record.update(status='draft',provider_status='draft',retired_by_daily2=True);persist(state_path,state);drafted+=1
    for override,plan in migration_items(topics,config):
        if plan['id'] in state['posts']:
            if state['posts'][plan['id']].get('status') not in ('scheduled','sent'):raise P.SafeFailure('daily2_existing_migration_uncertain')
            continue
        legacy=state['posts'].get(override['legacy_id'])
        if not legacy:raise P.SafeFailure('daily2_legacy_reservation_missing')
        old_hash=legacy.get('buffer_post_fingerprint') or legacy.get('migrated_post_fingerprint');old=by_hash.get(old_hash)
        if not old:raise P.SafeFailure('daily2_legacy_post_not_found')
        marker=state['daily2_edits'].get(plan['id'])
        if marker and marker.get('status')=='old_timer_canceled' and old.get('status')=='draft':
            # Safe recovery after a confirmed cancellation checkpoint: the old
            # timer is still a draft, and creation has not been recorded yet.
            fallback.append(plan);continue
        if old.get('status')!='scheduled':raise P.SafeFailure('daily2_legacy_not_scheduled')
        if ' '.join((old.get('text') or '').split())!=' '.join(plan['text'].split()):raise P.SafeFailure('daily2_legacy_content_changed')
        if marker and marker.get('status')=='intent':
            # A failed runner may have received no edit response. Re-read first;
            # never blindly retry or create a second post.
            check=client.post(old['id'])
            if not desired(check,plan):raise P.SafeFailure('daily2_edit_requires_reconciliation')
        else:
            state['daily2_edits'][plan['id']]={'status':'intent','source_post_fingerprint':old_hash,'old_due_at':old.get('dueAt'),'target_due_at':plan['due_at']};persist(state_path,state)
            try:
                result=client.edit(old['id'],plan)
            except Exception:
                check=client.post(old['id'])
                if not desired(check,plan):raise P.SafeFailure('daily2_edit_result_uncertain') from None
            else:
                if result.get('rejected'):
                    # A typed rejection is distinct from an uncertain timeout.
                    # Cancel the old timer by verified drafting before recreation.
                    canceled=client.edit(old['id'],draft=True);check=client.post(old['id'])
                    if check.get('status')!='draft':raise P.SafeFailure('daily2_old_cancellation_not_confirmed')
                    legacy.update(status='draft',provider_status='draft',cancellation_confirmed=True)
                    state['daily2_edits'][plan['id']].update(status='old_timer_canceled',method='verified_draft_then_recreate');persist(state_path,state);fallback.append(plan);continue
                check=client.post(old['id'])
                if not desired(check,plan):raise P.SafeFailure('daily2_edit_readback_not_confirmed')
        legacy.update(status='migrated_alias',migrated_post_fingerprint=old_hash,canonical_id=plan['id'],old_due_at=old.get('dueAt'),due_at=plan['due_at']);legacy.pop('buffer_post_fingerprint',None)
        state['posts'][plan['id']]={'fingerprint':fingerprint(plan),'status':'scheduled','provider_status':'scheduled','scheduling_type':'automatic','due_at':plan['due_at'],'buffer_post_fingerprint':old_hash,'migrated_from':override['legacy_id'],'voice_and_music':True,'is_ai_generated':plan['service']=='tiktok'}
        state['daily2_edits'][plan['id']].update(status='completed',method='edit_existing_post',provider_status='scheduled');persist(state_path,state);edited+=1
    if fallback:
        report=P.run(client,'publish',{'posts':fallback},state_path,pipeline.REPO/'.runtime/daily2-fallback.json',checkpoint=lambda:pipeline.checkpoint(state_path.parent))
        if not report['ok']:raise P.SafeFailure('daily2_recreation_not_confirmed')
        state=json.loads(state_path.read_text())
        for plan in fallback:state['daily2_edits'][plan['id']].update(status='completed',provider_status='scheduled')
    state['daily2_migration']={'status':'completed','version':2,'completed_at':datetime.now(timezone.utc).isoformat(),'old_company_page_cadence_removed':True};persist(state_path,state)
    return {'status':'completed','edited':edited,'recreated':len(fallback),'company_drafted':drafted}

def reconcile(client,state_path):
    rows=client.scan();by_hash={hashed(r['id']):r for r in rows};state=json.loads(state_path.read_text());counts={'scheduled':0,'sent':0,'errors':0,'uncertain':0};changed=False
    for key,record in state['posts'].items():
        if not key.startswith(PREFIX):continue
        row=by_hash.get(record.get('buffer_post_fingerprint'))
        if row:
            status=row.get('status');record['provider_status']=status
            if status=='sent':record.update(status='sent',sent_at=row.get('sentAt'));changed=True
            elif status=='error':record.update(status='delivery_error',error='daily2_delivery_failed');changed=True
        status=record.get('status')
        if status in ('scheduled','sent'):counts[status]+=1
        elif status=='delivery_error':counts['errors']+=1
        else:counts['uncertain']+=1
    if changed:persist(state_path,state)
    return counts,rows

def safe_slots(posts):
    return [{'id':p['id'],'service':p['service'],'due_at':p['due_at'],'topic':'mon_exploit' if '/mon-exploit.html' in p['text'] else 'chronoss' if '/demander-un-devis.html' in p['text'] else '13_urgent'} for p in posts]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['probe','verify','publish','migrate','preview'],default='probe');parser.add_argument('--date');parser.add_argument('--scheduled',action='store_true');args=parser.parse_args()
    config=settings();topics=catalogue();now=datetime.now(timezone.utc);start=date.fromisoformat(config['daily_v2']['starts_on']);begin=max(start,date.fromisoformat(args.date) if args.date else now.astimezone(PARIS).date())
    posts=horizon(begin,config['daily_v2']['rolling_days'],topics,config,now)
    if args.mode=='preview':
        renderer=pipeline.load_module('daily2_preview_renderer',ROOT/'render_rotation.py')
        for slot in (0,1):renderer.render(topic_for(begin,slot,topics,config),begin,slot,pipeline.REPO/'.runtime/output'/(begin.isoformat()+'-s'+str(slot)))
        pipeline.write_summary({'status':'daily2_previews_created','posts_created':0,'slots':safe_slots(posts[:4])});return 0
    client=Client(os.environ.get('BUFFER_API_KEY'));rows=client.scan()
    if args.mode=='probe':
        pipeline.git(pipeline.REPO,'fetch','--depth=1','origin','refs/heads/marketing-state')
        ledger=json.loads(pipeline.git(pipeline.REPO,'show','FETCH_HEAD:state.json').stdout)
        expected={ledger.get('posts',{}).get(o['legacy_id'],{}).get('buffer_post_fingerprint') for o in overrides()};expected.discard(None)
        multiple=client.scan(selection='multiple');unfiltered=client.scan(selection='unfiltered')
        comparisons={name:{'rows':len(values),'legacy_matches':len({hashed(row['id']) for row in values}&expected),'scheduled':sum(row.get('status')=='scheduled' for row in values)} for name,values in [('single_status',rows),('multiple_statuses',multiple),('unfiltered',unfiltered)]}
        pipeline.write_summary({'status':'daily2_connection_and_plan_checked','active_accounts':2,'posts_per_account_per_day':2,'cycle_days':31,'rolling_days':4,'queue_limit_per_account':10,'new_posts_created':0,'first_day_slots':safe_slots(posts[:4]),'company_page_scheduling':False,'calendar_comparison':comparisons});return 0
    media,state_dir=pipeline.setup_runtime();state_path=state_dir/'state.json'
    if args.mode=='verify':
        counts,_=reconcile(client,state_path);pipeline.write_summary({'status':'daily2_delivery_check','counts':counts,'new_posts_created':0});return 0 if not counts['errors'] and not counts['uncertain'] else 2
    keys={(date.fromisoformat(o['date']),o['slot']) for o in overrides()}
    if args.mode=='publish':keys.update((begin+timedelta(days=offset),slot) for offset in range(config['daily_v2']['rolling_days']) for slot in (0,1))
    rendered=prepare_media(keys,media,topics,config)
    migration=migrate(client,state_path,topics,config)
    if args.mode=='migrate':
        pipeline.write_summary({'status':'daily2_old_posts_normalized','migration':migration,'new_media':rendered,'new_cadence':{'linkedin':['10:00','17:00'],'tiktok':['10:00','19:00']},'timezone':'Europe/Paris'});return 0
    counts,rows=reconcile(client,state_path);state=json.loads(state_path.read_text())
    by_hash={hashed(row['id']):row for row in rows};known={r.get('buffer_post_fingerprint') for r in state['posts'].values() if r.get('buffer_post_fingerprint')}
    queue={'founder':0,'tiktok':0}
    for row in rows:
        if row['role'] not in queue or row.get('status') not in ('scheduled','sending'):continue
        queue[row['role']]+=1
        if hashed(row['id']) not in known:raise P.SafeFailure('daily2_unknown_queued_post_requires_review')
    for service,role in [('linkedin','founder'),('tiktok','tiktok')]:
        missing=sum(p['service']==service and p['id'] not in state['posts'] for p in posts)
        if queue[role]+missing>config['daily_v2']['buffer_free_limit_per_channel']:raise P.SafeFailure('daily2_free_queue_capacity_reached')
    # Never duplicate an identical human-posted text outside the ledger.
    for post in posts:
        if post['id'] in state['posts']:continue
        role='founder' if post['service']=='linkedin' else 'tiktok'
        if any(row['role']==role and ' '.join((row.get('text') or '').split())==' '.join(post['text'].split()) for row in rows):raise P.SafeFailure('daily2_duplicate_content_detected')
    report=P.run(client,'publish',{'posts':posts},state_path,pipeline.REPO/'.runtime/daily2-publish-report.json',checkpoint=lambda:pipeline.checkpoint(state_dir))
    latest=json.loads(state_path.read_text());observed=client.scan();current={hashed(row['id']):row for row in observed};verified=[]
    for post in posts:
        record=latest['posts'].get(post['id'],{});row=current.get(record.get('buffer_post_fingerprint'))
        if not row or row.get('status')!='scheduled' or row.get('schedulingType')!='automatic' or not same_time(row.get('dueAt'),post['due_at']):raise P.SafeFailure('daily2_schedule_readback_failed')
        verified.append({'id':post['id'],'service':post['service'],'provider_status':row['status'],'scheduling_type':row['schedulingType'],'due_at':row['dueAt'],'voice_and_music':True,'public_post_url':None})
    first=[row for row in verified if moment(row['due_at']).astimezone(PARIS).date()==begin]
    result={'status':'daily2_rolling_queue_confirmed' if report['ok'] else 'needs_attention','ok':report['ok'],'start_date':begin.isoformat(),'horizon_days':31,'rolling_days':4,'active_accounts':2,'posts_per_account_per_day':2,'new_posts_scheduled':sum(row.get('status')=='scheduled' for row in report['posts']),'already_recorded':sum(row.get('status')=='already_recorded' for row in report['posts']),'migration':migration,'first_day_verified_posts':first,'verified_rolling_posts':verified,'new_media':rendered,'original_music_under_approved_voice':True,'company_page_scheduling':False,'paid_generation':False}
    P.atomic_json(pipeline.REPO/'.runtime/daily2-result.json',result);pipeline.write_summary(result)
    return 0 if report['ok'] else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        code=str(error) if error.__class__.__name__ in ('SafeFailure','Failure') else 'daily2_step_failed'
        if not re.fullmatch('[a-z0-9_]+',code):code='daily2_step_failed'
        pipeline.write_summary({'status':'blocked','error':code,'no_automatic_creation_retry_after_uncertainty':True});raise SystemExit(2)

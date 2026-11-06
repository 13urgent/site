#!/usr/bin/env python3
"""Daily publishing of reviewed 13 URGENT topics. No paid AI or trend claim."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import urlencode,urlsplit,urlunsplit
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PARIS=ZoneInfo('Europe/Paris')

class Failure(Exception): pass

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def git(path,*args,allowed=(0,)):
    result=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,timeout=120)
    if result.returncode not in allowed:
        raise Failure('git_operation_failed_'+args[0])
    return result

def config():
    value=json.loads((ROOT/'config.json').read_text())
    if not value.get('enabled'):raise Failure('marketing_disabled')
    return value

def setup_runtime():
    config_value=config()
    runtime=REPO/'.runtime';runtime.mkdir(exist_ok=True)
    git(REPO,'config','user.name','13 URGENT automation')
    git(REPO,'config','user.email','automation@users.noreply.github.com')
    media=runtime/'media'
    if not media.exists():
        git(REPO,'fetch','--depth=1','origin','refs/heads/'+config_value['media_branch']+':refs/remotes/origin/'+config_value['media_branch'])
        git(REPO,'worktree','add','--detach',str(media),'origin/'+config_value['media_branch'])
    state=runtime/'state'
    if not state.exists():
        exists=git(REPO,'ls-remote','--exit-code','--heads','origin',config_value['state_branch'],allowed=(0,2)).returncode==0
        if exists:
            git(REPO,'fetch','--depth=1','origin','refs/heads/'+config_value['state_branch']+':refs/remotes/origin/'+config_value['state_branch'])
            git(REPO,'worktree','add','--detach',str(state),'origin/'+config_value['state_branch'])
        else:
            git(REPO,'worktree','add','--detach',str(state),'HEAD')
            git(state,'switch','--orphan',config_value['state_branch'])
            (state/'state.json').write_text('{"schema_version":1,"posts":{}}\n')
            checkpoint(state)
    return media,state

def checkpoint(state):
    # Only marketing intent/result hashes; never Buffer account metadata or keys.
    data=json.loads((state/'state.json').read_text())
    forbidden={'channel_id','buffer_post_id','email','organization_id','channel_name','token','key'}
    def inspect(value):
        if isinstance(value,dict):
            if forbidden.intersection(value):raise Failure('private_field_in_public_state')
            for child in value.values():inspect(child)
        elif isinstance(value,list):
            for child in value:inspect(child)
    inspect(data)
    git(state,'add','state.json')
    dirty=git(state,'diff','--cached','--quiet',allowed=(0,1)).returncode==1
    if dirty:git(state,'commit','-m','Update marketing delivery state')
    git(state,'push','origin','HEAD:refs/heads/'+config()['state_branch'])

def tracked_link(url,service,topic):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='13urgent.fr' or parsed.query:raise Failure('invalid_destination')
    query=urlencode({'utm_source':service,'utm_medium':'organic_social','utm_campaign':'13urgent_presentation','utm_content':topic})
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,query,''))

def topic_for(day,catalogue,epoch):
    topics=catalogue['topics']
    index=(day-date.fromisoformat(epoch)).days%len(topics)
    return topics[index]

def render_topic(topic):
    audience={'donneur_ordre':'Donneurs d’ordre','transporteur':'Transporteurs','particulier':'Particuliers'}[topic['audience']]
    feature=topic['feature']
    icon='document' if any(word in feature for word in ['document','confirmation','lettre','conducteur']) else 'form'
    if 'offre' in feature:icon='offers'
    if topic['audience']=='particulier':icon='boxes'
    labels=[audience,'Le fonctionnement expliqué','13urgent.fr']
    scenes=[]
    for index,title in enumerate(topic['scenes']):
        scenes.append({'eyebrow':'13 URGENT · '+('DÉCOUVREZ LA PLATEFORME' if index==0 else f'ÉTAPE {index} / 4'), 'title':title,'body':'Étude et devis avant engagement.' if topic['audience']=='particulier' else 'Selon votre accès et les conditions de la plateforme.', 'icon':'cta' if index==4 else icon,'labels':labels})
    return {'audience':audience,'url':topic['landing_url'],'caption':topic['tiktok'],'scenes':scenes}

def build_plan(day,topic,video_url,settings):
    posts=[]
    for account in settings['accounts']:
        if day.weekday() not in account['weekdays']:continue
        hour,minute=map(int,account['hour'].split(':'))
        due=datetime(day.year,day.month,day.day,hour,minute,tzinfo=PARIS).astimezone(timezone.utc)
        caption=topic[account['caption_key']].replace(topic['landing_url'],tracked_link(topic['landing_url'],account['service'],topic['id']))
        account_key={'linkedin_founder':'fondateur','linkedin_page':'entreprise','tiktok':'tiktok'}[account['caption_key']]
        posts.append({'id':f'{day:%Y%m%d}-{topic["id"]}-{account_key}-v1','channel_name':account['name'],'service':account['service'],'text':caption,'video_url':video_url,'due_at':due.isoformat().replace('+00:00','Z')})
    return {'schema_version':1,'date':day.isoformat(),'topic':topic['id'],'posts':posts}

def verify_public_media(url):
    for attempt in range(6):
        try:
            request=Request(url,headers={'Range':'bytes=0-63','User-Agent':'13URGENT-marketing/1.0'})
            with urlopen(request,timeout=25) as response:
                head=response.read(64)
                if response.status in (200,206) and head[4:8]==b'ftyp':return
        except Exception:pass
        if attempt<5:time.sleep(5)
    raise Failure('public_video_not_available')

def publish_media(output,day,media):
    settings=config();dest=media/settings['media_prefix']/day.isoformat();dest.mkdir(parents=True,exist_ok=True)
    for name in ['cover.jpg','storyboard.jpg','manifest.json']:
        shutil.copy2(output/name,dest/name)
    videos=list(output.glob('*.mp4'))
    if len(videos)!=1:raise Failure('video_file_count')
    target=dest/videos[0].name
    if target.exists() and target.read_bytes()!=videos[0].read_bytes():
        raise Failure('public_video_already_has_different_content')
    shutil.copy2(videos[0],target)
    relative=dest.relative_to(media)
    git(media,'add',str(relative))
    if git(media,'diff','--cached','--quiet',allowed=(0,1)).returncode==1:
        git(media,'commit','-m','Add daily 13 URGENT presentation video')
        git(media,'push','origin','HEAD:refs/heads/'+settings['media_branch'])
    url='https://raw.githubusercontent.com/13urgent/site/'+settings['media_branch']+'/'+str(target.relative_to(media))
    verify_public_media(url)
    return url

def write_summary(value):
    # This summary is public. Counts and static states only, no account metadata.
    print(json.dumps(value,ensure_ascii=False))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as stream:stream.write('# Marketing 13 URGENT\n\n```json\n'+json.dumps(value,ensure_ascii=False,indent=2)+'\n```\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['probe','publish','preview'],default='probe')
    parser.add_argument('--date',help='Editorial date in Paris; normally tomorrow')
    parser.add_argument('--scheduled',action='store_true')
    args=parser.parse_args()
    settings=config()
    now=datetime.now(PARIS)
    if args.scheduled and now.hour!=8:
        write_summary({'status':'outside_Paris_daily_window','sent_posts':0});return 0
    day=date.fromisoformat(args.date) if args.date else now.date()+timedelta(days=1)
    catalogue=json.loads((ROOT/'content/catalogue.json').read_text())
    validator=load_module('editorial_validator',ROOT/'content/validate_content.py')
    if validator.validate_catalogue(catalogue):raise Failure('editorial_validation_failed')
    topic=topic_for(day,catalogue,settings['topic_epoch'])
    publisher=load_module('buffer_publish',ROOT/'publisher/buffer_publish.py')
    client=publisher.BufferClient(os.environ.get('BUFFER_API_KEY')) if args.mode!='preview' else None
    if args.mode=='probe':
        # Require an unambiguous match for all three approved channels.
        probe_day=day+timedelta(days=(0-day.weekday())%7)
        plan=build_plan(probe_day,topic,'https://13urgent.fr/videos/connection-check.mp4',settings)
        report=publisher.run(client,'probe',plan,REPO/'.runtime/unused-state.json',REPO/'.runtime/probe.json')
        write_summary({'status':'connection_and_authorized_channels_checked','ok':report['ok'],'sent_posts':0});return 0
    output=REPO/'.runtime/output'/day.isoformat()
    renderer=load_module('video_renderer',ROOT/'video/render_daily.py')
    renderer.render(topic['id'],day,output,topic_override=render_topic(topic))
    if args.mode=='preview':
        plan=build_plan(day,topic,'https://13urgent.fr/videos/preview.mp4',settings)
        publisher.validate_plan(plan)
        (output/'preview-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        write_summary({'status':'preview_created','planned_posts':len(plan['posts']),'sent_posts':0});return 0
    # Resolve authorized accounts BEFORE publishing media or changing ledger.
    probe_day=day+timedelta(days=(0-day.weekday())%7)
    probe=build_plan(probe_day,topic,'https://13urgent.fr/videos/connection-check.mp4',settings)
    publisher.run(client,'probe',probe,REPO/'.runtime/unused-state.json',REPO/'.runtime/probe.json')
    media,state=setup_runtime()
    previous=json.loads((state/'state.json').read_text())
    if previous.get('posts'):
        delivery=publisher.verify_delivery(client,state/'state.json',REPO/'.runtime/delivery-report.json',checkpoint=lambda:checkpoint(state))
        write_summary({'status':'previous_deliveries_checked',**delivery['counts'],'scan_complete':delivery['scan_complete']})
    url=publish_media(output,day,media)
    plan=build_plan(day,topic,url,settings)
    report=publisher.run(client,'publish',plan,state/'state.json',REPO/'.runtime/publish-report.json',checkpoint=lambda:checkpoint(state))
    outcomes=report['posts']
    write_summary({'status':'scheduled' if report['ok'] else 'needs_attention','ok':report['ok'],'scheduled':sum(p['status']=='scheduled' for p in outcomes),'already_recorded':sum(p['status']=='already_recorded' for p in outcomes),'attention':sum(p['status'] not in ('scheduled','already_recorded') for p in outcomes),'publication_sent_not_yet_verified':True})
    return 0 if report['ok'] else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        # Provider bodies, identifiers, credentials and tracebacks stay out of logs.
        candidate=str(error)
        code=candidate if (isinstance(error,Failure) or error.__class__.__name__=='SafeFailure') and re.fullmatch('[a-z0-9_]+',candidate) else 'pipeline_step_failed'
        write_summary({'status':'blocked','error':code,'ok':False})
        raise SystemExit(2)

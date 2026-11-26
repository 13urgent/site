#!/usr/bin/env python3
"""Encrypted queue for verified owner-authorized campaigns; no SMTP outside Paris hours."""
from datetime import datetime,timezone
from pathlib import Path
import base64,hashlib,hmac,json,os,subprocess
import commercial_agent as agent
import commercial_hours
import run_campaign


def crypt(raw,password,decrypt=False):
    env={**os.environ,'COMMERCIAL_QUEUE_PASSWORD':password}
    cmd=['openssl','enc','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:COMMERCIAL_QUEUE_PASSWORD']
    if decrypt:cmd.append('-d')
    r=subprocess.run(cmd,input=raw,capture_output=True,env=env,timeout=30)
    if r.returncode:raise agent.CampaignError('campaign_queue_crypto_failed')
    return r.stdout

def mac_key(password):return hashlib.pbkdf2_hmac('sha256',password.encode(),b'13urgent/commercial-queue/auth/v1',200000,32)

def envelope(campaign,password):
    raw=json.dumps(campaign,ensure_ascii=False,sort_keys=True).encode();cid=campaign['campaign_id'];digest=hashlib.sha256(raw).hexdigest();cipher=crypt(raw,password)
    tag=hmac.new(mac_key(password),(cid+'\n'+digest).encode()+cipher,hashlib.sha256).hexdigest()
    return {'version':1,'campaign_id':cid,'payload_sha256':digest,'ciphertext':base64.b64encode(cipher).decode(),'authentication':tag}

def decrypt(value,password):
    if not isinstance(value,dict) or set(value)!={'version','campaign_id','payload_sha256','ciphertext','authentication'} or value['version']!=1:raise agent.CampaignError('campaign_queue_invalid')
    try:cipher=base64.b64decode(value['ciphertext'],validate=True)
    except Exception:raise agent.CampaignError('campaign_queue_invalid')
    if len(cipher)>60000:raise agent.CampaignError('campaign_queue_invalid')
    expected=hmac.new(mac_key(password),(value['campaign_id']+'\n'+value['payload_sha256']).encode()+cipher,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,value['authentication']):raise agent.CampaignError('campaign_queue_authentication_failed')
    raw=crypt(cipher,password,True)
    if hashlib.sha256(raw).hexdigest()!=value['payload_sha256']:raise agent.CampaignError('campaign_queue_digest_failed')
    campaign=json.loads(raw)
    if campaign['campaign_id']!=value['campaign_id']:raise agent.CampaignError('campaign_queue_identity_failed')
    return campaign

def commit(sd,relative,message):
    pipeline=run_campaign.pipeline;pipeline.git(sd,'add','--',relative)
    if pipeline.git(sd,'diff','--cached','--quiet',allowed=(0,1)).returncode==1:pipeline.git(sd,'commit','-m',message)
    pipeline.git(sd,'push','origin','HEAD:refs/heads/'+pipeline.config()['state_branch'])

def store(campaign,sd,password):
    sd=Path(sd);folder=sd/'commercial-queue';folder.mkdir(exist_ok=True);path=folder/(hashlib.sha256(campaign['campaign_id'].encode()).hexdigest()+'.json')
    if path.exists():
        if decrypt(json.loads(path.read_text()),password)!=campaign:raise agent.CampaignError('campaign_queue_content_conflict')
        return path
    path.write_text(json.dumps(envelope(campaign,password)));commit(sd,str(path.relative_to(sd)),'Queue authorized encrypted commercial campaign');return path

def finish(path,sd,held=False):
    sd=Path(sd)
    if held:
        target=path.with_suffix('.held');run_campaign.pipeline.git(sd,'mv',str(path.relative_to(sd)),str(target.relative_to(sd)));commit(sd,str(target.relative_to(sd)),'Hold commercial campaign for delivery review')
    else:
        run_campaign.pipeline.git(sd,'rm',str(path.relative_to(sd)));run_campaign.pipeline.git(sd,'commit','-m','Complete authorized commercial queue entry');run_campaign.pipeline.git(sd,'push','origin','HEAD:refs/heads/'+run_campaign.pipeline.config()['state_branch'])

def process(campaign,sd,password):
    import send_sealed_campaign as sealed
    path=store(campaign,sd,password)
    if datetime.now(timezone.utc)<datetime.fromisoformat(campaign['send_not_before'].replace('Z','+00:00')):return {'status':'queued_for_start_date','contacts':len(campaign['recipients']),'emails_sent':0}
    if not commercial_hours.allowed():return {'status':'queued_for_business_hours','contacts':len(campaign['recipients']),'emails_sent':0}
    rows=sealed.deliver(campaign,Path(sd)/'mail-state.json',password,lambda:run_campaign.checkpoint(sd));result=sealed.summary(rows)
    if any(r['status']=='deferred_business_hours' for r in rows):result['status']='queued_for_business_hours'
    else:finish(path,sd,held=result['status']=='needs_attention')
    return result

def main():
    if not commercial_hours.allowed():print(json.dumps({'status':'deferred_business_hours','emails_sent':0}));return
    password=os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password:raise agent.CampaignError('mail_access_not_connected')
    _,sd=run_campaign.pipeline.setup_runtime();folder=sd/'commercial-queue';paths=sorted(folder.glob('*.json'))[:20] if folder.is_dir() else []
    if paths:
        import monitor_replies
        monitor_replies.monitor(sd/'mail-state.json',password,lambda:run_campaign.checkpoint(sd))
    results=[]
    for path in paths:
        if not commercial_hours.allowed() or len(results)>=2:break
        c=decrypt(json.loads(path.read_text()),password)
        if datetime.now(timezone.utc)<datetime.fromisoformat(c['send_not_before'].replace('Z','+00:00')):continue
        results.append(process(c,sd,password))
    print(json.dumps({'status':'commercial_queue_checked','campaigns':len(results),'results':results}))
if __name__=='__main__':
    try:main()
    except Exception as e:
        code=str(e) if isinstance(e,agent.CampaignError) and __import__('re').fullmatch('[a-z_]+',str(e)) else 'commercial_queue_failed'
        print(json.dumps({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True}));raise SystemExit(2)

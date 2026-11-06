#!/usr/bin/env python3
"""GitHub mail executor; private campaign only comes from an encrypted secret."""
import argparse,json,os,re,sys
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'marketing'))
import pipeline
import commercial_agent as agent

def checkpoint(state_dir):
    path=state_dir/'mail-state.json';data=json.loads(path.read_text())
    # Delivery state is public: prohibit any address, body, subject or credential.
    if '@' in json.dumps(data) or any(key in json.dumps(data) for key in ['"password"','"body"','"subject"','"to"','"company"']):
        raise agent.CampaignError('private_field_in_public_delivery_state')
    pipeline.git(state_dir,'add','mail-state.json')
    if pipeline.git(state_dir,'diff','--cached','--quiet',allowed=(0,1)).returncode==1:
        pipeline.git(state_dir,'commit','-m','Update commercial mail delivery state')
    pipeline.git(state_dir,'push','origin','HEAD:refs/heads/'+pipeline.config()['state_branch'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['probe','send'],default='probe');parser.add_argument('--scheduled',action='store_true');args=parser.parse_args()
    now=datetime.now(ZoneInfo('Europe/Paris'))
    if args.scheduled and (now.weekday()!=0 or now.hour!=8):
        pipeline.write_summary({'status':'outside_Paris_Monday_window','emails_sent':0});return 0
    password=os.environ.get('CONTACT_MAIL_PASSWORD')
    if not password:raise agent.CampaignError('mail_access_not_connected')
    if args.mode=='probe':pipeline.write_summary(agent.probe(password));return 0
    payload=os.environ.get('PROSPECTION_CAMPAIGN_JSON')
    if not payload:raise agent.CampaignError('private_campaign_not_connected')
    campaign=json.loads(payload);agent.campaign_rows(campaign)
    not_before=datetime.fromisoformat(campaign['send_not_before'].replace('Z','+00:00'))
    if not_before.utcoffset() is None:raise agent.CampaignError('timezone_required')
    if now<not_before:
        pipeline.write_summary({'status':'before_campaign_date','emails_sent':0});return 0
    _,state_dir=pipeline.setup_runtime()
    result=agent.run(campaign,state_dir/'mail-state.json',execute=True,password=password,checkpoint=lambda:checkpoint(state_dir))
    counts={}
    for row in result:counts[row['status']]=counts.get(row['status'],0)+1
    issues=any(row['status'] in ('accepted_archive_pending','partial_acceptance','uncertain_do_not_retry','content_conflict') or row.get('recorded_status') in ('intent','accepted_archive_pending','partial_acceptance','uncertain_do_not_retry') for row in result)
    pipeline.write_summary({'status':'needs_attention' if issues else 'campaign_processed','counts':counts,'copies_saved_in_sent':counts.get('accepted_and_archived',0)+counts.get('archive_repaired_without_resend',0),'delivery_to_recipient_not_verified':True})
    return 2 if issues else 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        candidate=str(error)
        code=candidate if error.__class__.__name__ in ('CampaignError','Failure') and re.fullmatch('[a-z0-9_]+',candidate) else ('mail_authentication_failed' if error.__class__.__name__ in ('SMTPAuthenticationError','error') else 'mail_execution_failed')
        pipeline.write_summary({'status':'blocked','error':code,'emails_sent_in_this_step_not_confirmed':True});raise SystemExit(2)

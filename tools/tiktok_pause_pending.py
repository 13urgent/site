"""Move only our future scheduled TikTok posts to draft. Never publishes or deletes."""
import importlib.util,json,hashlib,os,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('buffer_pause',root/'marketing/publisher/buffer_publish.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def pause_known(client,ledger,now):
    channels=[c for c in client.channels() if c['service'].casefold()=='tiktok' and module.normal(c['name'])=='13urgentsite']
    if len(channels)!=1:raise module.SafeFailure('tiktok_identity_not_unique')
    known={r.get('buffer_post_fingerprint'):key for key,r in ledger.get('posts',{}).items() if key.endswith('-tiktok-v1') and r.get('buffer_post_fingerprint')}
    observations,complete=client.verification_posts(channels)
    result={'posts_created':0,'posts_deleted':0,'tiktok_moved_to_draft':0,'tiktok_already_in_draft':0,'linkedin_modified':0,'scan_complete':complete,'records':[]}
    for post in observations:
        key=known.get(hashlib.sha256(post['id'].encode()).hexdigest())
        if not key:continue
        if post['status']=='draft':
            result['tiktok_already_in_draft']+=1;result['records'].append({'ledger_key':key,'status':'draft','already_in_draft':True});continue
        if post['status']!='scheduled':continue
        try:due=datetime.fromisoformat(post['dueAt'].replace('Z','+00:00'))
        except (TypeError,KeyError,ValueError):continue
        if due<=now:continue
        client.query('mutation { editPost(input: { id: '+json.dumps(post['id'])+', saveToDraft: true }) { __typename } }')
        checked=client.post_status(post['id'])
        if checked['provider_status']!='draft':raise module.SafeFailure('tiktok_draft_not_confirmed')
        result['tiktok_moved_to_draft']+=1;result['records'].append({'ledger_key':key,'status':'draft','due_at_before':post['dueAt']})
    return result

def main():
    subprocess.run(['git','fetch','--depth=1','origin','refs/heads/marketing-state'],cwd=root,check=True,capture_output=True,timeout=30)
    raw=subprocess.run(['git','show','FETCH_HEAD:state.json'],cwd=root,check=True,capture_output=True,timeout=20).stdout
    ledger=json.loads(raw);client=module.BufferClient(os.environ.get('BUFFER_API_KEY'))
    result=pause_known(client,ledger,datetime.now(timezone.utc))
    out=root/'.runtime/tiktok-paused.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except Exception as error:
        code=str(error) if isinstance(error,module.SafeFailure) else 'tiktok_pause_unconfirmed'
        print(json.dumps({'status':'tiktok_pause_requires_review','error':code,'posts_created':0,'posts_deleted':0,'modification_result_not_confirmed':True}));sys.exit(2)

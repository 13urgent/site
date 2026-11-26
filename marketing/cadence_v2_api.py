"""Minimal Buffer controls for the owner's two-post daily cadence.

Raw provider identifiers remain in memory; durable records use SHA-256 only.
"""
from datetime import datetime
import hashlib,json
from pathlib import Path
import pipeline

P=pipeline.load_module('cadence_buffer',Path(__file__).parent/'publisher/buffer_publish.py')
LABELS={('linkedin','haeckel hamri'):'founder',('linkedin','chronos'):'company',('tiktok','13urgentsite'):'tiktok'}

def moment(value):
    if not isinstance(value,str):return None
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result if result.utcoffset() is not None else None
    except ValueError:return None

def same_time(a,b):
    a,b=moment(a),moment(b)
    return a is not None and b is not None and abs((a-b).total_seconds())<=1

def hashed(value):return hashlib.sha256(value.encode()).hexdigest()

class Client(P.BufferClient):
    def all_channels(self):
        account=self.query('query { account { organizations { id } } }').get('account')
        if not isinstance(account,dict) or not isinstance(account.get('organizations'),list):raise P.SafeFailure('cadence_account_schema')
        contexts={}
        for org in account['organizations']:
            oid=org.get('id')
            if not isinstance(oid,str):raise P.SafeFailure('cadence_account_schema')
            rows=self.query('query { channels(input:{organizationId:'+json.dumps(oid)+'}) { id name displayName service isDisconnected isLocked isQueuePaused } }').get('channels')
            if not isinstance(rows,list):raise P.SafeFailure('cadence_channel_schema')
            for row in rows:
                roles=set()
                for name in (row.get('name'),row.get('displayName')):
                    if isinstance(name,str):
                        label=P.normal(name)
                        if label=='chronoss':label='chronos'
                        role=LABELS.get((P.normal(row.get('service','')),label))
                        if role:roles.add(role)
                if not roles:continue
                if len(roles)!=1:raise P.SafeFailure('cadence_channel_ambiguous')
                role=next(iter(roles))
                if role in contexts or not isinstance(row.get('id'),str):raise P.SafeFailure('cadence_channel_ambiguous')
                contexts[role]={'role':role,'id':row['id'],'organization':oid,'service':row['service'],
                                'name':{'founder':'Haeckel Hamri','company':'Chronos','tiktok':'13urgentsite'}[role],
                                'ready':not any(row.get(k) for k in ('isDisconnected','isLocked','isQueuePaused'))}
        if not all(role in contexts and contexts[role]['ready'] for role in ('founder','tiktok')):raise P.SafeFailure('cadence_active_channel_not_ready')
        self.contexts=contexts;return contexts

    def channels(self):
        contexts=self.all_channels()
        return [{k:c[k] for k in ('id','name','service')} for role,c in contexts.items() if role in ('founder','tiktok')]

    def scan(self,selection='single'):
        contexts=self.all_channels();groups={};roles={}
        for role,ctx in contexts.items():groups.setdefault(ctx['organization'],[]).append(ctx['id']);roles[ctx['id']]=role
        result=[]
        for oid,ids in groups.items():
            # Always inspect ALL pending posts, separately from bounded history.
            # A growing archive must not block the next month's daily cadence.
            selections=([('scheduled,sending,needs_approval',5,True),('sent,error,draft',3,False)] if selection=='multiple'
                        else [('',3,False)] if selection=='unfiltered'
                        else [('scheduled',5,True),('sending',1,True),('needs_approval',1,True),('sent',1,False),('error',1,False),('draft',1,False)])
            for statuses,pages,strict in selections:
                after=None
                for _ in range(pages):
                    q=('query { posts(first:50,'+('after:'+json.dumps(after)+',' if after else '')
                       +'input:{organizationId:'+json.dumps(oid)+',filter:{channelIds:'+json.dumps(ids)+(',status:['+statuses+']' if statuses else '')+'},sort:[{field:createdAt,direction:desc}]}) '
                       +'{ edges { node { id channelId text status dueAt sentAt schedulingType externalLink assets { source } metadata { __typename ... on TiktokPostMetadata { isAiGenerated } } } } pageInfo { hasNextPage endCursor } } }')
                    data=self.query(q).get('posts')
                    if not isinstance(data,dict) or not isinstance(data.get('edges'),list) or not isinstance(data.get('pageInfo'),dict):raise P.SafeFailure('cadence_calendar_schema')
                    for edge in data['edges']:
                        row=edge.get('node') if isinstance(edge,dict) else None
                        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row.get('channelId') not in roles:raise P.SafeFailure('cadence_calendar_schema')
                        row['role']=roles[row['channelId']];result.append(row)
                    if not data['pageInfo'].get('hasNextPage'):break
                    cursor=data['pageInfo'].get('endCursor')
                    if not isinstance(cursor,str) or not cursor or cursor==after:raise P.SafeFailure('cadence_cursor_invalid')
                    after=cursor
                else:
                    if strict:raise P.SafeFailure('cadence_pending_scan_incomplete')
        return result

    def post(self,post_id):
        row=self.query('query { post(input:{id:'+json.dumps(post_id)+'}) { id status dueAt sentAt schedulingType assets { source } metadata { __typename ... on TiktokPostMetadata { isAiGenerated } } } }').get('post')
        if not isinstance(row,dict) or row.get('id')!=post_id:raise P.SafeFailure('cadence_post_readback_schema')
        return row

    def check_edit_schema(self):
        data=self.query('query { __type(name:"EditPostInput") { inputFields { name } } tiktok:__type(name:"TikTokPostMetadataInput") { inputFields { name } } }')
        edit={v.get('name') for v in (data.get('__type') or {}).get('inputFields',[])}
        ai={v.get('name') for v in (data.get('tiktok') or {}).get('inputFields',[])}
        if not {'id','dueAt','mode','saveToDraft','assets','schedulingType'}.issubset(edit):raise P.SafeFailure('cadence_edit_schema_unavailable')
        if 'isAiGenerated' not in ai:raise P.SafeFailure('cadence_ai_disclosure_unavailable')

    def edit(self,post_id,plan=None,draft=False):
        values=['id:'+json.dumps(post_id)]
        if draft:values.append('saveToDraft:true')
        else:
            values+=['mode:customScheduled','schedulingType:automatic','dueAt:'+json.dumps(plan['due_at'])]
            if plan.get('video_url'):values.append('assets:[{video:{url:'+json.dumps(plan['video_url'])+'}}]')
            if plan['service']=='tiktok':values.append('metadata:{tiktok:{isAiGenerated:true}}')
        q=('mutation { editPost(input:{'+','.join(values)+'}) { __typename ... on PostActionSuccess { post { id status dueAt schedulingType assets { source } metadata { __typename ... on TiktokPostMetadata { isAiGenerated } } } } ... on MutationError { message } } }')
        result=self.query(q).get('editPost')
        if not isinstance(result,dict):raise P.SafeFailure('cadence_edit_result_uncertain')
        if result.get('__typename')!='PostActionSuccess':return {'rejected':True}
        saved=result.get('post')
        if not isinstance(saved,dict) or saved.get('id')!=post_id:raise P.SafeFailure('cadence_edit_result_uncertain')
        return saved

    def create(self,post,channel):
        values=['channelId:'+json.dumps(channel['id']),'text:'+json.dumps(post['text']),'schedulingType:automatic','mode:customScheduled','dueAt:'+json.dumps(post['due_at'])]
        if post.get('video_url'):values.append('assets:[{video:{url:'+json.dumps(post['video_url'])+'}}]')
        if post['service']=='tiktok':values.append('metadata:{tiktok:{isAiGenerated:true}}')
        q=('mutation { createPost(input:{'+','.join(values)+'}) { __typename ... on PostActionSuccess { post { id status dueAt schedulingType metadata { __typename ... on TiktokPostMetadata { isAiGenerated } } } } ... on MutationError { message } } }')
        result=self.query(q).get('createPost')
        if not isinstance(result,dict) or result.get('__typename')!='PostActionSuccess':raise P.SafeFailure('cadence_creation_not_confirmed')
        row=result.get('post')
        if not isinstance(row,dict) or not isinstance(row.get('id'),str):raise P.SafeFailure('cadence_creation_uncertain')
        accepted=row.get('status')=='scheduled' and row.get('schedulingType')=='automatic' and same_time(row.get('dueAt'),post['due_at'])
        ai=(row.get('metadata') or {}).get('isAiGenerated')
        if post['service']=='tiktok' and ai is not True:accepted=False
        return {'status':'scheduled' if accepted else 'provider_not_scheduled','buffer_post_id':row['id'],'provider_status':row.get('status'),'scheduling_type':row.get('schedulingType'),'due_at':row.get('dueAt'),'is_ai_generated':ai}

def desired(row,plan):
    sources=[asset.get('source') for asset in row.get('assets',[]) if isinstance(asset,dict)]
    return (row.get('status')=='scheduled' and row.get('schedulingType')=='automatic'
            and same_time(row.get('dueAt'),plan['due_at']) and plan.get('video_url') in sources
            and (plan['service']!='tiktok' or (row.get('metadata') or {}).get('isAiGenerated') is True))

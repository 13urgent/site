import copy,json,tempfile,unittest
from datetime import date,datetime,timezone
from pathlib import Path
from unittest.mock import patch
import daily_v2 as m
from cadence_v2_api import Client


class FakeClient:
    def __init__(self,rows,mode='ok'):
        self.rows=rows;self.edits=0;self.mode=mode
    def check_edit_schema(self):pass
    def scan(self):return list(self.rows.values())
    def post(self,pid):return self.rows[pid]
    def edit(self,pid,plan=None,draft=False):
        self.edits+=1
        if draft:
            if self.mode!='draft_fail':self.rows[pid]['status']='draft'
            return self.rows[pid]
        if self.mode in ('reject','draft_fail'):return {'rejected':True}
        if self.mode!='timeout_no_change':
            self.rows[pid].update(dueAt=plan['due_at'],schedulingType='automatic',assets=[{'source':plan['video_url']}],metadata={'isAiGenerated':True})
        if self.mode.startswith('timeout'):raise TimeoutError('uncertain')
        return self.rows[pid]


class Tests(unittest.TestCase):
    def setUp(self):
        self.config=m.settings();self.topics=m.catalogue()
    def test_two_posts_per_day_per_network_for_31_days(self):
        plan=m.horizon(date(2026,11,27),31,self.topics,self.config)
        self.assertEqual(len(plan),124);self.assertEqual(len({p['id'] for p in plan}),124)
        self.assertEqual({p['channel_name'] for p in plan},{'Haeckel Hamri','13urgentsite'})
        for offset in range(31):
            day=date(2026,11,27)+m.timedelta(days=offset)
            group=[p for p in plan if m.moment(p['due_at']).astimezone(m.PARIS).date()==day]
            self.assertEqual(len(group),4)
            for service,expected in [('linkedin',['10:00','17:00']),('tiktok',['10:00','19:00'])]:
                self.assertEqual([m.moment(p['due_at']).astimezone(m.PARIS).strftime('%H:%M') for p in group if p['service']==service],expected)
    def test_four_day_rolling_window_is_eight_posts_per_account(self):
        plan=m.horizon(date(2026,11,27),4,self.topics,self.config)
        self.assertEqual(sum(p['service']=='linkedin' for p in plan),8)
        self.assertEqual(sum(p['service']=='tiktok' for p in plan),8)
        self.assertTrue(all(p.get('video_url') for p in plan))
    def test_paris_clock_is_correct_in_summer_and_winter(self):
        winter=m.entry(date(2026,11,27),0,'linkedin',self.topics,self.config)
        summer=m.entry(date(2027,7,5),0,'linkedin',self.topics,self.config)
        self.assertTrue(winter['due_at'].endswith('09:00:00Z'));self.assertTrue(summer['due_at'].endswith('08:00:00Z'))
    def test_approved_old_texts_are_preserved_in_reserved_slots(self):
        for old,plan in m.migration_items(self.topics,self.config):self.assertEqual(plan['text'],old['text'])
    def test_old_moderation_hold_is_archived_and_company_page_removed(self):
        self.assertNotIn('tiktok',self.config['publication_holds'])
        self.assertTrue(self.config['publication_hold_history'])
        self.assertEqual(len(self.config['accounts']),2)
        self.assertTrue(self.config['enabled']);self.assertEqual(self.config['state_branch'],'marketing-state')

    def fixtures(self):
        state={'schema_version':1,'posts':{}};rows={}
        for index,(old,plan) in enumerate(m.migration_items(self.topics,self.config)):
            pid='private-'+str(index);h=m.hashed(pid)
            state['posts'][old['legacy_id']]={'status':'scheduled','buffer_post_fingerprint':h,'fingerprint':'old'}
            rows[pid]={'id':pid,'role':'founder' if plan['service']=='linkedin' else 'tiktok','status':'scheduled','dueAt':old['date']+'T11:15:00Z','text':plan['text'],'assets':[],'schedulingType':'automatic'}
        return state,rows

    def migration(self,mode):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);path=Path(temp.name)/'state.json';state,rows=self.fixtures();path.write_text(json.dumps(state));client=FakeClient(rows,mode)
        def persist(p,value):m.P.atomic_json(p,value)
        return path,client,patch.object(m,'persist',side_effect=persist)

    def test_migration_edits_same_ids_and_replay_does_not_edit_again(self):
        path,client,guard=self.migration('ok')
        with guard:
            report=m.migrate(client,path,self.topics,self.config)
            self.assertEqual(report['edited'],4);self.assertEqual(report['recreated'],0)
            self.assertEqual(client.edits,4)
            self.assertEqual(m.migrate(client,path,self.topics,self.config)['status'],'already_completed')
            self.assertEqual(client.edits,4)
        saved=json.loads(path.read_text());canonical=[r for k,r in saved['posts'].items() if k.startswith(m.PREFIX)]
        self.assertEqual(len(canonical),4)
        self.assertFalse(any('buffer_post_id' in r or 'channel_id' in r for r in saved['posts'].values()))
        self.assertEqual(len({r['buffer_post_fingerprint'] for r in canonical}),4)
    def test_uncertain_edit_readback_can_confirm_without_duplicate(self):
        path,client,guard=self.migration('timeout_changed')
        with guard:
            report=m.migrate(client,path,self.topics,self.config)
            self.assertEqual(report['edited'],4);self.assertEqual(client.edits,4)
    def test_uncertain_edit_not_applied_is_never_blindly_retried(self):
        path,client,guard=self.migration('timeout_no_change')
        with guard:
            with self.assertRaises(m.P.SafeFailure):m.migrate(client,path,self.topics,self.config)
            with self.assertRaises(m.P.SafeFailure):m.migrate(client,path,self.topics,self.config)
        self.assertEqual(client.edits,1)
    def test_failed_cancellation_cannot_create_replacement(self):
        path,client,guard=self.migration('draft_fail')
        with guard,patch.object(m.P,'run') as create:
            with self.assertRaisesRegex(m.P.SafeFailure,'daily2_old_cancellation_not_confirmed'):m.migrate(client,path,self.topics,self.config)
            create.assert_not_called()
    def test_unknown_company_post_is_not_silently_deleted(self):
        path,client,guard=self.migration('ok');client.rows['unknown']={'id':'unknown','role':'company','status':'scheduled','dueAt':'2026-11-29T10:00:00Z'}
        with guard:
            with self.assertRaisesRegex(m.P.SafeFailure,'unknown_company_page_post_requires_review'):m.migrate(client,path,self.topics,self.config)
        self.assertEqual(client.edits,0)

    def test_pending_statuses_are_requested_separately(self):
        client=Client('local-test-only');queries=[]
        def query(text):
            queries.append(text)
            return {'posts':{'edges':[],'pageInfo':{'hasNextPage':False,'endCursor':None}}}
        contexts={'founder':{'organization':'private-org','id':'private-channel'}}
        with patch.object(client,'all_channels',return_value=contexts),patch.object(client,'query',side_effect=query):
            self.assertEqual(client.scan(),[])
        self.assertEqual(len(queries),6)
        self.assertTrue(all('status:['+status+']' in query for status,query in zip(('scheduled','sending','needs_approval','sent','error','draft'),queries)))

    def test_pending_history_is_never_silently_truncated(self):
        client=Client('local-test-only');calls=[]
        def query(text):
            calls.append(text)
            return {'posts':{'edges':[],'pageInfo':{'hasNextPage':True,'endCursor':'cursor-'+str(len(calls))}}}
        contexts={'founder':{'organization':'private-org','id':'private-channel'}}
        with patch.object(client,'all_channels',return_value=contexts),patch.object(client,'query',side_effect=query):
            with self.assertRaisesRegex(m.P.SafeFailure,'cadence_pending_scan_incomplete'):client.scan()
        self.assertEqual(len(calls),5)

if __name__=='__main__':unittest.main()

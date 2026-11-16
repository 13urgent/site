import importlib.util,json,tempfile,unittest,subprocess
from unittest.mock import patch,Mock
from datetime import date,datetime
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('pipeline',Path(__file__).with_name('pipeline.py'))
p=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(p)

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.settings=p.config()
        self.catalogue=json.loads((p.ROOT/'content/catalogue.json').read_text())
        self.topic=self.catalogue['topics'][0]
    def test_paris_schedule_handles_summer_and_winter(self):
        for day,expected in [(date(2026,11,9),'11:15:00+00:00'),(date(2027,7,5),'10:15:00+00:00')]:
            plan=p.build_plan(day,self.topic,'https://13urgent.fr/videos/check.mp4',self.settings)
            founder=next(row for row in plan['posts'] if row['id'].endswith('fondateur-v1'))
            self.assertEqual(datetime.fromisoformat(founder['due_at'].replace('Z','+00:00')).isoformat()[-14:],expected)
    def test_saturday_tiktok_only_and_monday_three_channels(self):
        self.assertEqual([x['service'] for x in p.build_plan(date(2026,11,7),self.topic,'https://13urgent.fr/videos/check.mp4',self.settings)['posts']],['tiktok'])
        monday=p.build_plan(date(2026,11,9),self.topic,'https://13urgent.fr/videos/check.mp4',self.settings)['posts']
        self.assertEqual(len(monday),3);self.assertEqual(len({x['id'] for x in monday}),3)
    def test_topic_rotation_is_repeatable_and_content_link_is_own(self):
        self.assertEqual(p.topic_for(date(2026,11,7),self.catalogue,'2026-11-07')['id'],self.topic['id'])
        self.assertEqual(p.topic_for(date(2026,11,19),self.catalogue,'2026-11-07')['id'],self.topic['id'])
        with self.assertRaises(p.Failure):p.tracked_link('https://external.invalid/','linkedin','topic')
        self.assertIn('utm_source=tiktok',p.tracked_link('https://13urgent.fr/','tiktok','topic'))
    def test_delayed_cron_and_retry_are_allowed_in_winter_and_summer(self):
        for stamp,allowed in [('2026-11-16T06:55:00+00:00',False),
                              ('2026-11-16T08:35:00+00:00',True),
                              ('2026-11-16T10:55:00+00:00',True),
                              ('2027-07-05T05:55:00+00:00',False),
                              ('2027-07-05T06:55:00+00:00',True)]:
            self.assertEqual(p.scheduled_window_open(datetime.fromisoformat(stamp)),allowed)

    def run_existing_day(self,mode,record_status='scheduled',fingerprint_conflict=False):
        # Same canonical IDs are still passed to the publisher, so its fingerprint
        # and quarantine checks remain authoritative. No video is rendered again.
        day=date(2026,11,16)
        topic=p.topic_for(day,self.catalogue,self.settings['topic_epoch'])
        plan=p.build_plan(day,topic,p.expected_media_url(day,topic,self.settings),self.settings)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);state=root/'state';state.mkdir()
            (state/'state.json').write_text(json.dumps({'schema_version':1,'posts':{
                post['id']:{'status':record_status} for post in plan['posts']}}))
            publisher=Mock()
            publisher.run.return_value={'ok':not fingerprint_conflict,'posts':[{'status':'id_conflict' if fingerprint_conflict else 'already_recorded'} for post in plan['posts']]}
            publisher.verify_delivery.return_value={'ok':True,'counts':{'sent':3,'scheduled':0,'errors':0,'uncertain':0},'scan_complete':True}
            validator=Mock();validator.validate_catalogue.return_value=[]
            def module(name,path):
                if name=='editorial_validator':return validator
                if name=='buffer_publish':return publisher
                self.fail('Renderer must not load during verification or a fully recorded retry')
            with patch.object(p,'REPO',root),patch.object(p,'load_module',side_effect=module),patch.object(p,'setup_runtime',return_value=(root/'media',state)),patch.object(p,'write_summary'),patch.object(p,'publish_media') as upload,patch('sys.argv',['pipeline','--mode',mode,'--date',day.isoformat()]):
                result=p.main()
            upload.assert_not_called()
            publisher.verify_delivery.assert_called_once()
            if mode=='verify':
                self.assertEqual([call.args[1] for call in publisher.run.call_args_list],['probe'])
            else:
                self.assertEqual(publisher.run.call_args_list[-1].args[2],plan)
            return result

    def test_completed_retry_uses_same_plan_without_rendering(self):
        self.assertEqual(self.run_existing_day('publish'),0)

    def test_conflicting_retry_is_not_silently_accepted(self):
        self.assertEqual(self.run_existing_day('publish','uncertain',True),2)

    def test_verification_never_publishes_media_or_posts(self):
        self.assertEqual(self.run_existing_day('verify'),0)

    def test_local_git_state_survives_fresh_runner_and_media_unchanged(self):
        def cmd(args):
            return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);remote=root/'remote.git';seed=root/'seed';runner=root/'runner'
            cmd(['git','init','--bare',str(remote)]);cmd(['git','clone',str(remote),str(seed)])
            cmd(['git','-C',str(seed),'config','user.name','test']);cmd(['git','-C',str(seed),'config','user.email','test@example.invalid'])
            cmd(['git','-C',str(seed),'switch','-c','main']);(seed/'index.html').write_text('production unchanged')
            cmd(['git','-C',str(seed),'add','index.html']);cmd(['git','-C',str(seed),'commit','-m','seed']);cmd(['git','-C',str(seed),'push','origin','HEAD:main','HEAD:gh-pages'])
            cmd(['git','clone','-b','main',str(remote),str(runner)])
            old=p.REPO;p.REPO=runner
            try:
                media,state=p.setup_runtime()
                self.assertEqual((media/'index.html').read_text(),'production unchanged')
                data=json.loads((state/'state.json').read_text());data['posts']['test']={'status':'intent','fingerprint':'hash'}
                (state/'state.json').write_text(json.dumps(data));p.checkpoint(state)
                stored=cmd(['git','--git-dir',str(remote),'show','marketing-state:state.json']).stdout
                self.assertEqual(json.loads(stored)['posts']['test']['status'],'intent')
                data['posts']['test']['channel_id']='forbidden';(state/'state.json').write_text(json.dumps(data))
                with self.assertRaises(p.Failure):p.checkpoint(state)
                self.assertEqual(cmd(['git','--git-dir',str(remote),'show','gh-pages:index.html']).stdout,'production unchanged')
            finally:p.REPO=old

if __name__=='__main__':unittest.main()

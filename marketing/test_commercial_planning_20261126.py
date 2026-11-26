import json,unittest
from datetime import datetime,timezone
from pathlib import Path
import commercial_planning_20261126 as m

class Tests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((Path(__file__).parent/'commercial_plan_20261126.json').read_text())
        self.settings=json.loads((Path(__file__).parent/'config.json').read_text())
        self.now=datetime(2026,11,26,14,tzinfo=timezone.utc)
    def test_avoids_automatic_posts_not_created_yet(self):
        plan,changes=m.build_plan(self.plan,[],self.settings,self.now)
        self.assertEqual([v['chosen_paris'][:10] for v in changes],['2026-11-28','2026-12-01','2026-12-03','2026-11-28'])
        self.assertEqual([v['date_adjusted'] for v in changes],[True,True,True,False])
        m.PUBLISHER.validate_plan(plan)
    def test_occupied_slot_is_skipped_and_spacing_is_preserved(self):
        rows=[{'role':'linkedin_founder','post':{'id':'private-buffer','status':'scheduled','dueAt':'2026-11-28T11:15:00Z'}}]
        _,changes=m.build_plan(self.plan,rows,self.settings,self.now)
        self.assertEqual(changes[0]['chosen_paris'][:10],'2026-11-29')
    def test_tiktok_uses_only_explicit_alternative_if_saturday_occupied(self):
        rows=[{'role':'tiktok','post':{'id':'private-buffer','status':'scheduled','dueAt':'2026-11-28T10:00:00Z'}}]
        _,changes=m.build_plan(self.plan,rows,self.settings,self.now)
        self.assertEqual(changes[3]['chosen_paris'][:10],'2026-11-30')
    def test_calendar_report_does_not_expose_queried_id_or_text(self):
        rows=[{'role':'linkedin_founder','post':{'id':'private-buffer','text':'private unpublished body','status':'scheduled','dueAt':'2026-11-28T11:15:00Z'}}]
        report=json.dumps(m.public_calendar(rows,self.now))
        self.assertNotIn('private-buffer',report);self.assertNotIn('private unpublished body',report)
    def test_no_slot_stops_instead_of_scheduling_two_close_posts(self):
        rows=[{'role':'tiktok','post':{'id':'private-'+d,'status':'scheduled','dueAt':d+'T10:00:00Z'}} for d in ['2026-11-28','2026-11-30']]
        with self.assertRaisesRegex(m.PUBLISHER.SafeFailure,'no_spaced_calendar_slot'):m.build_plan(self.plan,rows,self.settings,self.now)

if __name__=='__main__':unittest.main()

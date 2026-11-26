import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent

class RotationTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((ROOT/'rotation_catalogue.json').read_text())
    def test_31_days_have_two_distinct_service_angles(self):
        topics=self.data['topics']
        self.assertEqual(len(topics),62)
        self.assertEqual(len({t['id'] for t in topics}),62)
        self.assertEqual(len({t['hook'] for t in topics}),62)
        self.assertEqual({t['service'] for t in topics},{'urgent','mon_exploit','chronoss'})
        for day in range(31):
            a,b=topics[day*2:day*2+2]
            self.assertEqual((a['day_index'],b['day_index']),(day,day))
            self.assertEqual((a['slot'],b['slot']),(0,1));self.assertNotEqual(a['service'],b['service'])
    def test_reserved_topics_match_four_existing_posts(self):
        self.assertEqual({i:self.data['topics'][i]['service'] for i in [2,3,8,12]},{2:'mon_exploit',3:'urgent',8:'urgent',12:'chronoss'})
    def test_safe_destinations_and_platform_lengths(self):
        for topic in self.data['topics']:
            parsed=urlsplit(topic['cta_url']);self.assertEqual((parsed.scheme,parsed.netloc),('https','13urgent.fr'))
            self.assertIn(parsed.path,['/deposer.html','/mon-exploit.html','/demander-un-devis.html'])
            self.assertLessEqual(len(topic['linkedin']),3000);self.assertLessEqual(len(topic['tiktok']),2200)
    def test_two_particular_drafts_are_integrated_without_new_slots(self):
        included=[t for t in self.data['topics'] if t.get('caption_origin')]
        self.assertEqual(len(included),2)
        self.assertTrue(all(t['service']=='chronoss' and '?service=moving' in t['cta_url'] for t in included))

if __name__=='__main__':unittest.main()

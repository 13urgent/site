import unittest,copy
from unittest.mock import patch
import commercial_queue as q
class QueueTests(unittest.TestCase):
 def test_authenticated_private_round_trip(self):
  c={'campaign_id':'direction-test','recipients':[{'to':'contact@example.test','body':'DONNEES PRIVEES'}]};v=q.envelope(c,'test-password-not-a-real-secret')
  self.assertEqual(q.decrypt(v,'test-password-not-a-real-secret'),c);self.assertNotIn('contact@example.test',str(v));self.assertNotIn('DONNEES PRIVEES',str(v))
  bad={**v,'campaign_id':'different'}
  with self.assertRaisesRegex(q.agent.CampaignError,'authentication_failed'):q.decrypt(bad,'test-password-not-a-real-secret')
 def test_modified_or_wrong_key_cannot_reach_decryption(self):
  v=q.envelope({'campaign_id':'direction-test','recipients':[]},'test-password')
  with self.assertRaisesRegex(q.agent.CampaignError,'authentication_failed'):q.decrypt(v,'different-password')
  v['authentication']='0'*64
  with patch.object(q,'crypt') as crypt:
   with self.assertRaisesRegex(q.agent.CampaignError,'authentication_failed'):q.decrypt(v,'test-password')
   crypt.assert_not_called()
 def test_outside_window_campaign_is_queued_without_deliver(self):
  c={'campaign_id':'direction-test','send_not_before':'2026-01-01T00:00:00+00:00','recipients':[{}]}
  with patch.object(q,'store',return_value='queued') as store,patch('commercial_hours.allowed',return_value=False),patch('send_sealed_campaign.deliver') as deliver:
   r=q.process(c,'/tmp/unused','test');self.assertEqual(r['status'],'queued_for_business_hours');store.assert_called_once();deliver.assert_not_called()

 def test_future_campaign_waits_for_requested_start_date(self):
  c={'campaign_id':'direction-test','send_not_before':'2099-01-01T00:00:00+00:00','recipients':[{}]}
  with patch.object(q,'store',return_value='queued'),patch('send_sealed_campaign.deliver') as deliver:
   r=q.process(c,'/tmp/unused','test');self.assertEqual(r['status'],'queued_for_start_date');deliver.assert_not_called()

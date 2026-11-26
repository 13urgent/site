import unittest
from datetime import datetime,timezone
from unittest.mock import patch
import commercial_hours as h
import send_service_reply as service
class HoursTests(unittest.TestCase):
 def test_effective_tomorrow_winter_and_summer_paris(self):
  for stamp,expected in [('2026-11-26T22:00:00+00:00',True),('2026-11-27T08:59:59+00:00',False),('2026-11-27T09:00:00+00:00',True),('2026-11-27T16:59:59+00:00',True),('2026-11-27T17:00:00+00:00',False),('2027-07-01T08:00:00+00:00',True),('2027-07-01T16:00:00+00:00',False)]:self.assertEqual(h.allowed(datetime.fromisoformat(stamp)),expected,stamp)
 def test_automatic_commercial_reply_held_before_any_network(self):
  payload={'request_id':'direction-ack-test','to':'contact@example.test','subject':'TEST','body':'TEST'}
  with patch('commercial_hours.allowed',return_value=False):
   result=service.deliver(payload,'0'*64,'/tmp/does-not-need-to-exist','test',lambda:None,smtp_factory=lambda:self.fail('no SMTP outside window'),archive_factory=lambda:self.fail('no IMAP outside window'))
  self.assertEqual(result['status'],'deferred_business_hours')

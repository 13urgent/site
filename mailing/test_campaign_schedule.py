from datetime import datetime
import unittest
import run_campaign

class ScheduleTests(unittest.TestCase):
    def test_delayed_monday_is_allowed_and_other_days_are_excluded(self):
        for stamp,allowed in [('2026-11-16T06:37:00+00:00',False),
                              ('2026-11-16T07:37:00+00:00',True),
                              ('2026-11-16T09:15:00+00:00',True),
                              ('2026-11-16T10:37:00+00:00',True),
                              ('2026-11-17T07:37:00+00:00',False),
                              ('2027-07-05T06:37:00+00:00',True),
                              ('2027-07-04T23:59:00+00:00',False)]:
            self.assertEqual(run_campaign.scheduled_send_window_open(datetime.fromisoformat(stamp)),allowed)

if __name__=='__main__':unittest.main()

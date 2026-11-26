"""Owner's commercial sending window, effective 27 November 2026, Paris local time."""
from datetime import datetime,date,timezone,timedelta
from zoneinfo import ZoneInfo
EFFECTIVE=date(2026,11,27)
PARIS=ZoneInfo('Europe/Paris')
def allowed(now=None):
 local=(now or datetime.now(timezone.utc)).astimezone(PARIS)
 return local.date()<EFFECTIVE or 10<=local.hour<18
def deferred():return {'status':'deferred_business_hours','emails_sent':0,'copy_saved_in_sent':False,'timezone':'Europe/Paris'}

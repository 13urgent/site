import hashlib,unittest
from datetime import datetime,timezone
from tiktok_pause_pending import pause_known
class PauseTests(unittest.TestCase):
    def test_only_known_future_scheduled_tiktok_is_moved_to_draft(self):
        calls=[]
        class Client:
            def channels(self):return [{'id':'T','service':'tiktok','name':'13urgentsite'},{'id':'L','service':'linkedin','name':'Chronos'}]
            def verification_posts(self,channels):
                assert channels==[{'id':'T','service':'tiktok','name':'13urgentsite'}]
                return ([{'id':key,'status':state,'dueAt':due} for key,state,due in [('future','scheduled','2030-01-02T17:00:00Z'),('sent','sent','2030-01-02T17:00:00Z'),('unknown','scheduled','2030-01-02T17:00:00Z'),('sending','sending','2030-01-02T17:00:00Z'),('past','scheduled','2020-01-01T17:00:00Z')]],True)
            def query(self,q):calls.append(q);return {'editPost':{'__typename':'PostActionSuccess'}}
            def post_status(self,k):return {'status':'draft'}
        ledger={'posts':{key+'-tiktok-v1':{'buffer_post_fingerprint':hashlib.sha256(key.encode()).hexdigest()} for key in ['future','sent','sending','past']}}
        result=pause_known(Client(),ledger,datetime(2030,1,1,tzinfo=timezone.utc))
        self.assertEqual(result['tiktok_moved_to_draft'],1);self.assertEqual(len(calls),1);self.assertIn('saveToDraft: true',calls[0]);self.assertEqual(result['posts_created'],0);self.assertNotIn('"id"',str(result))
if __name__=='__main__':unittest.main()

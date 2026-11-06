import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import send_linkedin_now as m

class Client:
    def __init__(self,state,timeout=False,status='sent'):
        self.state=state;self.created=0;self.timeout=timeout;self.status=status
    def channels(self):return [{'id':'private-channel-test','name':'haeckel hamri','service':'linkedin'}]
    def query(self,q):
        if q.startswith('mutation'):
            self.created+=1
            saved=json.loads(self.state.read_text())['posts'][m.CAMPAIGN]
            assert saved['status']=='intent'
            assert 'mode: shareNow' in q and 'schedulingType: automatic' in q
            if self.timeout:raise TimeoutError()
            return {'createPost':{'__typename':'PostActionSuccess','post':{'id':'private-post-test','status':'sending','schedulingType':'automatic'}}}
        return {'post':{'status':self.status,'schedulingType':'automatic','sentAt':'2026-11-06T13:00:00Z','externalLink':'https://www.linkedin.com/feed/update/urn:li:activity:public-test?tracking=drop'}}

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)/'state.json';self.state.write_text('{"schema_version":1,"posts":{}}')
    def test_sends_once_and_confirms_actual_sent_status(self):
        client=Client(self.state);checkpoints=[]
        r=m.send(client,self.state,lambda:checkpoints.append(json.loads(self.state.read_text())['posts'][m.CAMPAIGN]['status']),wait=lambda s:None)
        self.assertEqual(r['status'],'sent');self.assertEqual(client.created,1);self.assertEqual(checkpoints[0],'intent')
        self.assertEqual(m.send(client,self.state,lambda:None)['status'],'sent');self.assertEqual(client.created,1)
        self.assertNotIn('private-channel-test',self.state.read_text());self.assertNotIn('private-post-test',self.state.read_text())
        self.assertNotIn('tracking=',r['external_link'])
    def test_checkpoint_failure_stops_before_creation(self):
        client=Client(self.state)
        def fail():raise RuntimeError('checkpoint')
        with self.assertRaises(RuntimeError):m.send(client,self.state,fail)
        self.assertEqual(client.created,0)
    def test_timeout_does_not_create_again(self):
        client=Client(self.state,timeout=True)
        with self.assertRaises(m.PUBLISHER.SafeFailure):m.send(client,self.state,lambda:None)
        with self.assertRaises(m.PUBLISHER.SafeFailure):m.send(client,self.state,lambda:None)
        self.assertEqual(client.created,1)
    def test_processing_is_not_reported_as_sent(self):
        client=Client(self.state,status='sending')
        r=m.send(client,self.state,lambda:None,wait=lambda s:None,max_polls=2)
        self.assertEqual(r['status'],'processing');self.assertEqual(client.created,1)
    def test_foreign_or_nonpublic_links_are_not_exposed(self):
        for url in ['http://linkedin.com/posts/a','https://evil.invalid/posts/a','https://www.linkedin.com/login?session=secret','https://u:p@www.linkedin.com/posts/a']:
            self.assertIsNone(m.public_link(url))

if __name__=='__main__':unittest.main()

import copy
from datetime import datetime, timezone
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from buffer_publish import BufferClient, SafeFailure, run, validate_plan, verify_delivery


NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
POST = {'id': '2026-11-06-founder', 'channel_name': 'Haeckel Hamri', 'service': 'linkedin',
        'text': 'Découvrez 13 URGENT.\nhttps://13urgent.fr/',
        'video_url': 'https://13urgent.fr/videos/marketing/2026-11-06.mp4',
        'due_at': '2026-11-06T18:00:00+01:00'}
CHANNEL = {'id': 'channel-test', 'name': 'Haeckel Hamri', 'service': 'linkedin'}


class FakeClient:
    def __init__(self, state, outcome=None):
        self.calls = 0
        self.state = state
        self.outcome = outcome

    def channels(self):
        return [CHANNEL]

    def create(self, post, channel):
        self.calls += 1
        saved = json.loads(self.state.read_text())
        assert saved['posts'][post['id']]['status'] == 'intent'
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome or {'status': 'scheduled', 'buffer_post_id': 'post-test', 'due_at': post['due_at']}


class Response(io.BytesIO):
    status = 200
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'state.json'
        self.report = Path(self.tmp.name) / 'report.json'
        self.plan = {'posts': [copy.deepcopy(POST)]}

    def call(self, client, **kwargs):
        return run(client, 'publish', self.plan, self.state, self.report, now=NOW, **kwargs)

    def test_intent_before_mutation_and_rerun_no_duplicate(self):
        client = FakeClient(self.state)
        checkpoints = []
        result = self.call(client, checkpoint=lambda: checkpoints.append(json.loads(self.state.read_text())['posts'][POST['id']]['status']))
        self.assertTrue(result['ok'])
        self.assertEqual(checkpoints, ['intent', 'scheduled'])
        self.assertEqual(client.calls, 1)
        state = json.loads(self.state.read_text())
        self.assertNotIn('channel_id', state['posts'][POST['id']])
        self.assertNotIn('buffer_post_id', state['posts'][POST['id']])
        self.assertEqual(len(state['posts'][POST['id']]['buffer_post_fingerprint']), 64)
        persisted = self.state.read_text() + self.report.read_text()
        self.assertNotIn('channel-test', persisted)
        self.assertNotIn('post-test', persisted)
        self.assertNotIn('Haeckel Hamri', persisted)
        self.call(client)
        self.assertEqual(client.calls, 1)

    def test_timeout_is_quarantined_and_never_retried(self):
        client = FakeClient(self.state, SafeFailure('buffer_network_error'))
        self.assertFalse(self.call(client)['ok'])
        self.assertEqual(json.loads(self.state.read_text())['posts'][POST['id']]['status'], 'uncertain')
        self.assertFalse(self.call(client)['ok'])
        self.assertEqual(client.calls, 1)

    def test_checkpoint_failure_prevents_mutation(self):
        client = FakeClient(self.state)
        def fail():
            raise RuntimeError('No remote persistence')
        with self.assertRaisesRegex(SafeFailure, 'state_checkpoint_failed'):
            self.call(client, checkpoint=fail)
        self.assertEqual(client.calls, 0)
        self.assertEqual(json.loads(self.state.read_text())['posts'][POST['id']]['status'], 'intent')

    def test_checkpoint_failure_after_success_leaves_remote_intent(self):
        client = FakeClient(self.state)
        remote = []
        def checkpoint():
            snapshot = json.loads(self.state.read_text())
            if snapshot['posts'][POST['id']]['status'] == 'scheduled':
                raise RuntimeError('network gone after creation')
            remote[:] = [snapshot]
        with self.assertRaises(SafeFailure):
            self.call(client, checkpoint=checkpoint)
        self.assertEqual(client.calls, 1)
        self.state.write_text(json.dumps(remote[0]))
        self.assertFalse(self.call(client)['ok'])
        self.assertEqual(client.calls, 1)

    def test_changed_id_content_is_blocked(self):
        client = FakeClient(self.state)
        self.call(client)
        self.plan['posts'][0]['text'] = 'Different content'
        self.assertFalse(self.call(client)['ok'])
        self.assertEqual(client.calls, 1)

    def test_probe_cannot_mutate_or_write_ledger(self):
        client = FakeClient(self.state)
        result = run(client, 'probe', self.plan, self.state, self.report)
        self.assertTrue(result['ok'])
        self.assertEqual(client.calls, 0)
        self.assertFalse(self.state.exists())

    def test_wrong_channel_and_duplicate_plan_rejected(self):
        self.plan['posts'][0]['channel_name'] = 'Another Company'
        with self.assertRaises(SafeFailure):
            validate_plan(self.plan)
        with self.assertRaises(SafeFailure):
            validate_plan({'posts': [POST, POST]})

    def test_past_due_does_not_publish(self):
        self.plan['posts'][0]['due_at'] = '2026-11-05T18:00:00+01:00'
        client = FakeClient(self.state)
        self.assertFalse(self.call(client)['ok'])
        self.assertEqual(client.calls, 0)

    def test_tiktok_requires_owned_video(self):
        post = {**POST, 'channel_name': '13urgentsite', 'service': 'tiktok', 'video_url': ''}
        with self.assertRaises(SafeFailure):
            validate_plan({'posts': [post]})
        post['video_url'] = 'https://external.example/video.mp4'
        with self.assertRaises(SafeFailure):
            validate_plan({'posts': [post]})

    def test_transport_headers_and_mutation_shape(self):
        requests = []
        def opener(request, timeout):
            requests.append(request)
            self.assertEqual(request.headers['Authorization'], 'Bearer test-not-a-secret')
            self.assertEqual(timeout, 35)
            return Response({'data': {'createPost': {'__typename': 'PostActionSuccess', 'post': {'id': 'p', 'dueAt': POST['due_at'], 'status': 'scheduled', 'schedulingType': 'automatic', 'sentAt': None}}}})
        client = BufferClient('test-not-a-secret', opener=opener)
        result = client.create(POST, CHANNEL)
        self.assertEqual(result['status'], 'scheduled')
        self.assertEqual(result['provider_status'], 'scheduled')
        self.assertEqual(result['scheduling_type'], 'automatic')
        query = json.loads(requests[0].data)['query']
        for fragment in ['schedulingType: automatic', 'mode: customScheduled', 'assets: [{ video:', 'PostActionSuccess']:
            self.assertIn(fragment, query)

    def test_timeout_and_provider_errors_do_not_leak_key(self):
        for failing in [lambda *a, **k: (_ for _ in ()).throw(TimeoutError('sensitive body')),
                        lambda *a, **k: (_ for _ in ()).throw(HTTPError('https://api.buffer.com', 401, 'sensitive body', {}, None))]:
            client = BufferClient('never-print-me', opener=failing)
            with self.assertRaises(SafeFailure) as caught:
                client.query('query { account { organizations { id } } }')
            self.assertNotIn('sensitive', str(caught.exception))
            self.assertNotIn('never-print-me', str(caught.exception))

    def test_graphql_error_blocks_success(self):
        client = BufferClient('test-key', opener=lambda *a, **k: Response({'errors': [{'message': 'private error'}], 'data': {'createPost': {}}}))
        with self.assertRaisesRegex(SafeFailure, '^buffer_graphql_error$'):
            client.create(POST, CHANNEL)

    def test_notification_or_draft_is_not_automatic_schedule(self):
        for status, scheduling in [('draft', 'automatic'), ('scheduled', 'notification'), ('needs_approval', 'automatic')]:
            client = BufferClient('test-key', opener=lambda *a, **k: Response({'data': {'createPost': {'__typename': 'PostActionSuccess', 'post': {'id': 'p', 'dueAt': POST['due_at'], 'status': status, 'schedulingType': scheduling}}}}))
            self.assertEqual(client.create(POST, CHANNEL)['status'], 'provider_not_scheduled')

    def test_read_post_status_is_read_only_and_contains_no_id(self):
        queries = []
        def opener(request, timeout):
            queries.append(json.loads(request.data)['query'])
            return Response({'data': {'post': {'status': 'sent', 'schedulingType': 'automatic', 'dueAt': POST['due_at'], 'sentAt': '2026-11-06T17:00:03Z'}}})
        result = BufferClient('test-key', opener=opener).post_status('raw-private-id')
        self.assertEqual(result['provider_status'], 'sent')
        self.assertNotIn('raw-private-id', json.dumps(result))
        self.assertTrue(queries[0].startswith('query { post(input:'))

    def test_due_at_equivalent_offset_and_wrong_due_at(self):
        for due, expected in [('2026-11-06T17:00:00.000Z', 'scheduled'), ('2026-11-06T17:00:01Z', 'scheduled'), ('2026-11-07T17:00:00Z', 'provider_not_scheduled')]:
            client = BufferClient('test-key', opener=lambda *a, **k: Response({'data': {'createPost': {'__typename': 'PostActionSuccess', 'post': {'id': 'p', 'dueAt': due, 'status': 'scheduled', 'schedulingType': 'automatic'}}}}))
            self.assertEqual(client.create(POST, CHANNEL)['status'], expected)

    def test_verification_marks_known_sent_and_error_without_raw_ids(self):
        known_sent = hashlib.sha256(b'known-sent').hexdigest()
        known_error = hashlib.sha256(b'known-error').hexdigest()
        self.state.write_text(json.dumps({'schema_version': 1, 'posts': {
            'one': {'status': 'scheduled', 'buffer_post_fingerprint': known_sent},
            'two': {'status': 'scheduled', 'buffer_post_fingerprint': known_error}}}))
        class Reader:
            def channels(self):
                return [CHANNEL]
            def verification_posts(self, channels):
                return [
                    {'id': 'known-sent', 'status': 'sent', 'schedulingType': 'automatic', 'sentAt': '2026-11-06T17:00:03Z'},
                    {'id': 'known-error', 'status': 'error', 'schedulingType': 'automatic'},
                    {'id': 'not-our-post', 'status': 'sent', 'schedulingType': 'automatic'}], True
        checkpoints = []
        report = verify_delivery(Reader(), self.state, self.report, checkpoint=lambda: checkpoints.append(True))
        self.assertEqual(report['counts'], {'scheduled': 0, 'sent': 1, 'errors': 1, 'uncertain': 0})
        self.assertEqual(report['records_matched'], 2)
        self.assertEqual(checkpoints, [True])
        self.assertFalse(report['ok'])
        self.assertNotIn('known-sent', self.state.read_text() + self.report.read_text())
        self.assertNotIn('channel-test', self.state.read_text() + self.report.read_text())

    def test_verification_pagination_is_capped_and_read_only(self):
        queries = []
        def opener(request, timeout):
            query = json.loads(request.data)['query']; queries.append(query)
            return Response({'data': {'posts': {'edges': [{'node': {'id': 'private-'+str(len(queries)), 'status': 'sent', 'schedulingType': 'automatic'}}],
                                              'pageInfo': {'hasNextPage': True, 'endCursor': 'cursor-'+str(len(queries))}}}})
        client = BufferClient('test-key', opener=opener)
        client._organization_by_channel = {'channel-test': 'private-org'}
        posts, complete = client.verification_posts([CHANNEL])
        self.assertEqual(len(queries), 5)
        self.assertEqual(len(posts), 5)
        self.assertFalse(complete)
        self.assertTrue(all(query.startswith('query { posts(first: 20,') for query in queries))
        self.assertTrue(all('channelIds: ["channel-test"]' in query for query in queries))
        self.assertFalse(any('mutation' in query for query in queries))

    def test_verification_checkpoint_failure_does_not_trigger_mutation(self):
        self.state.write_text(json.dumps({'schema_version': 1, 'posts': {'one': {'status': 'scheduled', 'buffer_post_fingerprint': hashlib.sha256(b'p').hexdigest()}}}))
        class Reader:
            def channels(self): return [CHANNEL]
            def verification_posts(self, channels):
                return [{'id': 'p', 'status': 'sent', 'schedulingType': 'automatic'}], True
        def fail(): raise RuntimeError('checkpoint unavailable')
        with self.assertRaisesRegex(SafeFailure, '^state_checkpoint_failed$'):
            verify_delivery(Reader(), self.state, self.report, checkpoint=fail)


if __name__ == '__main__':
    unittest.main()

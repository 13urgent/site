import hashlib
import json
import unittest

import diagnose_visibility as diagnostic


class VisibilityTests(unittest.TestCase):
    def test_only_public_network_urls_with_appropriate_path_are_kept(self):
        self.assertEqual(diagnostic.public_url('https://www.linkedin.com/feed/update/urn:li:123?tracking=x#test', 'post'),
                         'https://www.linkedin.com/feed/update/urn:li:123')
        self.assertEqual(diagnostic.public_url('www.tiktok.com/@owner', 'profile'), 'https://www.tiktok.com/@owner')
        self.assertEqual(diagnostic.public_url('https://fr.linkedin.com/posts/owner-example', 'post'),
                         'https://fr.linkedin.com/posts/owner-example')
        self.assertEqual(diagnostic.public_url('https://www.tiktok.com/@owner/video/12345', 'post'),
                         'https://www.tiktok.com/@owner/video/12345')
        for url in ('https://evil.test/posts/a', 'https://www.linkedin.com.evil.test/posts/a',
                    'https://secret@www.linkedin.com/posts/a', 'https://www.linkedin.com:443/posts/a',
                    'http://www.linkedin.com/posts/a', 'https://www.linkedin.com/login',
                    'https://www.tiktok.com/@owner', 'https://www.linkedin.com/posts/a\n'):
            self.assertIsNone(diagnostic.public_url(url, 'post'))

    def test_errors_are_classified_without_returning_provider_text(self):
        self.assertEqual(diagnostic.error_bucket({'message': 'token expired personal@example.test'}), 'account_authorization')
        self.assertEqual(diagnostic.error_bucket({'message': 'Video processing failed'}), 'media_or_processing')
        self.assertIsNone(diagnostic.error_bucket(None))

    def test_only_known_ids_are_queried_and_raw_identifiers_never_reported(self):
        class Client:
            def channels(self):
                return [{'id': 'PRIVATE-CHANNEL', 'label': 'tiktok', 'profile_url': 'https://www.tiktok.com/@owner',
                         'disconnected': False, 'locked': False, 'queue_paused': False}]
            def verification_posts(self, channels):
                return [{'id': 'PRIVATE-POST'}, {'id': 'UNRELATED-POST'}], True
            def query(self, query):
                self.last_query = query
                return {'post': {'channelId': 'PRIVATE-CHANNEL', 'status': 'sent', 'schedulingType': 'automatic',
                                 'sentAt': '2026-11-10T10:00:00Z', 'dueAt': None,
                                 'externalLink': 'https://www.tiktok.com/@owner/video/12345', 'error': None}}
        client = Client()
        state = {'schema_version': 1, 'posts': {'known-post': {'buffer_post_fingerprint': hashlib.sha256(b'PRIVATE-POST').hexdigest()},
                                              'missing-post': {'buffer_post_fingerprint': '0' * 64}}}
        report = diagnostic.diagnose(client, state)
        self.assertNotIn('UNRELATED-POST', client.last_query)
        self.assertNotIn('PRIVATE-', json.dumps(report))
        self.assertEqual(report['posts'][0]['target'], 'tiktok')
        self.assertFalse(report['posts'][0]['public_visibility_confirmed'])
        self.assertFalse(report['posts'][1]['matched'])
        self.assertEqual(report['new_posts_created'], 0)

    def test_channel_identity_uses_static_labels_and_surfaces_disconnection(self):
        class Client(diagnostic.VisibilityClient):
            def query(self, query):
                if 'account {' in query:
                    return {'account': {'organizations': [{'id': 'PRIVATE-ORG'}]}}
                return {'channels': [{'id': 'PRIVATE-CHANNEL', 'name': 'opaque-handle', 'displayName': 'CHRONOSS',
                                      'service': 'linkedin', 'externalLink': 'https://www.linkedin.com/company/example/',
                                      'isDisconnected': True, 'isLocked': False, 'isQueuePaused': False},
                                     {'id': 'OTHER-PRIVATE-CHANNEL', 'name': 'Unapproved', 'service': 'linkedin'}]}
        channels = Client('test-not-a-secret').channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]['label'], 'linkedin_company')
        self.assertTrue(channels[0]['disconnected'])


if __name__ == '__main__':
    unittest.main()

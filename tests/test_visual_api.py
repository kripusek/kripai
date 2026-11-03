"""Prawdziwe API i SQLite, inference zastąpione tylko w testach kontraktu."""
import unittest
from unittest.mock import patch
from uuid import uuid4
from app import main,visual
from tests import test_native


class VisualAPITests(unittest.TestCase):
    def setUp(self):
        self.case=test_native.APITests('test_login_csrf_logout_and_cookie_flags');self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.client=self.case.client

    def test_status_auth_prepare_owner_csrf_and_redacted_failure(self):
        from scripts import setup_visual
        with patch.object(setup_visual,'installed',return_value=None):
            result=self.client.get('/api/v1/visual/status')
            self.assertEqual(result.status_code,200);self.assertFalse(result.json()['installed'])
            self.assertEqual(result.json()['dimensions'],768)
        with patch.object(setup_visual,'prepare',side_effect=ValueError('private file path not for UI')):
            result=self.client.post('/api/v1/visual/prepare')
            self.assertEqual(result.status_code,503);self.assertNotIn('private',result.text)
        with patch.object(setup_visual,'prepare') as prepare:
            self.assertEqual(self.client.post('/api/v1/visual/prepare',headers={'X-CSRF-Token':''}).status_code,403)
            prepare.assert_not_called()
        self.case.post('/auth/logout')
        self.assertEqual(self.client.get('/api/v1/visual/status').status_code,401)
        self.assertEqual(self.client.post('/api/v1/visual/search',json={'query':'test','attachment_ids':[str(uuid4())]}).status_code,401)

    def test_search_validation_and_session_checked_after_retrieval(self):
        body={'query':'niebieskie koło','attachment_ids':[str(uuid4())]}
        with patch.object(visual,'retrieve',return_value=[{'attachment_id':body['attachment_ids'][0],'filename':'test.png','page':1,'distance':.1}]) as retrieve:
            result=self.client.post('/api/v1/visual/search',json=body)
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['items'][0]['page'],1)
            self.assertEqual(retrieve.call_args.args[2],'niebieskie koło')
            for invalid in [dict(body,attachment_ids=[]),dict(body,attachment_ids=[str(uuid4())]*6),dict(body,query='x'*501),dict(body,token='not allowed')]:
                self.assertEqual(self.client.post('/api/v1/visual/search',json=invalid).status_code,422)
        def revoke(*args):
            from app.db import connect
            with connect() as conn:conn.execute('UPDATE sessions SET revoked_at=now()')
            return []
        with patch.object(visual,'retrieve',side_effect=revoke):
            self.assertEqual(self.client.post('/api/v1/visual/search',json=body).status_code,401)

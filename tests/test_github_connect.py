"""Kreator: prawdziwy Windows DPAPI, konto i sieć kontrolowane."""
import json
import os
import unittest
from unittest.mock import patch
from app import config,github_connect as wizard
from app.integrations import ADAPTERS
from app.network import ToolError
from test_native import DataCase
import test_native

class GithubConnectTests(DataCase):
    def fetch(self,url,token=None):
        return {'data':json.dumps({'login':'fixture-user'} if url.endswith('/user') else {}).encode()}

    def test_failed_connection_or_backup_preserves_previous_configuration(self):
        path=config.DATA/'github.json';path.write_text('previous')
        with patch.object(wizard,'fetch',side_effect=ToolError('tool_remote_denied')):
            with self.assertRaises(ToolError):wizard.connect(['owner/repo'],'fixture-only')
        self.assertEqual(path.read_text(),'previous')
        with patch.object(wizard,'fetch',side_effect=self.fetch),patch.object(wizard,'protect',return_value='encrypted'),patch.object(wizard.shutil,'copyfile',side_effect=OSError('disk')):
            with self.assertRaises(OSError):wizard.connect(['owner/repo'],'fixture-only')
        self.assertEqual(path.read_text(),'previous');self.assertFalse(list(config.DATA.glob('github-*.tmp')))

    def test_revoke_before_save_and_invalid_repo_never_changes_disk(self):
        calls=[0]
        def check():
            calls[0]+=1
            if calls[0]>1:raise ToolError('login_required')
        with patch.object(wizard,'fetch',side_effect=self.fetch),patch.object(wizard,'protect',return_value='encrypted'):
            with self.assertRaises(ToolError):wizard.connect(['owner/repo'],'fixture-only',check=check)
        self.assertFalse((config.DATA/'github.json').exists())
        with patch.object(wizard,'fetch',side_effect=AssertionError('network')):
            for repos,write in [(['bad'],False),(['owner/repo'],True),([],False)]:
                with self.assertRaises(ToolError):wizard.connect(repos,'fixture-only',write)

    def test_native_dpapi_connect_and_disconnect_backup(self):
        if os.name!='nt':self.skipTest('DPAPI requires Windows')
        with patch.object(wizard,'fetch',side_effect=self.fetch):
            result=wizard.connect(['Owner/Repo'],'fixture-token-only')
        self.assertEqual(result['login'],'fixture-user')
        self.assertNotIn('fixture-token-only',(config.DATA/'github.json').read_text())
        self.assertEqual(ADAPTERS['github'].token('owner/repo'),'fixture-token-only')
        wizard.disconnect();self.assertFalse(ADAPTERS['github'].status()['configured'])
        self.assertEqual(len(list((config.BACKUPS/'credentials').glob('*.json'))),1)

class GithubConnectAPITests(unittest.TestCase):
    def setUp(self):
        base=test_native.APITests('runTest');self.addCleanup(base.doCleanups);base.setUp();self.post,self.client=base.post,base.client
    def test_connect_auth_csrf_validation_and_no_secret_in_response(self):
        body={'repositories':['owner/repo'],'token':'fixture-token-only','write':False}
        with patch.object(wizard,'fetch',side_effect=lambda url,token=None:{'data':b'{"login":"fixture-user"}'}),patch.object(wizard,'protect',return_value='encrypted'):
            response=self.post('/integrations/github/connect',body)
            self.assertEqual(response.status_code,200,response.text);self.assertNotIn(body['token'],response.text)
        self.assertEqual(self.client.post('/api/v1/integrations/github/connect',json=body,headers={'X-CSRF-Token':'bad'}).status_code,403)
        bad=self.post('/integrations/github/connect',dict(body,token='x'*513));self.assertEqual(bad.status_code,422);self.assertNotIn('xxx',bad.text)
        self.assertEqual(self.post('/integrations/github/disconnect').status_code,204)
        self.client.cookies.clear();self.assertEqual(self.post('/integrations/github/connect',body).status_code,401)

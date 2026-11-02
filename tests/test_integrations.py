import base64
import json
import tempfile
import unittest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch
from app import config, network, tools
from app.integrations import ADAPTERS


class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','DPAPI requires Windows')
    def test_real_dpapi_current_user(self):
        command="Add-Type -AssemblyName System.Security; [Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes('test-fixture-only'),$null,[Security.Cryptography.DataProtectionScope]::CurrentUser))"
        encrypted=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
        with tempfile.TemporaryDirectory() as folder,patch.object(config,'DATA',Path(folder)):
            (Path(folder)/'github.json').write_text(json.dumps({'repositories':['owner/private'],'credential':encrypted}))
            self.assertEqual(ADAPTERS['github'].token('owner/private'),'test-fixture-only')

    def test_tree_file_and_repository_boundary(self):
        scope=network.policy('kripusek/kripai',False,True)
        with tempfile.TemporaryDirectory() as folder, patch.object(config,'DATA',Path(folder)):
            with patch.object(network,'fetch',return_value={'data':json.dumps([{'path':'README.md','type':'file','size':5}]).encode()}):
                self.assertIn('README.md',network.execute('github_read',{'repository':'kripusek/kripai','section':'tree','path':''},scope)['text'])
            with patch.object(network,'fetch',return_value={'data':json.dumps({'encoding':'base64','content':base64.b64encode(b'hello').decode()}).encode()}):
                self.assertEqual(network.execute('github_read',{'repository':'kripusek/kripai','section':'file','path':'README.md'},scope)['text'],'hello')
            with patch.object(network,'fetch',side_effect=AssertionError('no request')):
                for repo,path in [('other/private','README.md'),('kripusek/kripai','../secret'),('kripusek/kripai','/secret')]:
                    with self.assertRaises(network.ToolError):network.execute('github_read',{'repository':repo,'section':'file','path':path},scope)

    def test_configuration_allowlist_and_safe_status(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config,'DATA',Path(folder)):
            adapter=ADAPTERS['github'];self.assertFalse(adapter.status()['configured'])
            (Path(folder)/'github.json').write_text(json.dumps({'repositories':['owner/private'],'credential':'encrypted'}))
            self.assertIsNone(adapter.token('other/repo'))
            self.assertNotIn('encrypted',json.dumps(adapter.status()))
            with self.assertRaises(network.ToolError):adapter.token('owner/private')
            (Path(folder)/'github.json').write_text('{}')
            self.assertEqual(adapter.status()['error'],'integration_configuration_invalid')

    def test_registry_schema_includes_paths(self):
        self.assertEqual(tools.GithubRead(repository='owner/repo',section='tree').path,'')

    def test_adapter_dispatch_and_real_public_child(self):
        from app.integrations import read
        with self.assertRaises(network.ToolError):read('shell',{}, {})
        scope=network.policy('',False,False)
        with self.assertRaises(network.ToolError):tools.read('github_read',{'repository':'owner/repo','section':'tree'},scope,lambda:None)

    def test_credentials_never_follow_redirect(self):
        from test_tools import Connection,Response
        Connection.requests=[];Connection.responses=[Response(status=302,headers={'Location':'https://example.org'})]
        with patch.object(network,'resolve',return_value='8.8.8.8'),patch.object(network,'PinnedHTTPS',Connection):
            with self.assertRaises(network.ToolError):network.fetch('https://api.github.com/repos/o/r',token='fixture')
        self.assertEqual(len(Connection.requests),1)
        with self.assertRaises(network.ToolError):network.fetch('https://example.org',token='fixture')

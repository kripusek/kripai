"""Prawdziwy SQLite; GitHub zastąpiony kontrolowanym API, bez zewnętrznego zapisu."""
import base64
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import config,github_changes as changes
from app.integrations import ADAPTERS
from app.network import ToolError
import test_native

class GithubChangesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=patch.object(config,'DATA',Path(self.temp.name));self.data.start();self.addCleanup(self.data.stop)
        self.calls=[];self.head='a'*40
        self.scope={'github':True,'owner':'owner-one','repositories':[changes.WRITE_REPOSITORY],
                    'github_files':{changes.WRITE_REPOSITORY+'/README.md':'blob-before'}}
        self.args={'repository':changes.WRITE_REPOSITORY,'title':'Improve README','body':'Clarify setup',
                   'files':[{'path':'README.md','content':'# Improved\n'}]}
    def api(self,repo,suffix,method='GET',payload=None):
        self.calls.append((suffix,method,payload))
        if suffix=='':return {'default_branch':'main'}
        if suffix=='git/ref/heads/main':return {'object':{'sha':self.head}}
        if suffix.startswith('contents/'):return {'type':'file','sha':'blob-before','encoding':'base64','content':base64.b64encode(b'# Old\n').decode()}
        if suffix.startswith('git/commits/') and method=='GET':return {'tree':{'sha':'old-tree'}}
        if suffix.startswith('git/trees/') and method=='GET':return {'tree':[{'path':'README.md','mode':'100755'}]}
        if suffix=='git/trees':return {'sha':'new-tree'}
        if suffix=='git/commits':return {'sha':'new-commit'}
        if suffix=='git/refs':return {'ref':payload['ref']}
        if suffix=='pulls':return {'html_url':'https://github.com/'+repo+'/pull/1'}
        raise AssertionError(suffix)
    def create(self):
        with patch.object(changes,'api',side_effect=self.api):
            return changes.draft(copy.deepcopy(self.args),copy.deepcopy(self.scope))['draft_id']
    def permission(self):
        return patch.object(ADAPTERS['github'],'configuration',return_value={'write_repositories':[changes.WRITE_REPOSITORY]})
    def test_draft_is_local_owner_isolated_and_diff_preserves_file_mode(self):
        did=self.create();self.assertTrue(all(method=='GET' for _,method,_ in self.calls))
        self.assertEqual(changes.list_drafts('other'),[])
        draft=changes.list_drafts('owner-one')[0]
        self.assertEqual(draft['id'],did);file=draft['proposal']['files'][0]
        self.assertIn('-# Old',file['diff']);self.assertIn('+# Improved',file['diff']);self.assertEqual(file['mode'],'100755')
    def test_publish_new_branch_pr_idempotent_and_never_updates_main(self):
        did=self.create()
        with self.permission(),patch.object(ADAPTERS['github'],'token',return_value='fixture'),patch.object(changes,'api',side_effect=self.api):
            result=changes.publish(did,'owner-one');count=len(self.calls)
            self.assertEqual(changes.publish(did,'owner-one'),result);self.assertEqual(len(self.calls),count)
        posts=[(path,payload) for path,method,payload in self.calls if method!='GET']
        self.assertEqual([p for p,_ in posts],['git/trees','git/commits','git/refs','pulls'])
        self.assertEqual(posts[2][1]['ref'],'refs/heads/kripai/'+did)
        self.assertEqual(posts[3][1]['base'],'main')
    def test_missing_permission_other_owner_and_changed_base_do_not_write(self):
        did=self.create()
        with patch.object(changes,'api',side_effect=AssertionError('network')):
            with self.assertRaises(ToolError):changes.publish(did,'other')
            with self.assertRaises(ToolError):changes.publish(did,'owner-one')
        self.head='b'*40;self.calls=[]
        with self.permission(),patch.object(ADAPTERS['github'],'token',return_value='fixture'),patch.object(changes,'api',side_effect=self.api):
            with self.assertRaises(ToolError):changes.publish(did,'owner-one')
        self.assertTrue(all(method=='GET' for _,method,_ in self.calls))
    def test_lost_response_keeps_unknown_and_blocks_retry(self):
        did=self.create()
        def failing(*args,**kwargs):
            if args[1]=='pulls':raise ToolError('github_network_failed')
            return self.api(*args,**kwargs)
        with self.permission(),patch.object(ADAPTERS['github'],'token',return_value='fixture'),patch.object(changes,'api',side_effect=failing):
            with self.assertRaises(ToolError):changes.publish(did,'owner-one')
            count=len(self.calls)
            with self.assertRaises(ToolError):changes.publish(did,'owner-one')
            self.assertEqual(len(self.calls),count)
        self.assertEqual(changes.list_drafts('owner-one')[0]['state'],'outcome_unknown')
    def test_path_repo_unread_file_and_stale_blob_are_denied(self):
        for path in ['../secret','.github/workflows/run.yml','private.key','README.md']:
            args=copy.deepcopy(self.args);args['files'][0]['path']=path
            scope=copy.deepcopy(self.scope);scope['github_files']={}
            with patch.object(changes,'api',side_effect=AssertionError('network')):
                with self.assertRaises(ToolError):changes.draft(args,scope)
        self.scope['github_files'][changes.WRITE_REPOSITORY+'/README.md']='changed'
        with patch.object(changes,'api',side_effect=self.api):
            with self.assertRaises(ToolError):changes.draft(copy.deepcopy(self.args),self.scope)

    def test_transport_blocks_redirects_and_unimplemented_mutations(self):
        from test_tools import Connection,Response
        Connection.requests=[];Connection.responses=[Response(status=302,headers={'Location':'https://evil.example'})]
        with patch.object(ADAPTERS['github'],'token',return_value='fixture'),patch.object(changes,'resolve',return_value='8.8.8.8'),patch.object(changes,'PinnedHTTPS',Connection):
            with self.assertRaises(ToolError):changes.api(changes.WRITE_REPOSITORY,'git/trees','POST',{'tree':[]})
        self.assertEqual(len(Connection.requests),1)
        with patch.object(changes,'resolve',side_effect=AssertionError('network')):
            for repo,path,method in [(changes.WRITE_REPOSITORY,'git/refs/heads/main','PATCH'),('other/repo','pulls','POST'),(changes.WRITE_REPOSITORY,'issues','POST')]:
                with self.assertRaises(ToolError):changes.api(repo,path,method,{})

class GithubChangesAPITests(unittest.TestCase):
    def test_session_csrf_and_owner_bound_publication(self):
        from uuid import uuid4
        base=test_native.APITests('runTest');self.addCleanup(base.doCleanups);base.setUp()
        client=base.client
        self.assertEqual(client.get('/api/v1/integrations/github/drafts').status_code,200)
        url='/api/v1/integrations/github/drafts/'+str(uuid4())+'/publish'
        with patch.object(changes,'publish',return_value={'url':'https://github.com/owner/repo/pull/1'}) as publish:
            self.assertEqual(client.post(url,headers={'X-CSRF-Token':'bad'}).status_code,403)
            publish.assert_not_called()
            self.assertEqual(base.post(url.removeprefix('/api/v1'),{}).status_code,200);self.assertEqual(publish.call_count,1)
        client.cookies.clear()
        self.assertEqual(client.get('/api/v1/integrations/github/drafts').status_code,401)

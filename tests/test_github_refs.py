"""Gałęzie/tagi/commity: tylko odczyt, bez uprawnień do propozycji z innej rewizji."""
import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
from app import config,network,tools,github_changes
from test_web_search import Reply

class GithubRefsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        context=patch.object(config,'DATA',Path(temp.name));context.start();self.addCleanup(context.stop)
        self.scope=network.policy('kripusek/kripai',github=True)
    def response(self,data):return {'data':json.dumps(data).encode()}
    def test_file_readme_and_tree_reference_is_encoded_and_sources_keep_it(self):
        file={'encoding':'base64','content':base64.b64encode(b'# Historical README').decode(),'sha':'a'*40,'path':'README.md'}
        for section in ['file','readme','tree']:
            with self.subTest(section=section),patch.object(network,'fetch',return_value=self.response([{'path':'README.md','type':'file'}] if section=='tree' else file)) as fetch:
                result=network.execute('github_read',{'repository':'kripusek/kripai','section':section,'path':'README.md' if section=='file' else '','ref':'feature/zażółć'},self.scope)
                self.assertEqual(parse_qs(urlsplit(fetch.call_args.args[0]).query),{'ref':['feature/zażółć']})
                self.assertIn('feature%2F',result['url']);self.assertEqual(result['ref'],'feature/zażółć')
        with patch.object(network,'fetch',return_value=self.response(file)) as fetch:
            result=network.execute('github_read',{'repository':'kripusek/kripai','section':'readme'},self.scope)
            self.assertNotIn('?',fetch.call_args.args[0]);self.assertTrue(result['url'].endswith('#readme'))
    def test_branch_listing_limit_and_bad_remote_data(self):
        rows=[{'name':'branch-'+str(i),'commit':{'sha':'b'*40}} for i in range(21)]
        with patch.object(network,'fetch',return_value=self.response(rows)) as fetch:
            result=network.execute('github_read',{'repository':'kripusek/kripai','section':'branches'},self.scope)
        self.assertEqual(result['count'],20);self.assertTrue(result['truncated']);self.assertNotIn('document',result)
        self.assertIn('per_page=21',fetch.call_args.args[0])
        for bad in [{},[{'name':'main','commit':{'sha':'invalid'}}],[None]]:
            with patch.object(network,'fetch',return_value=self.response(bad)),self.assertRaises(network.ToolError):
                network.execute('github_read',{'repository':'kripusek/kripai','section':'branches'},self.scope)
    def test_bad_refs_and_other_repo_are_denied_before_network(self):
        with patch.object(network,'fetch',side_effect=AssertionError('no network')):
            for ref in ['../secret','main?token=x','main\n','/branch','main\\file','a//b',None,'x'*201]:
                with self.subTest(ref=ref),self.assertRaises(network.ToolError):network.execute('github_read',{'repository':'kripusek/kripai','section':'file','ref':ref},self.scope)
            for section in ['issues','branches']:
                with self.assertRaises(network.ToolError):network.execute('github_read',{'repository':'kripusek/kripai','section':section,'ref':'main'},self.scope)
            with self.assertRaises(network.ToolError):network.execute('github_read',{'repository':'other/private','section':'tree','ref':'main'},self.scope)
    def test_explicit_ref_file_cannot_authorize_edit_draft(self):
        scope=network.policy('kripusek/kripusek-autoexec',github=True);scope['owner']='fixture-owner';calls=[0]
        class Client:
            def post(self,path,json):
                if path.endswith('apply-template'):return Reply({'prompt':'p'})
                if path.endswith('tokenize'):return Reply({'tokens':[1]})
                calls[0]+=1
                name,args=('github_read',{'repository':'kripusek/kripusek-autoexec','section':'file','path':'README.md','ref':'old-tag'}) if calls[0]==1 else ('github_draft',{'repository':'kripusek/kripusek-autoexec','title':'Proposal','body':'','files':[{'path':'README.md','content':'Changed'}]})
                return Reply({'choices':[{'message':{'tool_calls':[{'id':str(calls[0]),'type':'function','function':{'name':name,'arguments':__import__('json').dumps(args)}}]}}]})
        def read(name,args,current,check):
            if name=='github_draft':return github_changes.draft(args,current)
            return {'url':'https://github.com/kripusek/kripusek-autoexec/blob/old-tag/README.md','title':'Old README','text':'Old','document':'Old','sha':'c'*40,'truncated':False}
        with patch.object(tools,'read',side_effect=read):results=tools.plan(Client(),[],scope,lambda:None,lambda *a:None)
        self.assertNotIn('editable',results[0]);self.assertEqual(results[-1]['error'],'github_read_file_first')

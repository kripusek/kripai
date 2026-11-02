"""Przegląd PR: odczyt, spójne SHA, jawna niepełność i ochrona nazw sekretów."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import config,network,tools
from app.integrations import ADAPTERS

class GithubPullTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        context=patch.object(config,'DATA',Path(temp.name));context.start();self.addCleanup(context.stop)
        self.scope=network.policy('owner/repo',github=True)
        self.meta={'number':1,'state':'open','title':'Review fixture','body':'Description','head':{'sha':'a'*40},'base':{'sha':'b'*40},'changed_files':1,'draft':False,'merged':False}
        self.file={'filename':'app/main.py','status':'modified','patch':'@@ -1 +1 @@\n-old\n+new'}
    def wrap(self,data):return {'data':json.dumps(data).encode()}
    def read(self,**args):return network.execute('github_read',dict(repository='owner/repo',section='pull',number=1,**args),self.scope)
    def test_open_pr_list_uses_real_numbers_and_marks_limit(self):
        rows=[dict(self.meta,number=i) for i in range(1,12)]
        with patch.object(network,'fetch',return_value=self.wrap(rows)) as fetch:
            result=network.execute('github_read',{'repository':'owner/repo','section':'pulls'},self.scope)
        self.assertEqual(result['count'],10);self.assertTrue(result['truncated']);self.assertIn('#1 [open]',result['text'])
        self.assertIn('state=open',fetch.call_args.args[0]);self.assertNotIn('document',result)
    def test_stable_pr_has_patches_snapshot_and_read_only_source(self):
        with patch.object(network,'fetch',side_effect=[self.wrap(self.meta),self.wrap([self.file]),self.wrap(self.meta)]) as fetch:
            result=self.read()
        self.assertEqual(fetch.call_count,3);self.assertIn('+new',result['document'])
        self.assertEqual(result['head_sha'],'a'*40);self.assertEqual(result['base_sha'],'b'*40)
        self.assertFalse(result['truncated']);self.assertEqual(result['url'],'https://github.com/owner/repo/pull/1')
        self.assertEqual(result['text_patch_files'],1);self.assertNotIn('editable',result)
    def test_changed_head_or_base_rejects_inconsistent_snapshot(self):
        for key in ['head','base']:
            later=copy.deepcopy(self.meta);later[key]['sha']='c'*40
            with self.subTest(key=key),patch.object(network,'fetch',side_effect=[self.wrap(self.meta),self.wrap([self.file]),self.wrap(later)]),self.assertRaises(network.ToolError) as exc:self.read()
            self.assertEqual(exc.exception.code,'github_reference_changed')
    def test_partial_large_binary_and_sensitive_renames_are_explicit(self):
        meta=dict(self.meta,changed_files=25,body='long '*500)
        files=[dict(self.file,patch='x'*7000),{'filename':'image.png','status':'added'},{'filename':'.env.production','status':'added','patch':'fixture-sensitive'},{'filename':'config.txt','previous_filename':'.env','status':'renamed','patch':'fixture-sensitive'}]
        with patch.object(network,'fetch',side_effect=[self.wrap(meta),self.wrap(files),self.wrap(meta)]):result=self.read()
        self.assertTrue(result['truncated']);self.assertEqual(result['omitted_sensitive_files'],2)
        self.assertEqual(result['text_patch_files'],1);self.assertEqual(result['processed_files'],4)
        self.assertNotIn('fixture-sensitive',result['document']);self.assertIn('Brak tekstowego diff',result['document'])
    def test_missing_files_and_api_size_failure_do_not_claim_full_diff(self):
        for payload in [self.wrap([]),network.ToolError('tool_response_too_large')]:
            with patch.object(network,'fetch',side_effect=[self.wrap(self.meta),payload,self.wrap(self.meta)]):result=self.read()
            self.assertTrue(result['truncated']);self.assertEqual(result['processed_files'],0)
        self.assertEqual(result['diff_error'],'tool_response_too_large')
    def test_repo_number_ref_and_sensitive_files_denied_before_network(self):
        with patch.object(network,'fetch',side_effect=AssertionError('no network')):
            for number in [0,-1,True,1.5,'1',2147483648]:
                with self.subTest(number=number),self.assertRaises(network.ToolError):network.execute('github_read',{'repository':'owner/repo','section':'pull','number':number},self.scope)
            with self.assertRaises(network.ToolError):network.execute('github_read',{'repository':'other/private','section':'pull','number':1},self.scope)
            for path in ['.env','keys/private.pem','.env.production','settings/llm.key','store.sqlite3']:
                with self.subTest(path=path),self.assertRaises(network.ToolError) as exc:network.execute('github_read',{'repository':'owner/repo','section':'file','path':path},self.scope)
                self.assertEqual(exc.exception.code,'github_sensitive_path_denied')
        with patch.object(tools.subprocess,'Popen',side_effect=AssertionError('no worker')),self.assertRaises(network.ToolError):tools.read('github_read',{'repository':'owner/repo','section':'pull','number':'1'},self.scope,lambda:None)
    def test_private_token_only_in_transport_never_in_result(self):
        with patch.object(ADAPTERS['github'],'token',return_value='fixture-private-token'),patch.object(network,'fetch',side_effect=[self.wrap(self.meta),self.wrap([self.file]),self.wrap(self.meta)]) as fetch:
            result=self.read()
        self.assertNotIn('fixture-private-token',json.dumps(result))
        for call in fetch.call_args_list:
            self.assertTrue(call.args[0].startswith('https://api.github.com/repos/owner/repo/'))
            self.assertEqual(call.kwargs,{'token':'fixture-private-token'})

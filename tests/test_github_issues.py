"""Zgłoszenia GitHub: komentarze, zmiany metadanych, limity i brak uprawnień zapisu."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import config,network,tools

class IssueTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        context=patch.object(config,'DATA',Path(temp.name));context.start();self.addCleanup(context.stop)
        self.scope=network.policy('owner/repo',github=True)
        self.meta={'number':7,'state':'open','title':'Bug fixture','body':'Reproduction','comments':1,'updated_at':'2026-11-03T00:00:00Z','labels':[{'name':'bug'}]}
        self.comment={'id':17,'body':'Try this fix','user':{'login':'contributor'},'updated_at':'2026-11-03T00:00:00Z'}
    def wrap(self,data):return {'data':json.dumps(data).encode()}
    def read(self,**args):return network.execute('github_read',dict(repository='owner/repo',section='issue',number=7,**args),self.scope)
    def test_issue_body_and_comment_have_canonical_readonly_sources(self):
        meta=dict(self.meta,html_url='file:///secret',comments_url='https://evil.invalid')
        with patch.object(network,'fetch',side_effect=[self.wrap(meta),self.wrap([self.comment]),self.wrap(meta)]) as fetch:result=self.read()
        self.assertEqual(fetch.call_count,3);self.assertIn('/issues/7/comments?per_page=11',fetch.call_args_list[1].args[0]);self.assertIn('Try this fix',result['document']);self.assertIn('contributor',result['document'])
        self.assertEqual(result['url'],'https://github.com/owner/repo/issues/7');self.assertEqual(result['comment_urls'],['https://github.com/owner/repo/issues/7#issuecomment-17']);self.assertFalse(result['truncated']);self.assertNotIn('editable',result);self.assertNotIn('evil.invalid',result['document'])
    def test_issue_list_filters_pull_requests_without_claiming_complete_empty_list(self):
        rows=[dict(self.meta,number=n,pull_request={}) for n in range(1,22)]
        with patch.object(network,'fetch',return_value=self.wrap(rows)):result=network.execute('github_read',{'repository':'owner/repo','section':'issues'},self.scope)
        self.assertEqual(result['count'],0);self.assertEqual(result['omitted_pull_requests'],21);self.assertTrue(result['truncated']);self.assertIn('porcji',result['text'])
        rows=[dict(self.meta,number=n) for n in range(1,13)]
        with patch.object(network,'fetch',return_value=self.wrap(rows)):result=network.execute('github_read',{'repository':'owner/repo','section':'issues'},self.scope)
        self.assertEqual(result['count'],10);self.assertTrue(result['truncated']);self.assertIn('#1 [open]',result['text'])
    def test_metadata_change_rejects_mixed_read(self):
        for field,value in [('comments',2),('body','Edited'),('title','Changed'),('state','closed'),('updated_at','2026-11-03T01:00:00Z'),('labels',[])]:
            with self.subTest(field=field),patch.object(network,'fetch',side_effect=[self.wrap(self.meta),self.wrap([self.comment]),self.wrap(dict(self.meta,**{field:value}))]),self.assertRaises(network.ToolError) as error:self.read()
            self.assertEqual(error.exception.code,'github_issue_changed')
    def test_body_comments_and_labels_are_explicitly_partial(self):
        meta=dict(self.meta,body='x'*5000,comments=20,labels=[{'name':'tag'+str(n)} for n in range(9)])
        comments=[dict(self.comment,id=n,body='y'*2000,user=None) for n in range(1,12)]
        with patch.object(network,'fetch',side_effect=[self.wrap(meta),self.wrap(comments),self.wrap(meta)]):result=self.read()
        self.assertTrue(result['truncated']);self.assertEqual(result['processed_comments'],10);self.assertEqual(result['total_comments'],20);self.assertNotIn('x'*4001,result['document']);self.assertNotIn('y'*1501,result['document']);self.assertIn('autor niedostępny',result['document']);self.assertIn('bez transakcyjnej migawki',result['scope_note'])
    def test_large_comments_api_does_not_erase_issue_body(self):
        with patch.object(network,'fetch',side_effect=[self.wrap(self.meta),network.ToolError('tool_response_too_large'),self.wrap(self.meta)]):result=self.read()
        self.assertTrue(result['truncated']);self.assertEqual(result['comments_error'],'tool_response_too_large');self.assertIn('Reproduction',result['document']);self.assertEqual(result['processed_comments'],0)
    def test_permissions_failures_are_not_reported_as_empty_comments(self):
        with patch.object(network,'fetch',side_effect=[self.wrap(self.meta),network.ToolError('tool_remote_denied')]),self.assertRaises(network.ToolError) as error:self.read()
        self.assertEqual(error.exception.code,'tool_remote_denied')
    def test_pr_number_invalid_number_ref_path_and_foreign_repo_denied(self):
        with patch.object(network,'fetch',return_value=self.wrap(dict(self.meta,pull_request={}))) as fetch,self.assertRaises(network.ToolError) as error:self.read()
        self.assertEqual(error.exception.code,'github_issue_is_pull_request');self.assertEqual(fetch.call_count,1)
        with patch.object(network,'fetch',side_effect=AssertionError('no HTTP')):
            for args in [{'number':0},{'number':True},{'number':'7'},{'ref':'main'},{'path':'file.md'},{'repository':'outside/private'}]:
                parameters=dict(repository='owner/repo',section='issue',number=7);parameters.update(args)
                with self.subTest(args=args),self.assertRaises(network.ToolError):network.execute('github_read',parameters,self.scope)
        with patch.object(tools.subprocess,'Popen',side_effect=AssertionError('no worker')),self.assertRaises(network.ToolError):tools.read('github_read',{'repository':'owner/repo','section':'issue','number':'7'},self.scope,lambda:None)
    def test_malformed_metadata_comments_and_counts_rejected(self):
        for comments in [[dict(self.comment,id=True)],[self.comment,self.comment],[dict(self.comment,body={})],[dict(self.comment,user=42)]]:
            with self.subTest(comments=comments),patch.object(network,'fetch',side_effect=[self.wrap(self.meta),self.wrap(comments),self.wrap(self.meta)]),self.assertRaises(network.ToolError):self.read()
        for meta in [dict(self.meta,comments=True),dict(self.meta,number=8),dict(self.meta,title={}),dict(self.meta,labels='bad')]:
            with self.subTest(meta=meta),patch.object(network,'fetch',return_value=self.wrap(meta)),self.assertRaises(network.ToolError):self.read()
    def test_closed_issue_and_no_comments_are_complete(self):
        meta=dict(self.meta,state='closed',comments=0,body=None)
        with patch.object(network,'fetch',side_effect=[self.wrap(meta),self.wrap([]),self.wrap(meta)]):result=self.read()
        self.assertFalse(result['truncated']);self.assertEqual(result['total_comments'],0);self.assertIn('State: closed',result['document'])

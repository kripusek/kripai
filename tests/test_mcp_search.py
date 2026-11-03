"""Wyszukiwanie nazw przez prawdziwy MCP, ograniczenia i zakres bieżącej prośby."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import config,mcp_files,tools
from app.network import ToolError,policy
from scripts import setup_mcp_filesystem as setup
import test_native,test_mcp_files

class SearchTests(unittest.TestCase):
    setUp=test_mcp_files.FilesTests.setUp
    code=test_mcp_files.FilesTests.code
    def test_literal_query_and_original_request_only(self):
        self.assertEqual(mcp_files.search_query(' RAPORT ','Znajdź raport'), 'RAPORT')
        for query in ['*','**','../secret','a/b','x\n.md','..','a?b','a'*81]:self.code('mcp_files_query_invalid',mcp_files.search_query,query)
        self.code('tool_resource_not_authorized',mcp_files.search_query,'private','Znajdź raport')
        scope=tools.bind_integrations(policy('Znajdź raport',mcp=True))
        with patch.object(tools.subprocess,'Popen',side_effect=AssertionError('no spawn')):
            for query in ['private','**']:
                with self.assertRaises(ToolError):tools.read('mcp_files',{'action':'search','query':query},scope,lambda:None)
    def test_search_budget_size_and_depth(self):
        for index in range(1001):(self.root/(str(index)+'.md')).touch()
        self.code('mcp_files_search_limit',mcp_files.search_budget,self.root)
        deep=self.base/'deep';deep.mkdir();cursor=deep
        for _ in range(7):cursor=cursor/'sub';cursor.mkdir()
        self.code('mcp_files_search_limit',mcp_files.search_budget,deep)
    def test_real_windows_junction_denies_recursive_search(self):
        if os.name!='nt':self.skipTest('junction wymaga Windows')
        outside=self.base/'outside';outside.mkdir();link=self.root/'linked'
        result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(outside)],capture_output=True)
        if result.returncode:self.skipTest('brak możliwości utworzenia junction')
        try:self.code('mcp_files_search_links',mcp_files.search_budget,self.root)
        finally:link.rmdir()
    def test_results_are_relative_filtered_and_explicitly_limited(self):
        paths=[]
        for index in range(25):
            path=self.root/('Raport '+str(index)+'.txt');path.write_text('PRIVATE CONTENT NOT A SEARCH EXCERPT');paths.append(str(path))
        (self.root/'Raport.key').write_text('fixture');paths.append(str(self.root/'Raport.key'))
        data=mcp_files.search_result('\n'.join(paths),mcp_files.settings(),'rApOrT',self.id)
        self.assertEqual(data['matched_documents'],25);self.assertEqual(len(data['paths']),20);self.assertTrue(data['truncated']);self.assertEqual(data['omitted_entries'],1)
        self.assertNotIn(str(self.root),json.dumps(data));self.assertNotIn('PRIVATE CONTENT',json.dumps(data));self.assertIn('query=rApOrT',data['url'])
        self.code('mcp_files_path_denied',mcp_files.search_result,str(self.base/'Raport.txt'),mcp_files.settings(),'raport',self.id)
        self.code('mcp_protocol_invalid',mcp_files.search_result,'relative.txt',mcp_files.settings(),'relative',self.id)
        empty=mcp_files.search_result('No matches found',mcp_files.settings(),'none',self.id);self.assertEqual(empty['paths'],[]);self.assertFalse(empty['truncated'])
    def test_real_search_and_followup_read_only_grant_actual_results(self):
        if not setup.node() or not setup.installed():self.skipTest('opcjonalny Node/serwer nieprzygotowany')
        (self.root/'docs').mkdir();name='docs/Raport gęślą.txt';(self.root/name).write_text('MCP_SEARCH_FOUND',encoding='utf-8')
        (self.root/'.private').mkdir();(self.root/'.private/Raport.txt').write_text('NEVER_EXPOSE')
        scope=tools.bind_integrations(policy('Znajdź raport i go przeczytaj',mcp=True))
        from test_web_search import Reply
        requests=[0]
        class Client:
            def post(self,path,json):
                if path.endswith('apply-template'):return Reply({'prompt':'p'})
                if path.endswith('tokenize'):return Reply({'tokens':[1]})
                requests[0]+=1
                args={'action':'search','query':'RAPORT'} if requests[0]==1 else {'action':'read','path':name}
                return Reply({'choices':[{'message':{'tool_calls':[{'id':str(requests[0]),'type':'function','function':{'name':'mcp_files','arguments':__import__('json').dumps(args)}}]}}]})
        results=tools.plan(Client(),[],scope,lambda:None,lambda *a:None)
        self.assertEqual(results[-1]['text'],'MCP_SEARCH_FOUND');self.assertIn(name,results[0]['text']);self.assertNotIn('paths',results[0]);self.assertEqual(scope['local_documents'],[])
        self.assertNotIn('NEVER_EXPOSE',json.dumps(results));self.assertNotIn(str(self.root),json.dumps(results))
    def test_scope_change_and_invalid_search_shape_deny_before_node(self):
        with patch.object(mcp_files,'StdioClient',side_effect=AssertionError('no Node')):
            self.code('mcp_files_scope_changed',mcp_files.execute,'search','','old','raport')
            self.code('tool_arguments_invalid',mcp_files.execute,'search','docs',self.id,'raport')
            self.code('tool_arguments_invalid',mcp_files.execute,'read','guide.md',self.id,'raport')

class SearchAPITests(unittest.TestCase):
    def test_actual_search_endpoint_unicode_source_auth_and_old_root(self):
        if not setup.node() or not setup.installed():self.skipTest('opcjonalny Node/serwer nieprzygotowany')
        base=test_native.APITests('runTest');self.addCleanup(base.doCleanups);base.setUp()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'docs').mkdir();name='docs/Gęślą raport.md';(root/name).write_text('ok',encoding='utf-8')
            identity=mcp_files.configure(str(root),'Test')['root_id'];route='/api/v1/integrations/mcp-files/search'
            response=base.client.get(route,params={'root':identity,'query':'GĘŚLĄ'});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['paths'],[name])
            source=base.client.get(response.json()['url']);self.assertEqual(source.status_code,200);self.assertEqual(source.json()['paths'],[name])
            self.assertEqual(base.client.get(route,params={'root':identity,'query':'**'}).json()['error']['code'],'mcp_files_query_invalid')
            mcp_files.configure(str(root),'New');self.assertEqual(base.client.get(route,params={'root':identity,'query':'raport'}).status_code,404)
            base.client.cookies.clear();self.assertEqual(base.client.get(route,params={'root':identity,'query':'raport'}).status_code,401)

"""MCP stdio, prawdziwe procesy i pliki; inference osobno oznaczone jako atrapa."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from app import config,tools,mcp_client,mcp_documents
from app.network import ToolError,policy
import test_native

class McpDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'docs').mkdir();(self.root/'README.md').write_text('Dokument testowy. Zażółć.',encoding='utf-8')
        (self.root/'docs/guide.md').write_text('Poradnik',encoding='utf-8')
    def test_catalog_read_utf8_and_limits(self):
        self.assertIn('docs/guide.md',mcp_documents.catalog(self.root)['paths'])
        self.assertIn('Zażółć',mcp_documents.document(self.root,'README.md')['text'])
        (self.root/'docs/.hidden.md').write_text('hidden');self.assertNotIn('docs/.hidden.md',mcp_documents.catalog(self.root)['paths'])
        (self.root/'docs/large.md').write_text('x'*13000)
        self.assertTrue(mcp_documents.document(self.root,'docs/large.md')['truncated'])
        (self.root/'docs/large.md').write_bytes(b'x'*(mcp_documents.MAX_BYTES+1))
        with self.assertRaises(ToolError):mcp_documents.document(self.root,'docs/large.md')
    def test_traversal_credentials_binary_and_unknown_directory_denied(self):
        for path in ['../README.md','/README.md','docs/../README.md','llm.key','app/config.py','tools-tmp/test.md','docs/.secret.md','docs/a.md:stream','docs\\guide.md','docs/%2e%2e/a.md']:
            with self.subTest(path=path),self.assertRaises(ToolError):mcp_documents.document(self.root,path)
        (self.root/'docs/binary.md').write_bytes(b'abc\0def')
        with self.assertRaises(ToolError):mcp_documents.document(self.root,'docs/binary.md')
    def test_symlink_outside_document_root_denied(self):
        target=self.root/'outside.md';target.write_text('outside')
        try:(self.root/'docs/link.md').symlink_to(target)
        except OSError:self.skipTest('Windows account cannot create symlinks')
        self.assertNotIn('docs/link.md',mcp_documents.catalog(self.root)['paths'])
        with self.assertRaises(ToolError):mcp_documents.document(self.root,'docs/link.md')
    @unittest.skipUnless(os.name=='nt','Windows junction')
    def test_windows_junction_is_not_followed(self):
        target=self.root/'private';target.mkdir();(target/'secret.md').write_text('fixture')
        link=self.root/'docs/junction'
        result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0)
        try:
            self.assertNotIn('docs/junction/secret.md',mcp_documents.catalog(self.root)['paths'])
            with self.assertRaises(ToolError):mcp_documents.document(self.root,'docs/junction/secret.md')
        finally:link.rmdir()

class McpClientTests(unittest.TestCase):
    def test_real_server_handshake_call_and_write_tool_rejected(self):
        client=mcp_client.StdioClient()
        try:
            client.initialize();response=client.request('tools/call',{'name':'read_document','arguments':{'path':'README.md'}})
            self.assertTrue(json.loads(response['content'][0]['text'])['text'])
            denied=client.request('tools/call',{'name':'write_document','arguments':{'path':'README.md'}})
            self.assertTrue(denied['isError'])
        finally:client.close()
        self.assertIsNotNone(client.process.poll());self.assertIsNone(client.job.handle)
    def test_bad_protocol_wrong_id_oversized_frame_and_disconnect(self):
        commands=["print('not json',flush=True)","import json;print(json.dumps({'jsonrpc':'2.0','id':99,'result':{}}),flush=True)","print('x'*65537,flush=True)","pass"]
        for script in commands:
            client=mcp_client.StdioClient(command=[sys.executable,'-c',script],timeout=2)
            try:
                with self.assertRaises(ToolError):client.initialize()
            finally:client.close()
            self.assertIsNotNone(client.process.poll())
    def test_timeout_and_cancel_kill_real_child(self):
        client=mcp_client.StdioClient(command=[sys.executable,'-c','import time;time.sleep(30)'],timeout=.15)
        try:
            with self.assertRaises(ToolError) as error:client.initialize()
            self.assertEqual(error.exception.code,'mcp_timeout')
        finally:client.close()
        self.assertIsNotNone(client.process.poll())
        count=[0]
        def check():
            count[0]+=1
            if count[0]>2:raise ToolError('tool_cancelled')
        client=mcp_client.StdioClient(check,command=[sys.executable,'-c','import time;time.sleep(30)'])
        try:
            with self.assertRaises(ToolError) as error:client.initialize()
            self.assertEqual(error.exception.code,'tool_cancelled')
        finally:client.close()
        self.assertIsNotNone(client.process.poll())
    def test_server_cannot_request_sampling_or_client_secrets(self):
        script="import sys,json;req=json.loads(sys.stdin.readline());print(json.dumps({'jsonrpc':'2.0','id':500,'method':'sampling/createMessage','params':{}}),flush=True);r=json.loads(sys.stdin.readline());assert r['error']['code']==-32601;print(json.dumps({'jsonrpc':'2.0','id':req['id'],'result':{'denied':True}}),flush=True)"
        client=mcp_client.StdioClient(command=[sys.executable,'-c',script])
        try:self.assertEqual(client.request('initialize',{}),{'denied':True})
        finally:client.close()
    def test_secret_environment_not_forwarded(self):
        original=subprocess.Popen;environments=[]
        def launch(*args,**kwargs):environments.append(kwargs['env']);return original(*args,**kwargs)
        with patch.dict(os.environ,{'GITHUB_TOKEN':'fixture-sensitive'}),patch.object(mcp_client.subprocess,'Popen',side_effect=launch):
            client=mcp_client.StdioClient()
            try:client.initialize()
            finally:client.close()
        self.assertNotIn('GITHUB_TOKEN',environments[0])
    def test_scope_and_schema_deny_before_spawn(self):
        with patch.object(tools.subprocess,'Popen',side_effect=AssertionError('no spawn')):
            for scope,args in [(policy('README.md'),{'action':'read','path':'README.md'}),(policy('other.md',mcp=True),{'action':'read','path':'README.md'}),(policy('README.md',mcp=True),{'action':'write','path':'README.md'})]:
                with self.assertRaises(ToolError):tools.read('mcp_docs',args,scope,lambda:None)
    def test_real_nested_job_process_and_large_protocol_result(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(config,'DATA',Path(folder)):
            result=tools.read('mcp_docs',{'action':'read','path':'README.md'},policy('README.md',mcp=True),lambda:None)
            self.assertTrue(result['document']);self.assertTrue(result['url'].startswith('/api/v1/integrations/mcp/document?'))
            self.assertEqual(list((config.DATA/'tools-tmp').iterdir()),[])
    def test_catalog_authorizes_next_read_without_changing_original_scope(self):
        from test_web_search import Reply
        requests=[0];scope=policy('Pokaż dokumentację KripAI',mcp=True)
        class Client:
            def post(self,path,json):
                if path.endswith('apply-template'):return Reply({'prompt':'p'})
                if path.endswith('tokenize'):return Reply({'tokens':[1]})
                requests[0]+=1
                args={'action':'list'} if requests[0]==1 else {'action':'read','path':'docs/guide.md'}
                return Reply({'choices':[{'message':{'tool_calls':[{'id':str(requests[0]),'type':'function','function':{'name':'mcp_docs','arguments':__import__('json').dumps(args)}}]}}]})
        def read(name,args,current,check):
            if args['action']=='list':return {'url':'catalog','title':'Catalog','text':'docs/guide.md','paths':['docs/guide.md']}
            self.assertIn('docs/guide.md',current['documents'])
            return {'url':'document','title':'Guide','text':'Verified document'}
        with patch.object(tools,'read',side_effect=read):result=tools.plan(Client(),[],scope,lambda:None,lambda *a:None)
        self.assertEqual(result[-1]['text'],'Verified document');self.assertEqual(scope['documents'],[])
        self.assertNotIn('paths',result[0])

class McpAPITests(unittest.TestCase):
    def setUp(self):
        base=test_native.APITests('runTest');self.addCleanup(base.doCleanups);base.setUp();self.base=base
    def test_authorized_source_endpoint_and_connection_test(self):
        client=self.base.client
        response=self.base.post('/integrations/mcp/test',{});self.assertEqual(response.status_code,200);self.assertTrue(response.json()['available'])
        document=client.get('/api/v1/integrations/mcp/document?path=README.md');self.assertEqual(document.status_code,200);self.assertIn('text/plain',document.headers['content-type'])
        self.assertEqual(client.get('/api/v1/integrations/mcp/document?path=../llm.key').status_code,404)
        self.assertEqual(client.post('/api/v1/integrations/mcp/test',headers={'X-CSRF-Token':'wrong'}).status_code,403)
        client.cookies.clear();self.assertEqual(client.get('/api/v1/integrations/mcp/catalog').status_code,401)
    def test_old_idempotency_hash_and_explicit_false_keep_same_run(self):
        from app.db import connect
        from app.models import MessageCreate
        from app.security import digest
        key=str(uuid4());body={'text':'Hej','client_message_id':str(uuid4())}
        cid,response=self.base.send(key=key,body=body)
        self.assertEqual(response.status_code,202)
        old=MessageCreate.model_validate(body).model_dump(mode='json',exclude={'allow_mcp','attachment_page'})
        with connect() as conn:stored=conn.execute('SELECT request_sha256 FROM idempotency_keys WHERE key=?',(key,)).fetchone()['request_sha256']
        self.assertEqual(bytes(stored),digest(json.dumps(old,sort_keys=True,ensure_ascii=False,separators=(',',':'))))
        route='/conversations/'+cid+'/messages'
        self.assertEqual(self.base.post(route,dict(body,allow_mcp=False),key).json(),response.json())
        self.assertEqual(self.base.post(route,dict(body,allow_mcp=True),key).status_code,409)
        self.assertEqual(self.base.wait(response.json()['run_id'])['status'],'completed')
    def test_mcp_only_chat_real_process_history_and_offline_default(self):
        original=test_native.FakeModel.do_POST;plans=[0]
        def handler(server):
            import io
            body=json.loads(server.rfile.read(int(server.headers['Content-Length'])))
            if server.path=='/v1/chat/completions' and body.get('tools'):
                plans[0]+=1
                message={'tool_calls':[{'id':'mcp','type':'function','function':{'name':'mcp_docs','arguments':'{"action":"read","path":"README.md"}'}}]} if plans[0]==1 else {'content':'done'}
                data={'choices':[{'message':message}]}
            elif body.get('max_tokens')==128:data={'choices':[{'message':{'content':'KripAI działa lokalnie na Windows.'}}]}
            else:
                encoded=json.dumps(body).encode();server.rfile=io.BytesIO(encoded);server.headers.replace_header('Content-Length',str(len(encoded)));return original(server)
            server.send_response(200);server.end_headers();server.wfile.write(json.dumps(data).encode())
        with patch.object(test_native.FakeModel,'do_POST',handler):
            cid,response=self.base.send(body={'text':'Przeczytaj README.md przez MCP','client_message_id':str(uuid4()),'allow_mcp':True})
            run=self.base.wait(response.json()['run_id']);self.assertEqual(run['status'],'completed',run)
        rows=self.base.client.get('/api/v1/conversations/'+cid+'/messages').json()['items'];source=rows[-1]['tool_sources'][0]
        self.assertEqual(source['name'],'mcp_docs');self.assertTrue(source['excerpt'].startswith('# KripAI'))
        with patch.object(tools,'plan',side_effect=AssertionError('offline cannot plan')):
            _,response=self.base.send();self.assertEqual(self.base.wait(response.json()['run_id'])['status'],'completed')

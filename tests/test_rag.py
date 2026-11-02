from schema_helpers import drop_tools
"""RAG: prawdziwy sqlite-vec/SQLite/PDF/HTTP; model embeddingów kontrolowany."""
from contextlib import contextmanager
import concurrent.futures
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import struct
import threading
import time
from unittest.mock import patch
import unittest
from uuid import uuid4
import httpx
import test_native
from test_native import DataCase
from test_media import pdf
from app import config,rag,vectors,embeddings,maintenance
from app.db import connect,migrate,migration_checksums
from app.context import prepare,ContextTooLarge
from app.embeddings import RagError

class FakeEncoder:
    def chunks(self,text):yield text[:700]
    def embed(self,text,query=False):
        values=[0.0]*384;values[0 if 'STRONA 1' in text or 'pierwsza' in text else 1]=1
        return vectors.encode(values)

@contextmanager
def fake_session(check):check();yield FakeEncoder()

class RagDataTests(DataCase):
    def setUp(self):
        super().setUp();rag.STOP.clear();rag.media.guard.stopping.clear();rag.media.guard.recent.clear()
        self.uid=self.user();self.sid=str(uuid4());self.aid=str(uuid4())
        with connect() as conn:
            conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',(self.sid,self.uid,b'token',b'csrf',time.time()+600))
            conn.execute("INSERT INTO attachments(id,owner_id,filename,media_type,original,preview,pages,current_page) VALUES (?,?,?,'application/pdf',?,?,2,1)",(self.aid,self.uid,'dokument.pdf',pdf(),b'PNG'))
        self.user_data={'id':self.uid,'session_id':self.sid}
        self.stack.enter_context(patch.object(embeddings,'session',fake_session))
    def ready(self):
        rag.queue(self.aid,self.user_data);self.assertTrue(rag.process_next())
        with connect() as conn:
            doc=conn.execute('SELECT * FROM rag_documents').fetchone();self.assertEqual(doc['status'],'ready',doc)
    def test_pdf_index_retrieval_acl_partition_and_extension_disabled(self):
        self.ready()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_chunks').fetchone()['n'],2)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],2)
            # Dozwolone wyniki mają gorszy dystans niż obce/niewybrane: globalne top-k + filtr nie przejdzie.
            first=conn.execute('SELECT id FROM rag_chunks WHERE page=1').fetchone()['id']
            conn.execute('UPDATE rag_vectors SET embedding=? WHERE chunk_id=?',(vectors.encode([.8,.6]+[0]*382),first))
            for i in range(10):
                conn.execute('INSERT INTO rag_vectors VALUES (?,?,?,?)',(1000+i,'other',self.aid,vectors.encode([1]+[0]*383)))
                conn.execute('INSERT INTO rag_vectors VALUES (?,?,?,?)',(2000+i,self.uid,'not-selected',vectors.encode([1]+[0]*383)))
            with self.assertRaises(sqlite3.OperationalError):conn.execute("SELECT load_extension('missing')")
            plan=conn.execute('EXPLAIN QUERY PLAN SELECT chunk_id FROM rag_vectors WHERE embedding MATCH ? AND k=3 AND owner_id=? AND document_id=?',(vectors.encode([1]+[0]*383),self.uid,self.aid)).fetchall()
            self.assertTrue(any('VIRTUAL TABLE INDEX' in str(row) for row in plan))
        hits=rag.retrieve([self.aid],self.uid,'pierwsza strona',lambda:None)
        self.assertEqual(hits[0]['page'],1);self.assertIn('STRONA 1',hits[0]['text'])
        with self.assertRaises(RagError) as e:rag.retrieve([self.aid],'other','x',lambda:None)
        self.assertEqual(e.exception.status,404)
    def test_checkpoint_failure_resume_no_duplicate_chunks(self):
        rag.queue(self.aid,self.user_data)
        original=rag.media.decode
        def fail_page(data,page,*args):
            if page==2:raise OSError('crash')
            return original(data,page,*args)
        with patch.object(rag.media,'decode',fail_page):rag.process_next()
        with connect() as conn:
            doc=conn.execute('SELECT * FROM rag_documents').fetchone();self.assertEqual(doc['status'],'failed');self.assertEqual(doc['next_page'],2);self.assertEqual(doc['chunks'],1)
        rag.queue(self.aid,self.user_data);rag.process_next()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT status FROM rag_documents').fetchone()['status'],'ready')
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_chunks').fetchone()['n'],2)
    def test_cancellation_during_embedding_never_commits_page(self):
        rag.queue(self.aid,self.user_data)
        class PauseEncoder(FakeEncoder):
            def embed(inner,*args,**kwargs):rag.pause(self.aid,self.uid);return super().embed(*args,**kwargs)
        @contextmanager
        def session(check):yield PauseEncoder()
        with patch.object(embeddings,'session',session):rag.process_next()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT status FROM rag_documents').fetchone()['status'],'paused')
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],0)
        rag.queue(self.aid,self.user_data);rag.process_next()
        with connect() as conn:self.assertEqual(conn.execute('SELECT chunks FROM rag_documents').fetchone()['chunks'],2)
        # Drugi wariant: pauza w trakcie rzeczywistego procesu dekodera.
        import subprocess,sys
        rag.queue(self.aid,self.user_data,True)
        folder=config.DATA/'cancel-decoder';folder.mkdir()
        processes=[];popen=subprocess.Popen
        def launch(argv,**kwargs):
            child=popen(argv,**kwargs);processes.append(child);return child
        def decoder(data,page,key,cancelled):
            rag.media.guard.process([sys.executable,'-c',"from pathlib import Path; import time; Path('ready').touch(); time.sleep(60)"],folder,key,cancelled,20)
            return {'text_layer':'zbyt późno'},b'PNG'
        with patch.object(rag.media,'decode',decoder),patch.object(rag.media.voice.subprocess,'Popen',launch),concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(rag.process_next)
            for _ in range(100):
                if (folder/'ready').exists():break
                time.sleep(.01)
            self.assertTrue((folder/'ready').exists())
            rag.pause(self.aid,self.uid);future.result(5)
        self.assertTrue(processes and all(p.poll() is not None for p in processes))
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],0)

    def test_gaming_and_revoked_session_pause_without_embedding(self):
        for mode,revoked in [('gaming',False),('normal',True)]:
            rag.queue(self.aid,self.user_data)
            with connect() as conn:
                conn.execute('UPDATE system_mode SET requested_mode=?',(mode,))
                if revoked:conn.execute('UPDATE sessions SET revoked_at=now()')
            with patch.object(embeddings,'session',side_effect=AssertionError('must not start')):
                # check_document musi być wywołany przed wejściem w encoder.
                rag.process_next()
            with connect() as conn:self.assertEqual(conn.execute('SELECT status FROM rag_documents').fetchone()['status'],'paused')
            with connect() as conn:conn.execute("UPDATE system_mode SET requested_mode='normal'")
    def test_backup_restore_delete_vectors_and_sources_and_backup_failure(self):
        self.ready();cid=self.conversation();mid=str(uuid4())
        hits=rag.retrieve([self.aid],self.uid,'pierwsza',lambda:None)
        with connect() as conn:
            conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'assistant','Odpowiedź [1]')",(mid,cid))
            rag.save_sources(conn,mid,hits)
        backup=maintenance.backup()
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):rag.remove(self.aid,self.uid)
        rag.remove(self.aid,self.uid)
        with connect() as conn:
            for table in ['rag_documents','rag_chunks','rag_vectors','message_sources']:self.assertEqual(conn.execute('SELECT count(*) AS n FROM '+table).fetchone()['n'],0)
            self.assertIsNotNone(conn.execute('SELECT 1 FROM attachments').fetchone())
        maintenance.restore(backup)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],2)
            self.assertEqual(len(rag.sources(conn,mid,self.uid)),2)
        rag.media.delete(self.aid,self.uid)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],0)
    def test_model_mismatch_refused_and_rebuild_purges_old_index(self):
        self.ready()
        with connect() as conn:conn.execute("UPDATE rag_documents SET space='old-model'")
        with self.assertRaises(RagError):rag.queue(self.aid,self.user_data)
        with self.assertRaises(RagError):rag.retrieve([self.aid],self.uid,'x',lambda:None)
        rag.queue(self.aid,self.user_data,True);rag.process_next()
        with connect() as conn:self.assertEqual(conn.execute('SELECT space FROM rag_documents').fetchone()['space'],vectors.SPACE)
    def test_blank_or_truncated_page_not_marked_ready_and_quota_rolls_back(self):
        for info in [{'text_layer':'','text_truncated':False},{'text_layer':'a','text_truncated':True}]:
            rag.queue(self.aid,self.user_data,True)
            with patch.object(rag.media,'decode',return_value=(info,b'PNG')):rag.process_next()
            with connect() as conn:self.assertEqual(conn.execute('SELECT status FROM rag_documents').fetchone()['status'],'failed')
        rag.queue(self.aid,self.user_data,True)
        with patch.object(rag,'MAX_CHUNKS',0):rag.process_next()
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'],0)
    def test_restart_resumes_indexing_checkpoint(self):
        rag.queue(self.aid,self.user_data)
        with connect() as conn:conn.execute("UPDATE rag_documents SET status='indexing'")
        rag.start()
        try:
            for _ in range(100):
                with connect() as conn:state=conn.execute('SELECT status FROM rag_documents').fetchone()['status']
                if state=='ready':break
                time.sleep(.03)
            self.assertEqual(state,'ready')
        finally:rag.shutdown()
    def test_migrate_v3_backup_and_rollback_on_failure(self):
        with connect() as conn:
            drop_tools(conn)
            for table in ['message_sources','rag_vectors','rag_chunks','rag_documents']:conn.execute('DROP TABLE '+table)
            conn.execute('ALTER TABLE runs DROP COLUMN rag_selection');conn.execute('DELETE FROM schema_migrations WHERE version=4')
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):migrate()
        with connect() as conn:self.assertEqual(len(conn.execute('SELECT * FROM schema_migrations').fetchall()),3)
        migrate()
        with connect() as conn:self.assertEqual(len(conn.execute('SELECT * FROM schema_migrations').fetchall()),len(migration_checksums()))

    def test_corrupt_derived_index_not_published_as_backup(self):
        self.ready()
        with connect() as conn:conn.execute('DELETE FROM rag_vectors WHERE chunk_id=(SELECT min(id) FROM rag_chunks)')
        with self.assertRaises(ValueError):maintenance.backup()
        self.assertEqual(list(config.BACKUPS.glob('*.partial')),[])

class RagAPITests(unittest.TestCase):
    def setUp(self):
        # Wspólne API/HTTP fixture bez ponownego dziedziczenia testów rdzenia.
        base=test_native.APITests('runTest')
        self.addCleanup(base.doCleanups)
        base.setUp()
        self.client,self.post,self.wait,self.user=base.client,base.post,base.wait,base.user

    def test_rag_chat(self):
        with patch.object(embeddings,'session',fake_session):
            aid=str(uuid4());uid=self.user()
            with connect() as conn:
                sid=conn.execute('SELECT id FROM sessions WHERE user_id=?',(uid,)).fetchone()['id']
                conn.execute("INSERT INTO attachments(id,owner_id,filename,media_type,original,preview,pages,current_page) VALUES (?,?,?,'application/pdf',?,?,2,1)",(aid,uid,'plan.pdf',pdf(),b'PNG'))
            response=self.post('/rag/documents/'+aid+'/index',{});self.assertEqual(response.status_code,202,response.text)
            for _ in range(100):
                rows=self.client.get('/api/v1/rag/documents').json()['items']
                if rows and rows[0]['status']=='ready':break
                time.sleep(.05)
            self.assertEqual(rows[0]['status'],'ready',rows)
            cid=self.post('/conversations',{}).json()['id']
            key=str(uuid4());body={'text':'pierwsza strona','client_message_id':str(uuid4()),'document_ids':[aid]}
            response=self.post('/conversations/'+cid+'/messages',body,key);self.assertEqual(response.status_code,202,response.text)
            self.assertEqual(self.post('/conversations/'+cid+'/messages',body,key).json(),response.json())
            rid=response.json()['run_id'];result=self.wait(rid);self.assertEqual(result['status'],'completed',result)
            rows=self.client.get('/api/v1/conversations/'+cid+'/messages').json()['items']
            self.assertTrue(rows[-1]['sources']);self.assertEqual(rows[-1]['sources'][0]['filename'],'plan.pdf')
            self.assertIn('rag.sources',self.client.get('/api/v1/runs/'+rid+'/events').text)
            self.assertEqual(self.client.post('/api/v1/rag/documents/'+aid+'/index',json={},headers={'X-CSRF-Token':'bad'}).status_code,403)
            self.assertEqual(self.client.delete('/api/v1/rag/documents/'+str(uuid4())).status_code,404)
            self.assertEqual(self.client.delete('/api/v1/rag/documents/'+aid).status_code,204)
            self.assertEqual(self.client.get('/api/v1/conversations/'+cid+'/messages').json()['items'][-1]['sources'],[])
        replay=self.client.get('/api/v1/runs/'+rid+'/events').text
        self.assertNotIn('STRONA 1',replay);self.assertNotIn('STRONA 2',replay)


class EmbeddingTests(unittest.TestCase):
    def test_real_http_prefixes_normalization_and_failures(self):
        bodies=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));bodies.append((self.path,data))
                result={'tokens':list(range(len(data['content'])//2))} if self.path=='/tokenize' else {'data':[{'embedding':[3,4]+[0]*382}]}
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(result).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with httpx.Client(base_url='http://127.0.0.1:'+str(server.server_port),trust_env=False) as client:
                model=embeddings.Encoder(client,lambda:None);v=model.embed('pytanie',True);self.assertAlmostEqual(struct.unpack('<384f',v)[0],.6)
                model.embed('źródło');self.assertEqual([b['input'] for p,b in bodies if p=='/v1/embeddings'],['query: pytanie','passage: źródło'])
                chunks=list(model.chunks('a'*1800));self.assertGreater(len(chunks),2);self.assertTrue(all(len(c)<=700 for c in chunks))
                with self.assertRaises(RagError):model.embed('x'*2000,True)
        finally:server.shutdown();server.server_close();thread.join()
    def test_invalid_embeddings_and_checksum_rejected(self):
        for value in [[0]*384,[float('nan')]*384,[1]*383,[True]*384]:
            with self.assertRaises(ValueError):vectors.encode(value)
        with patch.object(vectors,'EXTENSION_ROOT',Path('/missing')):
            c=sqlite3.connect(':memory:')
            try:
                with self.assertRaises(RuntimeError):vectors.load(c)
            finally:c.close()
    def test_context_budget_drops_sources_without_dropping_question(self):
        hits=[{'text':'a'*700,'page':1} for _ in range(3)]
        class Response:
            def __init__(self,result):self.result=result
            def raise_for_status(self):pass
            def json(self):return self.result
        class Client:
            def post(self,path,json):return Response({'prompt':str(json['messages'])} if path.endswith('template') else {'tokens':list(range(len(json['content'])))})
        messages,_,tokens=prepare([{'role':'user','content':'pytanie'}],Client(),hits)
        self.assertLess(len(hits),3);self.assertLessEqual(tokens,config.CONTEXT-config.OUTPUT-128);self.assertEqual(messages[-1]['content'],'pytanie')
        self.assertIn('niezaufanymi',messages[0]['content'])

class EncoderProcessTests(unittest.TestCase):
    def test_cpu_command_real_child_cleanup_and_cancel_before_ready(self):
        import subprocess,sys,tempfile
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'runtime/llama').mkdir(parents=True);(root/'runtime/llama/llama-server.exe').touch();(root/'models').mkdir();(root/'models/test.gguf').write_bytes(b'fixture');(root/'llm.key').write_text('qa-key')
            lock=dict(vectors.LOCK,model={'name':'test.gguf','sha256':hashlib.sha256(b'fixture').hexdigest()})
            launched=[];commands=[];popen=subprocess.Popen
            def launch(argv,**kwargs):
                commands.append(argv);child=popen([sys.executable,'-c','import time;time.sleep(60)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);launched.append(child);return child
            class Client:
                def __init__(self,**kwargs):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def get(self,path):return type('Health',(),{'status_code':200})()
            with patch.object(config,'ROOT',root),patch.object(config,'DATA',root),patch.object(embeddings,'LOCK',lock),patch.object(embeddings.subprocess,'Popen',launch),patch.object(embeddings.httpx,'Client',Client):
                with embeddings.session(lambda:None):self.assertIsNone(launched[0].poll())
                self.assertIsNotNone(launched[0].poll())
                command=commands[0];self.assertEqual(command[command.index('--device')+1],'none');self.assertEqual(command[command.index('--n-gpu-layers')+1],'0');self.assertIn('--no-op-offload',command);self.assertIn(vectors.LOCK['metadata_override'],command)
                self.assertNotIn('qa-key',command)
                checks=[0]
                def cancel():
                    checks[0]+=1
                    if checks[0]>=3:raise RagError('rag_paused')
                with self.assertRaises(RagError):
                    with embeddings.session(cancel):pass
                self.assertTrue(all(p.poll() is not None for p in launched))
                (root/'models/test.gguf').write_bytes(b'wrong')
                with self.assertRaises(RagError):
                    with embeddings.session(lambda:None):pass
                self.assertEqual(len(launched),2)

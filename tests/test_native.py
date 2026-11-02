"""Rzeczywisty SQLite i API; mały serwer HTTP zastępuje wyłącznie kosztowny model."""
import concurrent.futures
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config,main
from app.db import migrate,connect,open_db
from app.maintenance import backup,restore,set_password,validate
from app.context import select_context,ContextTooLarge
from app.model_process import ModelProcess
from app.processes import InstanceLock
from app.security import verify_password
from fastapi.testclient import TestClient
import httpx

PASSWORD='testowe haslo do testow 123'

class FakeModel(BaseHTTPRequestHandler):
    release_stream=threading.Event()
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers();self.wfile.write(b'{"status":"ok"}')
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/apply-template':data={'prompt':json.dumps(body['messages'],ensure_ascii=False)}
        elif self.path=='/tokenize':data={'tokens':list(range(len(body['content'])//3+1))}
        else:
            text=body['messages'][-1]['content']
            if text=='FAIL':self.send_response(500);self.end_headers();return
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            try:
                for piece in (['x'*200,'koniec'] if text=='STREAM' else ['Testowa ','odpowiedź.']):
                    self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':piece}}]})+'\n\n').encode());self.wfile.flush()
                    if text=='WAIT':time.sleep(.8)
                    if text=='STREAM':self.release_stream.wait(8)
                self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError):pass
            return
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())

class DataCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        root=Path(self.temp.name)
        self.stack.enter_context(patch.object(config,'DATA',root/'data'))
        self.stack.enter_context(patch.object(config,'BACKUPS',root/'backups'))
        migrate();set_password(PASSWORD)
        main.login_attempts.clear()
    def user(self):
        with connect() as c:return c.execute("SELECT id FROM users WHERE username='owner'").fetchone()['id']
    def conversation(self):
        cid=str(uuid4());uid=self.user()
        with connect() as c:c.execute('INSERT INTO conversations(id,owner_id) VALUES (?,?)',(cid,uid))
        return cid

class DatabaseTests(DataCase):
    def test_migration_repeat_and_unknown_version(self):
        migrate()
        with connect() as c:c.execute('UPDATE schema_migrations SET version=99 WHERE version=1')
        with self.assertRaises(RuntimeError):migrate()
    def test_changed_schema_rejected(self):
        with connect() as c:c.execute("UPDATE schema_migrations SET checksum='wrong'")
        with self.assertRaises(RuntimeError):migrate()
    def test_foreign_key_rejects_cross_conversation_run(self):
        a=self.conversation();b=self.conversation();mid=str(uuid4())
        with connect() as c:c.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user','test')",(mid,a))
        with self.assertRaises(sqlite3.IntegrityError),connect() as c:
            c.execute("INSERT INTO runs(id,conversation_id,user_message_id,status) VALUES (?,?,?,'queued')",(str(uuid4()),b,mid))
    def test_transaction_rolls_back_on_error(self):
        with self.assertRaises(RuntimeError),connect() as c:
            c.execute("UPDATE users SET username='changed'");raise RuntimeError()
        self.assertIsNotNone(self.user())
    def test_wal_and_foreign_keys(self):
        with connect() as c:
            self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()['journal_mode'],'wal')
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()['foreign_keys'],1)
    def test_backup_restore_preserves_history_and_revokes_sessions(self):
        cid=self.conversation()
        with connect() as c:c.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user','zapisana historia')",(str(uuid4()),cid))
        path=backup();validate(path)
        with connect() as c:c.execute('DELETE FROM messages')
        restore(path)
        with connect() as c:self.assertEqual(c.execute('SELECT content FROM messages').fetchone()['content'],'zapisana historia')
        self.assertGreaterEqual(len(list(config.BACKUPS.glob('*.sqlite3'))),2)
    def test_backup_verification_failure_leaves_live_data_and_no_partial_copy(self):
        cid=self.conversation()
        with patch('app.maintenance.validate',side_effect=ValueError('bad copy')):
            with self.assertRaises(ValueError):backup()
        self.assertEqual(list(config.BACKUPS.iterdir()),[])
        with connect() as c:self.assertEqual(c.execute('SELECT id FROM conversations').fetchone()['id'],cid)
    def test_bad_backup_does_not_replace_live_database(self):
        cid=self.conversation();bad=Path(self.temp.name)/'bad';bad.write_text('not sqlite')
        with self.assertRaises(sqlite3.DatabaseError):restore(bad)
        with connect() as c:self.assertEqual(c.execute('SELECT id FROM conversations').fetchone()['id'],cid)
    def test_password_reset_rejects_short_and_revokes_tokens(self):
        with self.assertRaises(ValueError):set_password('short')
        uid=self.user()
        with connect() as c:
            c.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',('s',uid,b't',b'c',time.time()+100))
        set_password('inne nowe haslo 12345')
        with connect() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM sessions').fetchone()['n'],0)
            hashed=c.execute('SELECT password_hash FROM users').fetchone()['password_hash']
        self.assertFalse(verify_password(PASSWORD,hashed));self.assertTrue(verify_password('inne nowe haslo 12345',hashed))
    def test_single_instance_lock(self):
        with InstanceLock():
            with self.assertRaises(RuntimeError):
                with InstanceLock():pass
        with InstanceLock():pass

class ContextTests(unittest.TestCase):
    def test_long_history_trims_whole_turns_and_preserves_input(self):
        history=[{'role':role,'content':str(i)+'x'*100} for i in range(100) for role in ['user','assistant']]
        history.append({'role':'user','content':'ostatnie pytanie'})
        copy=json.dumps(history)
        count=lambda messages:sum(len(m['content']) for m in messages)
        selected,omitted,tokens=select_context(history,count,budget=600)
        self.assertGreater(omitted,0);self.assertLessEqual(tokens,600)
        self.assertEqual(selected[1]['role'],'user');self.assertEqual(selected[-1]['content'],'ostatnie pytanie')
        self.assertEqual(json.dumps(history),copy)
    def test_oversized_latest_message_fails_explicitly(self):
        with self.assertRaises(ContextTooLarge):select_context([{'role':'user','content':'x'*5000}],lambda m:sum(len(x['content']) for x in m),100)
    def test_tokenizer_failure_not_silent_character_fallback(self):
        def fail(_):raise RuntimeError('tokenizer unavailable')
        with self.assertRaises(RuntimeError):select_context([{'role':'user','content':'hi'}],fail)

class APITests(DataCase):
    def setUp(self):
        super().setUp()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),FakeModel)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        url='http://127.0.0.1:'+str(self.server.server_port)
        self.stack.enter_context(patch.object(config,'LLM',url));self.stack.enter_context(patch.object(main,'LLM',url))
        def control(stop):
            while not stop.is_set():
                with connect() as c:c.execute("UPDATE system_mode SET controller_state=CASE requested_mode WHEN 'normal' THEN 'ready' ELSE 'stopped' END")
                stop.wait(.02)
        self.stack.enter_context(patch.object(main,'control',control))
        self.client=self.stack.enter_context(TestClient(main.app,base_url=config.ORIGIN))
        r=self.client.post('/api/v1/auth/login',headers={'Origin':config.ORIGIN},json={'username':'owner','password':PASSWORD})
        self.assertEqual(r.status_code,204)
        self.client.headers['Origin']=config.ORIGIN
        self.client.headers['X-CSRF-Token']=self.client.cookies.get('assistant_csrf')
        for _ in range(50):
            if self.client.get('/api/v1/system/status').json()['controller']=='ready':break
            time.sleep(.01)
    def post(self,path,body=None,key=None):
        return self.client.post('/api/v1'+path,json=body,headers={'Idempotency-Key':key or str(uuid4())})
    def send(self,text='hej',cid=None,key=None,body=None):
        cid=cid or self.post('/conversations',{}).json()['id']
        body=body or {'text':text,'client_message_id':str(uuid4())}
        return cid,self.post('/conversations/'+cid+'/messages',body,key)
    def wait(self,rid):
        for _ in range(150):
            r=self.client.get('/api/v1/runs/'+rid).json()
            if r['status'] in main.TERMINAL:return r
            time.sleep(.03)
        self.fail('Timeout run')
    def test_login_csrf_logout_and_cookie_flags(self):
        other=TestClient(main.app,base_url=config.ORIGIN)
        self.assertEqual(other.get('/api/v1/me').status_code,401)
        self.assertEqual(other.post('/api/v1/auth/login',headers={'Origin':config.ORIGIN},json={'username':'owner','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/v1/conversations',headers={'X-CSRF-Token':''},json={}).status_code,403)
        self.assertEqual(self.post('/auth/logout').status_code,204)
        self.assertEqual(self.client.get('/api/v1/me').status_code,401)
    def test_host_origin_proxy_and_chunked_body_denied(self):
        self.assertEqual(self.client.get('/api/v1/me',headers={'Host':'evil.example'}).status_code,400)
        self.assertEqual(self.client.get('/api/v1/me',headers={'CF-Connecting-IP':'1.2.3.4'}).status_code,400)
        self.assertEqual(self.client.post('/api/v1/conversations',json={},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/v1/conversations',content=iter([b'x'*17000])).status_code,413)
    def test_stream_history_idempotency_and_replay(self):
        key=str(uuid4());body={'text':'hej','client_message_id':str(uuid4())}
        cid,r=self.send(key=key,body=body);self.assertEqual(r.status_code,202)
        retry=self.post('/conversations/'+cid+'/messages',body,key);self.assertEqual(retry.json(),r.json())
        self.assertEqual(self.post('/conversations/'+cid+'/messages',dict(body,text='inne'),key).status_code,409)
        rid=r.json()['run_id'];self.assertEqual(self.wait(rid)['status'],'completed')
        rows=self.client.get('/api/v1/conversations/'+cid+'/messages').json()['items']
        self.assertEqual([row['content'] for row in rows],['hej','Testowa odpowiedź.'])
        events=self.client.get('/api/v1/runs/'+rid+'/events').text
        self.assertIn('context.info',events);self.assertIn('assistant.text.delta',events)
        replay=self.client.get('/api/v1/runs/'+rid+'/events',headers={'Last-Event-ID':'1'}).text
        self.assertNotIn('\nid: 1\n','\n'+replay)
        self.assertEqual(self.client.get('/api/v1/runs/'+rid+'/events',headers={'Last-Event-ID':'9999'}).status_code,410)
    def test_real_http_stream_delivers_delta_before_completion(self):
        import uvicorn
        server=uvicorn.Server(uvicorn.Config(main.app,host='127.0.0.1',port=0,lifespan='off',access_log=False,log_level='error'))
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        try:
            for _ in range(100):
                if server.started:break
                time.sleep(.01)
            port=server.servers[0].sockets[0].getsockname()[1]
            FakeModel.release_stream.clear()
            _,r=self.send('STREAM');rid=r.json()['run_id']
            headers={'Host':'localhost:8765','Cookie':'assistant_session='+self.client.cookies.get('assistant_session')}
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',headers=headers,trust_env=False,timeout=5) as client:
                start=time.monotonic()
                with client.stream('GET','/api/v1/runs/'+rid+'/events') as response:
                    self.assertEqual(response.status_code,200)
                    for line in response.iter_lines():
                        if line=='event: assistant.text.delta':break
                    else:self.fail('Brak fragmentu SSE')
                    self.assertNotEqual(self.client.get('/api/v1/runs/'+rid).json()['status'],'completed')
            FakeModel.release_stream.set();self.wait(rid)
        finally:
            FakeModel.release_stream.set();server.should_exit=True;thread.join(timeout=5)
    def test_concurrent_idempotency_is_atomic(self):
        cid=self.post('/conversations',{}).json()['id'];key=str(uuid4());body={'text':'hej','client_message_id':str(uuid4())}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(lambda _:self.post('/conversations/'+cid+'/messages',body,key),range(4)))
        self.assertTrue(all(r.status_code==202 for r in rows));self.assertEqual(len({r.json()['run_id'] for r in rows}),1)
        self.wait(rows[0].json()['run_id'])
    def test_failure_and_gaming_cancel_then_recovery(self):
        _,r=self.send('FAIL');self.assertEqual(self.wait(r.json()['run_id'])['status'],'failed')
        _,r=self.send('WAIT');rid=r.json()['run_id']
        self.assertEqual(self.post('/system/mode',{'mode':'gaming'}).status_code,202)
        self.assertEqual(self.wait(rid)['status'],'cancelled')
        _,r=self.send();self.assertEqual(r.status_code,503)
        self.post('/system/mode',{'mode':'normal'})
        for _ in range(100):
            if self.client.get('/api/v1/system/status').json()['controller']=='ready':break
            time.sleep(.01)
        _,r=self.send();self.assertEqual(self.wait(r.json()['run_id'])['status'],'completed')
    def test_owner_isolation(self):
        cid=self.post('/conversations',{}).json()['id']
        with connect() as c:
            c.execute("INSERT INTO users(id,username,password_hash) SELECT 'other','other',password_hash FROM users LIMIT 1")
            c.execute("UPDATE conversations SET owner_id='other' WHERE id=?",(cid,))
        self.assertEqual(self.client.get('/api/v1/conversations/'+cid).status_code,404)
        self.assertEqual(self.send(cid=cid)[1].status_code,404)
    def test_pagination_latest_first_and_no_duplicates(self):
        cid=self.post('/conversations',{}).json()['id']
        with connect() as c:
            for i in range(123):c.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user',?)",(uuid4(),cid,str(i)))
        page=self.client.get('/api/v1/conversations/'+cid+'/messages?limit=50').json()
        self.assertEqual(page['items'][-1]['content'],'122');self.assertEqual(page['items'][0]['content'],'73')
        page2=self.client.get('/api/v1/conversations/'+cid+'/messages?limit=50&cursor='+page['next_cursor']).json()
        self.assertEqual(page2['items'][-1]['content'],'72')
        self.assertFalse({r['id'] for r in page['items']}&{r['id'] for r in page2['items']})
    def test_reset_invalidates_logged_in_session(self):
        set_password('nowe bezpieczne haslo 555')
        self.assertEqual(self.client.get('/api/v1/me').status_code,401)
    def test_incomplete_run_marked_failed_on_restart(self):
        _,r=self.send('WAIT');rid=r.json()['run_id']
        self.wait(rid)
        self.client.__exit__(None,None,None)
        with connect() as c:c.execute("UPDATE runs SET status='generating' WHERE id=?",(rid,))
        self.client.__enter__()
        with connect() as c:
            row=c.execute('SELECT status,error_code FROM runs WHERE id=?',(rid,)).fetchone()
            self.assertEqual(row,{'status':'failed','error_code':'server_restarted'})

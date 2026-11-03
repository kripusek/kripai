"""Rzeczywisty HTTP/SSE i SQLite, kontrolowane zakończenia modelu."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app import config,main,media
from app.db import connect
from app.context import select_context
from test_native import DataCase,PASSWORD


class Engine(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/apply-template':data={'prompt':'test'}
        elif self.path=='/tokenize':data={'tokens':[1]*10}
        else:
            self.server.budgets.append(body['max_tokens'])
            content=body['messages'][-1]['content'];text=content if isinstance(content,str) else content[0]['text']
            self.send_response(200);self.end_headers()
            self.wfile.write(b'data: {"choices":[{"delta":{"content":"Fragment kodu"}}]}\n\n')
            if text!='BROKEN':
                payload={'choices':[{'delta':{},'finish_reason':'length' if text=='LIMIT' else 'stop'}]}
                self.wfile.write(('data: '+json.dumps(payload)+'\n\ndata: [DONE]\n\n').encode())
            return
        self.send_response(200);self.end_headers();self.wfile.write(json.dumps(data).encode())


class CutoffTests(DataCase):
    def setUp(self):
        super().setUp()
        # Ten fixture steruje inferencją bez lifespan aplikacji. Nie dziedziczy
        # flag shutdown pozostawionych przez poprzedni TestClient z lifespan.
        self.stack.enter_context(patch.object(main,'stop_worker',threading.Event()))
        self.stack.enter_context(patch.object(media.guard,'stopping',threading.Event()))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Engine);self.server.budgets=[]
        thread=threading.Thread(target=self.server.serve_forever);thread.start();self.addCleanup(lambda:(self.server.shutdown(),thread.join(),self.server.server_close()))
        url='http://127.0.0.1:'+str(self.server.server_port)
        self.stack.enter_context(patch.object(config,'LLM',url));self.stack.enter_context(patch.object(main,'LLM',url))
        self.client=TestClient(main.app,base_url=config.ORIGIN);self.addCleanup(self.client.close);self.client.headers['Origin']=config.ORIGIN
        self.client.post('/api/v1/auth/login',json={'username':'owner','password':PASSWORD});self.client.headers['X-CSRF-Token']=self.client.cookies.get('assistant_csrf')
        with connect() as conn:conn.execute("UPDATE system_mode SET controller_state='ready'")

    def run_text(self,text):
        cid=self.conversation();r=self.client.post('/api/v1/conversations/'+cid+'/messages',json={'text':text,'client_message_id':str(uuid4())},headers={'Idempotency-Key':str(uuid4())});self.assertEqual(r.status_code,202,r.text)
        rid=r.json()['run_id']
        with connect() as conn:run=conn.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
        main.infer(run)
        with connect() as conn:return conn.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone(),conn.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY seq',(cid,)).fetchall()

    def test_limit_preserves_answer_and_reports_limit_in_run_and_sse(self):
        run,rows=self.run_text('LIMIT');self.assertEqual(run['status'],'completed');self.assertIsNone(run['error_code']);self.assertEqual(rows[-1]['content'],'Fragment koduFragment kodu')
        with connect() as conn:
            event=conn.execute("SELECT payload FROM run_events WHERE run_id=? AND type='run.status' ORDER BY seq DESC LIMIT 1",(run['id'],)).fetchone()
        self.assertIsNone(event['payload']['error_code']);self.assertEqual(self.server.budgets,[2048,2048])

    def test_partial_text_survives_broken_stream(self):
        run,rows=self.run_text('BROKEN')
        self.assertEqual(run['status'],'failed');self.assertEqual(rows[-1]['content'],'Fragment kodu')

    def test_normal_stop_not_reported_as_cutoff(self):
        run,rows=self.run_text('STOP');self.assertEqual(run['status'],'completed');self.assertIsNone(run['error_code'])

    def test_broken_stream_not_falsely_completed(self):
        run,rows=self.run_text('BROKEN');self.assertEqual(run['status'],'failed');self.assertEqual(run['error_code'],'inference_interrupted')

    def test_vision_distinguishes_length_from_stop(self):
        with connect() as conn:s=conn.execute('SELECT id,user_id FROM sessions').fetchone()
        for prompt,reason in [('LIMIT','length'),('STOP','stop')]:
            answer=media.ask_model(b'test-image',prompt,(s['id'],s['user_id'],str(uuid4())),threading.Event())
            self.assertEqual(answer,'Fragment kodu');self.assertEqual(answer.finish_reason,reason)
        self.assertEqual(self.server.budgets,[2048,2048])

    def test_context_reserves_full_output_budget(self):
        messages,omitted,tokens=select_context([{'role':'user','content':'test'}],lambda m:100)
        self.assertLessEqual(tokens+config.OUTPUT+128,config.CONTEXT)

"""Prawdziwa baza/API/dekoder; VLM kontrolowany, bez GPU w teście."""
import concurrent.futures
import threading
import time
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app import config,main,media,voice,maintenance
from app.db import connect,migrate
from test_native import DataCase,PASSWORD
from test_media import png,pdf


class ChatImageTests(DataCase):
    def setUp(self):
        super().setUp()
        self.client=TestClient(main.app,base_url=config.ORIGIN);self.addCleanup(self.client.close)
        self.client.headers['Origin']=config.ORIGIN
        self.client.post('/api/v1/auth/login',json={'username':'owner','password':PASSWORD})
        self.client.headers['X-CSRF-Token']=self.client.cookies.get('assistant_csrf')
        self.stack.enter_context(patch.object(media,'guard',voice.VoiceService()))
        self.cid=self.conversation()
        with connect() as conn:conn.execute("UPDATE system_mode SET controller_state='ready',requested_mode='normal'")
        self.models=config.DATA/'models';self.models.mkdir()
        for name in ('vision-model.gguf','vision-mmproj.gguf'):(self.models/name).write_bytes(b'fixture')

    def upload(self,data=None):
        result=self.client.post('/api/v1/media/jobs/'+str(uuid4())+'/files?name=x.png',content=png() if data is None else data)
        self.assertEqual(result.status_code,201,result.text);return result.json()['id']

    def send(self,aid,body=None,key=None):
        return self.client.post('/api/v1/conversations/'+self.cid+'/messages',json=body or {'text':'Co jest na zdjęciu?','client_message_id':str(uuid4()),'attachment_id':aid},headers={'Idempotency-Key':key or str(uuid4())})

    def run_row(self,rid):
        with connect() as conn:return conn.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()

    def controller(self):
        stop=threading.Event()
        def control():
            while not stop.wait(.01):
                with connect() as conn:conn.execute("UPDATE system_mode SET loaded_profile=requested_profile,controller_state='ready'")
        thread=threading.Thread(target=control);thread.start();self.addCleanup(lambda:(stop.set(),thread.join()))

    def test_image_message_idempotency_history_and_backup(self):
        aid=self.upload();body={'text':'Zadanie','client_message_id':str(uuid4()),'attachment_id':aid};key=str(uuid4())
        result=self.send(aid,body,key);self.assertEqual(result.status_code,202,result.text)
        self.assertEqual(self.send(aid,body,key).json(),result.json())
        rows=self.client.get('/api/v1/conversations/'+self.cid+'/messages').json()['items'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['attachment_id'],aid)
        copy=maintenance.backup();maintenance.restore(copy)
        with connect() as conn:
            row=conn.execute('SELECT * FROM message_images').fetchone();self.assertEqual(row['attachment_id'],aid);self.assertIsNone(row['session_id'])
        self.assertEqual(self.client.get('/api/v1/files/'+aid+'/preview').status_code,401)

    def test_missing_model_other_owner_pdf_no_partial_message(self):
        aid=self.upload();(self.models/'vision-model.gguf').unlink();self.assertEqual(self.send(aid).status_code,503)
        (self.models/'vision-model.gguf').write_bytes(b'fixture');self.assertEqual(self.send(self.upload(pdf())).status_code,422)
        with connect() as conn:
            conn.execute("INSERT INTO users VALUES ('other','other','test',0)")
            conn.execute("UPDATE attachments SET owner_id='other' WHERE id=?",(aid,))
        self.assertEqual(self.send(aid).status_code,404)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],0)

    def test_stream_before_completion_then_history(self):
        aid=self.upload();rid=self.send(aid).json()['run_id'];self.controller()
        started=threading.Event();release=threading.Event()
        def model(preview,question,key,cancelled,on_delta=None,check=None):
            self.assertTrue(preview.startswith(b'\x89PNG'));self.assertEqual(question,'Co jest na zdjęciu?')
            on_delta('Fragment');started.set();release.wait(5);check();return 'Fragment i koniec.'
        with patch.object(media,'ask_model',model),concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(main.infer,self.run_row(rid));self.assertTrue(started.wait(5))
            with connect() as conn:
                events=conn.execute("SELECT payload FROM run_events WHERE run_id=? AND type='assistant.text.delta'",(rid,)).fetchall();self.assertEqual(events[0]['payload']['text'],'Fragment')
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM messages WHERE role='assistant'").fetchone()['n'],0)
            release.set();future.result(5)
        self.assertEqual(self.run_row(rid)['status'],'completed')
        self.assertEqual(self.client.get('/api/v1/conversations/'+self.cid+'/messages').json()['items'][-1]['content'],'Fragment i koniec.')

    def test_cancel_first_token_and_deleted_image_no_text_fallback(self):
        aid=self.upload();rid=self.send(aid).json()['run_id'];self.controller();started=threading.Event()
        def waiting(preview,question,key,cancelled,on_delta=None,check=None):
            started.set()
            while True:check();time.sleep(.01)
        with patch.object(media,'ask_model',waiting),concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(main.infer,self.run_row(rid));self.assertTrue(started.wait(5))
            self.assertEqual(self.client.post('/api/v1/runs/'+rid+'/cancel',headers={'Idempotency-Key':str(uuid4())}).status_code,202);future.result(5)
        self.assertEqual(self.run_row(rid)['status'],'cancelled')
        with connect() as conn:conn.execute("UPDATE system_mode SET controller_state='ready'")
        rid=self.send(aid).json()['run_id'];self.assertEqual(self.client.delete('/api/v1/files/'+aid).status_code,204)
        main.infer(self.run_row(rid));self.assertEqual(self.run_row(rid)['error_code'],'file_not_found')

    def test_v2_upgrade_backup_failure_then_success_preserves_images(self):
        aid=self.upload()
        with connect() as conn:
            conn.execute('DROP TABLE message_images');conn.execute('DELETE FROM schema_migrations WHERE version=3')
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):migrate()
        with connect() as conn:self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='message_images'").fetchone())
        migrate();self.assertTrue(list(config.BACKUPS.glob('*.sqlite3')))
        with connect() as conn:self.assertEqual(conn.execute('SELECT original FROM attachments WHERE id=?',(aid,)).fetchone()['original'],png())

"""Pliki: prawdziwe dekodery/SQLite/procesy, VLM jako kontrolowana atrapa HTTP."""
import concurrent.futures
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from uuid import uuid4
from PIL import Image,PngImagePlugin
from fastapi.testclient import TestClient
from app import config,main,media,voice,maintenance
from app.db import connect,migrate,migration_checksums
from app.model_process import ModelProcess
from test_native import DataCase,PASSWORD


def png():
    output=io.BytesIO();info=PngImagePlugin.PngInfo();info.add_text('private','secret metadata')
    Image.new('RGBA',(40,20),(0,0,0,0)).save(output,format='PNG',pnginfo=info)
    return output.getvalue()


def pdf(pages=2):
    # Mały poprawny PDF z rzeczywistą warstwą tekstową i tablicą xref.
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'']
    kids=[]
    for index in range(pages):
        page_id=len(objects)+1;stream_id=page_id+1;kids.append(f'{page_id} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {stream_id} 0 R >>'.encode())
        stream=f'BT /F1 16 Tf 10 50 Td (STRONA {index+1}) Tj ET'.encode()
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode()+stream+b'\nendstream')
    objects[1]=f'<< /Type /Pages /Count {pages} /Kids [{" ".join(kids)}] >>'.encode()
    result=b'%PDF-1.4\n';offsets=[0]
    for n,obj in enumerate(objects,1):
        offsets.append(len(result));result+=f'{n} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(result);result+=f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]:result+=f'{offset:010d} 00000 n \n'.encode()
    return result+f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


class MediaTests(DataCase):
    def setUp(self):
        super().setUp()
        self.guard=voice.VoiceService();self.stack.enter_context(patch.object(media,'guard',self.guard))
        self.client=TestClient(main.app,base_url=config.ORIGIN);self.addCleanup(self.client.close)
        self.client.headers['Origin']=config.ORIGIN
        self.client.post('/api/v1/auth/login',json={'username':'owner','password':PASSWORD})
        self.client.headers['X-CSRF-Token']=self.client.cookies.get('assistant_csrf')
        with connect() as conn:session=conn.execute('SELECT id,user_id FROM sessions').fetchone()
        self.key=(session['id'],session['user_id'],str(uuid4()))

    def upload(self,data=None,name='plik.png',jid=None):
        return self.client.post('/api/v1/media/jobs/'+(jid or str(uuid4()))+'/files',params={'name':name},content=png() if data is None else data)

    def operation(self,aid,op,body,jid=None):
        return self.client.post('/api/v1/media/jobs/'+(jid or str(uuid4()))+'/files/'+aid+'/'+op,json=body)

    def test_png_sanitized_private_original_download_and_no_auto_send(self):
        data=png();response=self.upload(data,'../../hello.html');self.assertEqual(response.status_code,201,response.text)
        aid=response.json()['id'];self.assertEqual(response.json()['filename'],'hello.html')
        preview=self.client.get('/api/v1/files/'+aid+'/preview');self.assertEqual(preview.status_code,200)
        with Image.open(io.BytesIO(preview.content)) as image:
            self.assertNotIn('private',image.info);self.assertEqual(image.getpixel((0,0)),(255,255,255))
        result=self.client.get('/api/v1/files/'+aid+'/download');self.assertEqual(result.content,data)
        self.assertIn('hello.png',result.headers['content-disposition'])
        self.assertEqual(result.headers['x-content-type-options'],'nosniff')
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],0)
        self.client.post('/api/v1/auth/logout')
        for suffix in ('','/preview','/download'):self.assertEqual(self.client.get('/api/v1/files/'+aid+suffix).status_code,401)

    def test_jpeg_rotation_and_pdf_page_text(self):
        image=Image.new('RGB',(30,10),'red');exif=Image.Exif();exif[274]=6
        stream=io.BytesIO();image.save(stream,format='JPEG',exif=exif)
        row=self.upload(stream.getvalue(),'x.jpg').json()
        with Image.open(io.BytesIO(self.client.get('/api/v1/files/'+row['id']+'/preview').content)) as result:self.assertEqual(result.size,(10,30))
        response=self.upload(pdf(),'x.pdf');self.assertEqual(response.status_code,201,response.text)
        row=response.json();self.assertEqual(row['pages'],2);self.assertIn('STRONA 1',row['text_layer'])
        result=self.operation(row['id'],'page',{'page':2});self.assertEqual(result.status_code,200,result.text)
        self.assertIn('STRONA 2',result.json()['text_layer'])
        result=self.operation(row['id'],'analyze',{'mode':'ocr'});self.assertEqual(result.json()['source'],'pdf_text')
        self.assertIn('STRONA 2',result.json()['text'])
        self.assertEqual(self.operation(row['id'],'page',{'page':3}).status_code,422)
        self.assertEqual(self.operation(row['id'],'analyze',{'tools':['shell']}).status_code,422)

    def test_malformed_empty_oversize_pages_and_cleanup(self):
        for data in (b'',b'<script>bad</script>',b'%PDF-broken',png()[:20],pdf(51)):
            self.assertGreaterEqual(self.upload(data).status_code,400)
        self.assertEqual(self.upload(b'x'*(media.MAX_UPLOAD+1)).status_code,413)
        self.assertFalse(list((config.DATA/'media-tmp').glob('*')))
        self.assertEqual(self.client.get('/api/v1/files').json()['items'],[])

    def test_blank_pdf_and_oversized_pixel_image(self):
        import pypdfium2 as pdfium
        with pdfium.PdfDocument.new() as document:
            page=document.new_page(200,100);page.close()
            output=io.BytesIO();document.save(output)
        response=self.upload(output.getvalue(),'blank.pdf')
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json()['text_layer'],'')
        output=io.BytesIO();Image.new('1',(4001,4000)).save(output,format='PNG')
        self.assertGreaterEqual(self.upload(output.getvalue()).status_code,400)
        self.assertFalse(list((config.DATA/'media-tmp').glob('*')))

    def test_auth_csrf_origin_and_other_owner(self):
        aid=self.upload().json()['id']
        response=self.client.post('/api/v1/media/jobs/'+str(uuid4())+'/files?name=x.png',content=png(),headers={'X-CSRF-Token':'wrong'})
        self.assertEqual(response.status_code,403)
        response=self.client.post('/api/v1/media/jobs/'+str(uuid4())+'/files?name=x.png',content=png(),headers={'Origin':'https://evil.test'})
        self.assertEqual(response.status_code,403)
        with connect() as conn:
            conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',('second','other','unused'))
            conn.execute('UPDATE attachments SET owner_id=\'second\' WHERE id=?',(aid,))
        self.assertEqual(self.client.get('/api/v1/files').json()['items'],[])
        for suffix in ('','/preview','/download'):self.assertEqual(self.client.get('/api/v1/files/'+aid+suffix).status_code,404)
        self.assertEqual(self.client.delete('/api/v1/files/'+aid).status_code,404)
        self.assertEqual(self.operation(aid,'page',{'page':1}).status_code,404)
        self.assertEqual(self.operation(aid,'analyze',{'mode':'ocr'}).status_code,404)

    def test_backup_restore_delete_and_copy_failure(self):
        aid=self.upload(pdf(),'x.pdf').json()['id'];copy=maintenance.backup()
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')):
            # Sam moduł nie usuwa danych, jeśli kopia się nie udała.
            self.assertEqual(self.client.delete('/api/v1/files/'+aid).status_code,503)
        self.assertEqual(self.client.get('/api/v1/files/'+aid).status_code,200)
        self.assertEqual(self.client.delete('/api/v1/files/'+aid).status_code,204)
        self.assertEqual(self.client.get('/api/v1/files/'+aid).status_code,404)
        maintenance.restore(copy)
        uid=self.user()
        with connect() as conn:
            row=media.owned(conn,aid,uid);self.assertEqual(row['original'],pdf());self.assertIn('STRONA 1',row['text_layer'])
        self.assertEqual(self.client.get('/api/v1/files/'+aid).status_code,401)

    def test_quota_cancel_gaming_and_missing_model(self):
        aid=self.upload().json()['id']
        self.assertEqual(self.operation(aid,'analyze',{}).status_code,503)
        with patch.object(media,'MAX_FILES',1):self.assertEqual(self.upload().status_code,409)
        jid=str(uuid4());self.client.post('/api/v1/media/jobs/'+jid+'/cancel')
        self.assertEqual(self.upload(jid=jid).status_code,409)
        with connect() as conn:conn.execute("UPDATE system_mode SET requested_mode='gaming'")
        self.assertEqual(self.upload().status_code,409)
        self.assertEqual(self.operation(aid,'analyze',{}).status_code,409)

    def test_decoder_real_process_timeout_no_partial_file(self):
        with patch.object(media,'DECODE_TIMEOUT',.0001):
            result=self.upload();self.assertEqual(result.status_code,504,result.text)
        self.assertFalse(list((config.DATA/'media-tmp').glob('*')))
        self.assertEqual(self.client.get('/api/v1/files').json()['items'],[])

    def vision_controller(self):
        models=config.DATA/'models';models.mkdir()
        for name in ('vision-model.gguf','vision-mmproj.gguf'):(models/name).write_bytes(b'test placeholder')
        stopped=threading.Event()
        def controller():
            while not stopped.wait(.02):
                with connect() as conn:conn.execute("UPDATE system_mode SET loaded_profile=requested_profile,controller_state='ready'")
        thread=threading.Thread(target=controller);thread.start()
        self.addCleanup(lambda:(stopped.set(),thread.join()))

    def test_vision_real_http_request_and_failure_returns_text_profile(self):
        aid=self.upload().json()['id'];self.vision_controller()
        bodies=[];broken=threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                bodies.append(json.loads(self.rfile.read(int(self.headers['content-length']))))
                if broken.is_set():self.send_response(500);self.end_headers();return
                self.send_response(200);self.end_headers()
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"KRIPAI TEST"}}]}\n\ndata: [DONE]\n\n')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
        self.addCleanup(lambda:(server.shutdown(),thread.join(),server.server_close()))
        with patch.object(config,'LLM','http://127.0.0.1:'+str(server.server_port)):
            response=self.operation(aid,'analyze',{'mode':'ocr'});self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['text'],'KRIPAI TEST')
            self.assertNotIn('tools',bodies[0]);self.assertIn('niezaufane',bodies[0]['messages'][0]['content'])
            self.assertTrue(bodies[0]['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            broken.set();self.assertEqual(self.operation(aid,'analyze',{}).status_code,503)
        with connect() as conn:self.assertEqual(conn.execute('SELECT requested_profile FROM system_mode').fetchone()['requested_profile'],'text')

    def test_cancel_and_gaming_during_vision(self):
        aid=self.upload().json()['id'];self.vision_controller()
        for gaming in (False,True):
            started=threading.Event()
            def waiting(preview,question,key,cancelled):
                started.set()
                while True:media.guard.permitted(key,cancelled);time.sleep(.02)
            with patch.object(media,'ask_model',waiting),concurrent.futures.ThreadPoolExecutor() as pool:
                jid=str(uuid4());future=pool.submit(self.operation,aid,'analyze',{},jid)
                self.assertTrue(started.wait(5))
                if gaming:
                    with connect() as conn:conn.execute("UPDATE system_mode SET requested_mode='gaming'")
                else:self.client.post('/api/v1/media/jobs/'+jid+'/cancel')
                self.assertEqual(future.result(5).status_code,409)
            with connect() as conn:self.assertEqual(conn.execute('SELECT requested_profile FROM system_mode').fetchone()['requested_profile'],'text')

    def test_process_profiles_do_not_overlap_and_gaming_stops(self):
        processes=[]
        def launch(*args,**kwargs):
            self.assertTrue(all(p.poll() is not None for p in processes))
            process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);processes.append(process);return process
        manager=ModelProcess(launch=launch,health=lambda:True);self.addCleanup(manager.close)
        for profile in ('text','vision','text'):self.assertEqual(manager.step('normal',profile),'ready')
        manager.step('gaming');self.assertTrue(all(p.poll() is not None for p in processes))
        self.assertEqual(len(processes),3)


class MediaMigrationTests(DataCase):
    def old_database(self):
        with connect() as conn:
            conn.execute('DROP TABLE message_sources');conn.execute('DROP TABLE rag_vectors');conn.execute('DROP TABLE rag_chunks');conn.execute('DROP TABLE rag_documents');conn.execute('ALTER TABLE runs DROP COLUMN rag_selection')
            conn.execute('DROP TABLE message_images')
            conn.execute('DROP TABLE attachments')
            conn.execute('ALTER TABLE system_mode DROP COLUMN requested_profile')
            conn.execute('ALTER TABLE system_mode DROP COLUMN loaded_profile')
            conn.execute('DELETE FROM schema_migrations WHERE version>=2')

    def test_upgrade_backup_and_old_restore(self):
        self.old_database();uid=self.user();old=maintenance.backup();migrate()
        with connect() as conn:self.assertEqual(len(conn.execute('SELECT * FROM schema_migrations').fetchall()),len(migration_checksums()))
        self.assertEqual(self.user(),uid);self.assertGreaterEqual(len(list(config.BACKUPS.glob('*.sqlite3'))),2)
        maintenance.restore(old)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],0)
        self.assertEqual(self.user(),uid)

    def test_upgrade_aborts_before_schema_change_if_backup_fails(self):
        self.old_database()
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):migrate()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM schema_migrations').fetchone()['n'],1)
            self.assertIsNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='attachments'").fetchone())

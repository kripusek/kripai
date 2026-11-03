"""Wznawianie bajtów, rzeczywisty SQLite/dekoder, spójny commit i odmowy dostępu."""
import concurrent.futures,hashlib,sqlite3,threading,time,unittest
from unittest.mock import patch
from contextlib import closing
from uuid import uuid4
import test_native
from test_media import png
from app import config,media,uploads,maintenance
from app.db import connect,migrate
from app.models import UploadStart

class UploadTests(test_native.DataCase):
    def setUp(self):
        super().setUp();media.guard.stopping.clear();media.guard.recent.clear()
        self.uid=self.user();self.sid=str(uuid4());self.key=(self.sid,self.uid,str(uuid4()));self.data=png()
        with connect() as conn:conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',(self.sid,self.uid,b'fixture-token',b'fixture-csrf',time.time()+600))
    def begin(self,data=None,**extra):
        data=self.data if data is None else data;body=dict(id=str(uuid4()),name='plik.png',size=len(data),sha256=hashlib.sha256(data).hexdigest());body.update(extra)
        result=uploads.start(UploadStart(**body),self.key);return result['id']
    def full(self,**extra):
        identity=self.begin(**extra);uploads.append(identity,0,self.data,self.key);return identity
    def code(self,code,fn,*args):
        with self.assertRaises(media.MediaError) as error:fn(*args)
        self.assertEqual(error.exception.code,code)
    def test_resume_repeated_chunks_and_completion_without_duplicate_file(self):
        identity=self.begin();half=len(self.data)//2
        first=uploads.append(identity,0,self.data[:half],self.key);self.assertEqual(first['received'],half);self.assertNotIn('data',first)
        migrate();self.assertEqual(uploads.get(identity,self.key)['received'],half)
        self.assertEqual(uploads.append(identity,0,self.data[:half],self.key)['received'],half)
        uploads.append(identity,half,self.data[half:],self.key);result=uploads.finish(identity,self.key);self.assertEqual(result['id'],identity)
        with patch.object(media,'decode',side_effect=AssertionError('no second decode')):
            self.assertEqual(uploads.finish(identity,self.key)['id'],identity);self.assertEqual(uploads.finish(identity,(self.sid,self.uid,str(uuid4())))['id'],identity)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],1);self.assertEqual(media.owned(conn,identity,self.uid)['original'],self.data)
            self.assertEqual(conn.execute('SELECT length(data) AS n FROM upload_sessions').fetchone()['n'],0)
    def test_conflicting_offsets_sizes_digest_and_incomplete_data(self):
        identity=self.begin();uploads.append(identity,0,self.data[:10],self.key)
        for offset,data in [(0,b'different'),(20,b'later')]:self.code('upload_offset_conflict',uploads.append,identity,offset,data,self.key)
        self.code('upload_incomplete',uploads.finish,identity,self.key)
        self.code('upload_chunk_size',uploads.append,identity,10,b'x'*(uploads.CHUNK+1),self.key)
        self.code('upload_chunk_size',uploads.append,identity,10,b'x'*len(self.data),self.key)
        wrong=self.full(sha256='0'*64)
        with patch.object(media,'decode',side_effect=AssertionError('hash first')):self.code('upload_digest_mismatch',uploads.finish,wrong,(self.sid,self.uid,str(uuid4())))
    def test_creation_is_idempotent_but_changed_metadata_is_not(self):
        identity=self.begin();body=UploadStart(id=identity,name='plik.png',size=len(self.data),sha256=hashlib.sha256(self.data).hexdigest())
        self.assertEqual(uploads.start(body,self.key)['id'],identity)
        self.code('upload_conflict',uploads.start,body.model_copy(update={'name':'other.png'}),self.key)
    def test_expired_completed_receipt_reports_gone_to_clear_cached_identity(self):
        identity=self.full();uploads.finish(identity,self.key)
        with connect() as conn:conn.execute('UPDATE upload_sessions SET expires_at=0 WHERE id=?',(identity,))
        body=UploadStart(id=identity,name='plik.png',size=len(self.data),sha256=hashlib.sha256(self.data).hexdigest())
        self.code('upload_expired',uploads.start,body,self.key)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],1)
            self.assertEqual(media.owned(conn,identity,self.uid)['original'],self.data)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM upload_sessions').fetchone()['n'],0)
        fresh=self.begin();self.assertNotEqual(fresh,identity)
    def test_session_binding_foreign_owner_and_revocation(self):
        identity=self.begin();other_sid=str(uuid4());other_uid=str(uuid4())
        with connect() as conn:
            hashed=conn.execute('SELECT password_hash FROM users WHERE id=?',(self.uid,)).fetchone()['password_hash'];conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(other_uid,'other',hashed))
            conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',(other_sid,other_uid,b'other-token',b'other-csrf',time.time()+600))
        self.code('upload_not_found',uploads.get,identity,(other_sid,other_uid));self.assertEqual(uploads.list_pending((other_sid,other_uid))['items'],[])
        self.assertEqual(uploads.discard((other_sid,other_uid))['discarded'],0)
        with connect() as conn:conn.execute('UPDATE sessions SET revoked_at=now() WHERE id=?',(self.sid,))
        self.code('login_required',uploads.get,identity,self.key)
    def test_cancelled_finish_keeps_bytes_for_resume(self):
        identity=self.full()
        def cancelled(data,page,key,flag):flag.set();return {'media_type':'image/png','pages':1,'text_layer':''},png()
        with patch.object(media,'decode',side_effect=cancelled):self.code('media_cancelled',uploads.finish,identity,self.key)
        self.assertEqual(uploads.get(identity,self.key)['status'],'uploading');self.assertEqual(uploads.finish(identity,(self.sid,self.uid,str(uuid4())))['id'],identity)
    def test_failed_atomic_store_rolls_back_attachment_and_receipt(self):
        identity=self.full();original=media.store
        def fail(*args,**kwargs):original(*args,**kwargs);raise OSError('fixture transaction failure')
        with patch.object(media,'store',side_effect=fail),self.assertRaises(OSError):uploads.finish(identity,self.key)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],0)
        self.assertEqual(uploads.get(identity,self.key)['status'],'uploading');self.assertEqual(uploads.finish(identity,(self.sid,self.uid,str(uuid4())))['id'],identity)
    def test_storage_credit_active_quota_and_no_file_resurrection(self):
        identity=self.full()
        with patch.object(uploads,'MAX_ACTIVE',1):self.code('upload_quota',self.begin)
        info={'media_type':'image/png','pages':1,'text_layer':''};preview=png()
        with patch.object(media,'MAX_STORAGE',len(self.data)+len(preview)),patch.object(media,'decode',return_value=(info,preview)):uploads.finish(identity,self.key)
        with connect() as conn:conn.execute('DELETE FROM attachments WHERE id=?',(identity,))
        self.code('upload_file_gone',uploads.get,identity,self.key)
        self.code('upload_file_gone',uploads.finish,identity,(self.sid,self.uid,str(uuid4())))
    def test_parallel_retry_of_same_chunk_is_once_only(self):
        identity=self.begin()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:uploads.append(identity,0,self.data[:20],self.key),range(2)))
        self.assertEqual([r['received'] for r in results],[20,20]);self.assertEqual(uploads.get(identity,self.key)['received'],20)
    def test_cleanup_and_discard_require_backup_before_bytes_are_removed(self):
        identity=self.full()
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')),self.assertRaises(OSError):uploads.discard(self.key)
        self.assertEqual(uploads.get(identity,self.key)['received'],len(self.data))
        with connect() as conn:conn.execute('UPDATE upload_sessions SET expires_at=0 WHERE id=?',(identity,))
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')),self.assertRaises(OSError):uploads.cleanup()
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM upload_sessions').fetchone()['n'],1)
        uploads.cleanup()
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM upload_sessions').fetchone()['n'],0)
        self.assertTrue(list(config.BACKUPS.glob('*.sqlite3')))
    def test_discard_recreate_same_id_during_decode_cannot_commit_stale_attempt(self):
        identity=self.full();original_decode=media.decode
        def recreate(data,page,key,cancelled):
            uploads.discard(key)
            self.full(id=identity)
            return original_decode(data,page,key,cancelled)
        with patch.object(media,'decode',side_effect=recreate):self.code('upload_conflict',uploads.finish,identity,self.key)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],0)
        self.assertEqual(uploads.get(identity,self.key)['received'],len(self.data))
        self.assertEqual(uploads.finish(identity,(self.sid,self.uid,str(uuid4())))['id'],identity)
    def test_final_transaction_rechecks_mode_and_cancellation(self):
        identity=self.full();original_permitted=media.guard.permitted
        # Druga kontrola występuje po dekodowaniu; zmiana tuż po niej nadal blokuje commit.
        calls=0
        def after_check(key,flag):
            nonlocal calls
            original_permitted(key,flag);calls+=1
            if calls==2:
                with connect() as conn:conn.execute("UPDATE system_mode SET requested_mode='gaming'")
        info={'media_type':'image/png','pages':1,'text_layer':''}
        with patch.object(media,'decode',return_value=(info,self.data)),patch.object(media.guard,'permitted',side_effect=after_check):self.code('gaming_mode',uploads.finish,identity,self.key)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM attachments').fetchone()['n'],0)
            conn.execute("UPDATE system_mode SET requested_mode='normal'")
        calls=0
        def after_cancel(key,flag):
            nonlocal calls
            original_permitted(key,flag);calls+=1
            if calls==2:flag.set()
        with patch.object(media,'decode',return_value=(info,self.data)),patch.object(media.guard,'permitted',side_effect=after_cancel):self.code('media_cancelled',uploads.finish,identity,(self.sid,self.uid,str(uuid4())))
        self.assertEqual(uploads.get(identity,self.key)['status'],'uploading')
    def test_backup_holds_write_reservation_and_contains_removed_bytes(self):
        for operation in ('discard','cleanup'):
            with self.subTest(operation=operation):
                identity=self.full();attempted=threading.Event();original_backup=maintenance.backup;saved=[]
                if operation=='cleanup':
                    with connect() as conn:conn.execute('UPDATE upload_sessions SET expires_at=0 WHERE id=?',(identity,))
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future=None
                    def writer():
                        attempted.set()
                        return uploads.append(identity,0,self.data,self.key)
                    def backup():
                        nonlocal future
                        future=pool.submit(writer);self.assertTrue(attempted.wait(2))
                        self.assertFalse(future.done())
                        saved.append(original_backup());return saved[-1]
                    with patch.object(maintenance,'backup',side_effect=backup):
                        if operation=='discard':self.assertEqual(uploads.discard(self.key)['discarded'],1)
                        else:uploads.cleanup()
                    with self.assertRaises(media.MediaError) as error:future.result(timeout=5)
                    self.assertEqual(error.exception.code,'upload_not_found')
                with closing(sqlite3.connect(saved[0])) as conn:self.assertEqual(conn.execute('SELECT data FROM upload_sessions WHERE id=?',(identity,)).fetchone()[0],self.data)
    def test_v6_upgrade_backup_failure_preserves_old_schema_then_migrates(self):
        with connect() as conn:
            for name in ('visual_vectors','visual_pages','visual_documents','upload_sessions'):conn.execute('DROP TABLE '+name)
            conn.execute('ALTER TABLE message_images DROP COLUMN page')
            conn.execute('DELETE FROM schema_migrations WHERE version>=7')
        with patch.object(maintenance,'backup',side_effect=OSError('disk full')),self.assertRaises(OSError):migrate()
        with connect() as conn:self.assertEqual(conn.execute('SELECT max(version) AS n FROM schema_migrations').fetchone()['n'],6)
        migrate()
        from app.db import migration_checksums
        with connect() as conn:self.assertEqual(conn.execute('SELECT max(version) AS n FROM schema_migrations').fetchone()['n'],len(migration_checksums()))

class UploadAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp();self.data=png()
    def begin(self):
        identity=str(uuid4());response=self.base.post('/media/uploads',{'id':identity,'name':'test.png','size':len(self.data),'sha256':hashlib.sha256(self.data).hexdigest()});self.assertEqual(response.status_code,200,response.text);return identity
    def test_chunks_real_decoder_resume_and_lost_completion_response(self):
        identity=self.begin();path='/api/v1/media/uploads/'+identity+'/chunks';client=self.base.client
        response=client.put(path,params={'offset':0},content=self.data[:20]);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(client.get('/api/v1/media/uploads/'+identity).json()['received'],20)
        self.assertEqual(client.put(path,params={'offset':20},content=self.data[20:]).status_code,200)
        route='/media/jobs/'+str(uuid4())+'/uploads/'+identity+'/complete';result=self.base.post(route,{});self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.base.post('/media/jobs/'+str(uuid4())+'/uploads/'+identity+'/complete',{}).json()['id'],result.json()['id'])
        self.assertEqual(client.get('/api/v1/files').json()['items'][0]['id'],identity)
    def test_chunk_body_limits_csrf_origin_auth_and_invalid_metadata(self):
        identity=self.begin();client=self.base.client;path='/api/v1/media/uploads/'+identity+'/chunks?offset=0'
        self.assertEqual(client.put(path,content=b'x'*(uploads.CHUNK+1)).status_code,413)
        self.assertEqual(client.put(path,content=self.data,headers={'X-CSRF-Token':'wrong'}).status_code,403)
        self.assertEqual(client.put(path,content=self.data,headers={'Origin':'https://evil.invalid'}).status_code,403)
        self.assertEqual(client.get('/api/v1/media/uploads/'+identity).json()['received'],0)
        self.assertEqual(self.base.post('/media/uploads',{'id':str(uuid4()),'name':'x','size':True,'sha256':'0'*64}).status_code,422)
        client.cookies.clear();self.assertEqual(client.put(path,content=self.data).status_code,401)

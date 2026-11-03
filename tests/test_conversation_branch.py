"""SQLite: kopia prefiksu, ACL, referencje i atomowosc transakcji."""
import time
from unittest.mock import patch
from uuid import uuid4
from test_native import DataCase
from app.db import connect
from app import conversation_branch as module
from app.conversation_branch import BranchError,branch


class ConversationBranchTests(DataCase):
    def setUp(self):
        super().setUp();self.uid=self.user();self.cid=self.conversation();self.sid=self.session();self.ids=[]
        with connect() as conn:
            for role,text in [('user','first'),('assistant','answer'),('user','later')]:
                mid=str(uuid4());self.ids.append(mid)
                conn.execute('INSERT INTO messages(id,conversation_id,role,content,client_message_id) VALUES (?,?,?,?,?)',(mid,self.cid,role,text,str(uuid4())))
    def session(self,uid=None):
        sid=str(uuid4())
        with connect() as conn:conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',(sid,uid or self.uid,uuid4().bytes,uuid4().bytes,time.time()+600))
        return sid
    def other_user(self):
        uid=str(uuid4())
        with connect() as conn:
            hashed=conn.execute('SELECT password_hash FROM users WHERE id=?',(self.uid,)).fetchone()['password_hash']
            conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(uid,uid,hashed))
        return uid
    def fork(self,cid=None,uid=None,mid=None,sid=None):
        with connect() as conn:return branch(conn,cid or self.cid,uid or self.uid,mid or self.ids[1],sid or self.sid)
    def expect(self,code,status,**kwargs):
        with self.assertRaises(BranchError) as error:self.fork(**kwargs)
        self.assertEqual((error.exception.code,error.exception.status),(code,status))
    def snapshot(self):
        with connect() as conn:
            names=[row['name'] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {name:conn.execute('SELECT * FROM "'+name+'" ORDER BY 1').fetchall() for name in names}
    def attachment(self,uid):
        aid=str(uuid4())
        with connect() as conn:conn.execute("INSERT INTO attachments(id,owner_id,filename,media_type,original,preview,pages,current_page) VALUES (?,?,'file.png','image/png',X'01',X'02',1,1)",(aid,uid))
        return aid
    def test_inclusive_prefix_fresh_ids_and_original_unchanged_no_runs_or_flags(self):
        with connect() as conn:
            conn.execute('UPDATE conversations SET title=? WHERE id=?',('x'*200,self.cid))
            run=str(uuid4());conn.execute("INSERT INTO runs(id,conversation_id,user_message_id,status,allow_web,allow_github) VALUES (?,?,?,'completed',1,1)",(run,self.cid,self.ids[0]))
            conn.execute("INSERT INTO run_events(run_id,seq,event_id,type,payload) VALUES (?,1,?,'fixture','{}')",(run,str(uuid4())))
        before=self.snapshot();result=self.fork();after=self.snapshot()
        self.assertEqual(set(result),{'id','title','created_at','copied_messages'});self.assertNotEqual(result['id'],self.cid);self.assertEqual(result['copied_messages'],2);self.assertLessEqual(len(result['title']),200)
        copied=[row for row in after['messages'] if row['conversation_id']==result['id']]
        source=[row for row in before['messages'] if row['conversation_id']==self.cid][:2]
        for old,new in zip(source,copied):
            self.assertNotEqual(old['id'],new['id']);self.assertNotEqual(old['seq'],new['seq']);self.assertIsNone(new['client_message_id'])
            for name in ('role','content','created_at'):self.assertEqual(new[name],old[name])
        after['conversations']=[row for row in after['conversations'] if row['id']!=result['id']]
        after['messages']=[row for row in after['messages'] if row['conversation_id']!=result['id']]
        self.assertEqual(after,before)
    def test_sources_owned_attachments_only_and_image_session_rebound(self):
        owned=self.attachment(self.uid);foreign=self.attachment(self.other_user());old_session=self.session()
        with connect() as conn:
            conn.execute("INSERT INTO tool_sources VALUES (?,1,'web','https://example.invalid/','title','literal source')",(self.ids[1],))
            for ordinal,aid in enumerate((owned,foreign),1):conn.execute('INSERT INTO message_sources VALUES (?,?,?,?,?)',(self.ids[1],ordinal,aid,1,'document excerpt'))
            conn.execute('INSERT INTO message_images(message_id,attachment_id,session_id,page) VALUES (?,?,?,2)',(self.ids[0],owned,old_session))
            conn.execute('INSERT INTO message_images(message_id,attachment_id,session_id,page) VALUES (?,?,?,2)',(self.ids[1],foreign,old_session))
            attachments=conn.execute('SELECT * FROM attachments ORDER BY id').fetchall()
        result=self.fork()
        with connect() as conn:
            copies=conn.execute('SELECT id FROM messages WHERE conversation_id=? ORDER BY seq',(result['id'],)).fetchall();mids=[row['id'] for row in copies]
            self.assertEqual(conn.execute('SELECT * FROM attachments ORDER BY id').fetchall(),attachments)
            sources=conn.execute('SELECT s.* FROM message_sources s JOIN messages m ON m.id=s.message_id WHERE m.conversation_id=?',(result['id'],)).fetchall()
            self.assertEqual(len(sources),1);self.assertEqual(sources[0]['attachment_id'],owned);self.assertEqual(sources[0]['message_id'],mids[1])
            images=conn.execute('SELECT i.* FROM message_images i JOIN messages m ON m.id=i.message_id WHERE m.conversation_id=?',(result['id'],)).fetchall()
            self.assertEqual(images,[{'message_id':mids[0],'attachment_id':owned,'session_id':self.sid,'page':2}])
            web=conn.execute('SELECT * FROM tool_sources WHERE message_id=?',(mids[1],)).fetchall();self.assertEqual(len(web),1);self.assertEqual(web[0]['excerpt'],'literal source')
    def test_ownership_point_roles_and_current_session(self):
        other=self.other_user();other_sid=self.session(other);other_cid=self.conversation()
        self.expect('not_found',404,uid=other,sid=other_sid)
        self.expect('not_found',404,cid=str(uuid4()))
        self.expect('not_found',404,cid=other_cid)
        self.expect('not_found',404,mid=str(uuid4()))
        self.expect('branch_point',422,mid=self.ids[0])
        self.expect('login_required',401,sid=other_sid)
        self.expect('login_required',401,sid=str(uuid4()))
        with connect() as conn:conn.execute('UPDATE sessions SET expires_at=0 WHERE id=?',(self.sid,))
        self.expect('login_required',401)
        with connect() as conn:conn.execute('UPDATE sessions SET expires_at=now()+600,revoked_at=now() WHERE id=?',(self.sid,))
        self.expect('login_required',401)
    def test_active_source_run_blocks_branch_other_source_does_not(self):
        run=str(uuid4())
        with connect() as conn:conn.execute("INSERT INTO runs(id,conversation_id,user_message_id,status) VALUES (?,?,?,'queued')",(run,self.cid,self.ids[0]))
        for status in ('queued','preparing_context','generating','cancelling'):
            with connect() as conn:conn.execute('UPDATE runs SET status=? WHERE id=?',(status,run))
            self.expect('generation_busy',409)
        with connect() as conn:conn.execute("UPDATE runs SET status='failed' WHERE id=?",(run,))
        other=self.conversation();mid=str(uuid4())
        with connect() as conn:
            conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user','other active run')",(mid,other))
            conn.execute("INSERT INTO runs(id,conversation_id,user_message_id,status) VALUES (?,?,?,'generating')",(str(uuid4()),other,mid))
        self.assertEqual(self.fork()['copied_messages'],2)
    def test_transaction_rollback_removes_all_copies(self):
        before=self.snapshot()
        with self.assertRaises(OSError),connect() as conn:
            branch(conn,self.cid,self.uid,self.ids[1],self.sid);raise OSError('fixture commit failure')
        self.assertEqual(self.snapshot(),before)
    def test_limits_reject_without_truncation_and_utf8_counts_bytes(self):
        before=self.snapshot()
        with patch.object(module,'MAX_MESSAGES',1):self.expect('branch_too_large',413)
        with patch.object(module,'MAX_TEXT_BYTES',10):self.expect('branch_too_large',413)
        self.assertEqual(self.snapshot(),before)
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE id=?',('\u0105'*5,self.ids[0]));conn.execute('UPDATE messages SET content=? WHERE id=?',('ok',self.ids[1]))
        with patch.object(module,'MAX_TEXT_BYTES',11):self.expect('branch_too_large',413)
        with patch.object(module,'MAX_TEXT_BYTES',12):self.assertEqual(self.fork()['copied_messages'],2)
    def test_actual_1000_message_limit_and_8mib_limit(self):
        with connect() as conn:
            for _ in range(999):conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user','x')",(str(uuid4()),self.cid))
            point=str(uuid4());conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'assistant','end')",(point,self.cid))
        self.expect('branch_too_large',413,mid=point)
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE id=?',('x'*module.MAX_TEXT_BYTES,self.ids[0]))
        self.expect('branch_too_large',413)
    def test_malformed_stored_text_rolls_back_without_new_conversation(self):
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE id=?',(b'not-text',self.ids[0]))
        before=self.snapshot();self.expect('branch_invalid_data',500);self.assertEqual(self.snapshot(),before)

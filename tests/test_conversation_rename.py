"""Rzeczywisty SQLite: wlasciciel, walidacja i zachowanie danych rozmowy."""
import unittest
from uuid import uuid4
from test_native import DataCase
from app.db import connect
from app.conversations import ConversationError,normalize_title,rename


class ConversationRenameTests(DataCase):
    def setUp(self):
        super().setUp();self.uid=self.user();self.cid=self.conversation()
    def expect(self,code,status,fn,*args):
        with self.assertRaises(ConversationError) as error:fn(*args)
        self.assertEqual((error.exception.code,error.exception.status),(code,status))
    def snapshot(self):
        with connect() as conn:
            names=[row['name'] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {name:conn.execute('SELECT * FROM "'+name+'" ORDER BY 1').fetchall() for name in names}
    def test_rename_preserves_all_history_sources_active_runs_and_other_rows(self):
        self.conversation();message=str(uuid4());run=str(uuid4())
        with connect() as conn:
            conn.execute("UPDATE conversations SET title='before',updated_at=1 WHERE id=?",(self.cid,))
            conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user','original text')",(message,self.cid))
            conn.execute("INSERT INTO runs(id,conversation_id,user_message_id,status) VALUES (?,?,?,'generating')",(run,self.cid,message))
            conn.execute("INSERT INTO tool_sources VALUES (?,1,'web','https://example.invalid/','source title','original excerpt')",(message,))
        before=self.snapshot();result=rename(self.cid,self.uid,'  New title  ');after=self.snapshot()
        self.assertEqual(set(result),{'id','title','updated_at'});self.assertEqual(result['id'],self.cid);self.assertEqual(result['title'],'New title');self.assertGreater(result['updated_at'],1)
        for row in before['conversations']:
            if row['id']==self.cid:row.update(title=result['title'],updated_at=result['updated_at'])
        self.assertEqual(before,after)
    def test_unknown_and_foreign_conversation_share_404_and_do_not_mutate(self):
        foreign=str(uuid4())
        with connect() as conn:
            hashed=conn.execute('SELECT password_hash FROM users WHERE id=?',(self.uid,)).fetchone()['password_hash']
            conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(foreign,'other',hashed))
        before=self.snapshot()
        self.expect('not_found',404,rename,self.cid,foreign,'changed')
        self.expect('not_found',404,rename,str(uuid4()),self.uid,'changed')
        self.assertEqual(before,self.snapshot())
    def test_invalid_titles_leave_database_unchanged(self):
        before=self.snapshot()
        for title in ('','   ','x'*201,'x\n','x\r','\tx','a\0b','a\x7fb','a\x85b','a\u2028b','a\u2029b','a\ud800b',None,42,True,[],{}):
            with self.subTest(title=repr(title)):self.expect('conversation_title',422,rename,self.cid,self.uid,title)
        self.assertEqual(before,self.snapshot())
    def test_bound_parameters_preserve_unicode_and_sql_as_literal_text(self):
        for title in ('a','x'*200,'Za\u017c\u00f3\u0142\u0107 \U0001f600',"x'; DELETE FROM conversations; --"):
            with self.subTest(title=title):self.assertEqual(rename(self.cid,self.uid,title)['title'],title)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM conversations').fetchone()['n'],1)
    def test_normalized_whitespace_and_repeated_request(self):
        self.assertEqual(normalize_title(' \u00a0Title \u00a0'),'Title')
        self.assertEqual(rename(self.cid,self.uid,' first ')['title'],'first')
        self.assertEqual(rename(self.cid,self.uid,'first')['title'],'first')

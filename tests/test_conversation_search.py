"""SQLite: literalny Unicode, ACL, limity skanowania i kursor bez utraty rekordow."""
import sqlite3
from unittest.mock import patch
from uuid import uuid4
from test_native import DataCase
from app.db import connect
from app import conversation_search as module
from app.conversation_search import SearchError,search


class ConversationSearchTests(DataCase):
    def setUp(self):
        super().setUp();self.uid=self.user();self.cid=self.conversation()
    def messages(self,texts,cid=None):
        with connect() as conn:
            for number,text in enumerate(texts):
                conn.execute('INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,?,?)',(str(uuid4()),cid or self.cid,'assistant' if number%2 else 'user',text))
            return [row['seq'] for row in conn.execute('SELECT seq FROM messages WHERE conversation_id=? ORDER BY seq DESC',(cid or self.cid,))]
    def expect(self,code,query,cursor=None,limit=20):
        with self.assertRaises(SearchError) as error:search(self.uid,query,cursor,limit)
        self.assertEqual((error.exception.code,error.exception.status),(code,422))
    def test_owner_acl_precedes_limit_and_search_uses_message_content_only(self):
        expected=self.messages(['Own NEEDLE content','no match'])
        foreign=str(uuid4());other=str(uuid4())
        with connect() as conn:
            hashed=conn.execute('SELECT password_hash FROM users WHERE id=?',(self.uid,)).fetchone()['password_hash']
            conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(foreign,'other',hashed))
            conn.execute("INSERT INTO conversations(id,owner_id,title) VALUES (?,?,'foreign title')",(other,foreign))
            conn.execute("UPDATE conversations SET title='needle title' WHERE id=?",(self.cid,))
        self.messages(['needle foreign']*2100,other)
        result=search(self.uid,'needle')
        self.assertEqual([row['seq'] for row in result['items']],[expected[-1]])
        self.assertEqual(result['items'][0]['conversation_id'],self.cid)
        self.assertEqual(result['scanned_messages'],2);self.assertFalse(result['partial']);self.assertIsNone(result['next_cursor'])
        self.assertEqual(search(self.uid,'title')['items'],[])
    def test_unicode_folding_excerpt_tracks_original_positions(self):
        contents=['\u00df'*3000+'TARGET'+'tail'*300,'x'*4000+'Stra\u00dfe'+'x'*4000,'x'*4000+'ffi'*120+'tail'*300,'\u00dft']
        self.messages(contents)
        for query,source,expected in [('target',contents[0],'TARGET'),('STRASSE',contents[1],'Stra\u00dfe'),('\ufb03'*120,contents[2],'ffi'),('st',contents[3],'\u00dft')]:
            with self.subTest(query=query):
                items=search(self.uid,query)['items'];matching=[item for item in items if expected in item['excerpt']]
                self.assertTrue(matching)
                for item in matching:self.assertLessEqual(len(item['excerpt']),240);self.assertIn(item['excerpt'],source)
    def test_pagination_has_no_duplicates_or_missed_messages(self):
        expected=self.messages(['needle '+str(index) for index in range(57)])
        actual=[];cursor=None
        while True:
            page=search(self.uid,'needle',cursor,7);actual.extend(row['seq'] for row in page['items'])
            self.assertLessEqual(len(page['items']),7);self.assertLessEqual(page['scanned_messages'],2000)
            self.assertEqual(page['partial'],page['next_cursor'] is not None)
            cursor=page['next_cursor']
            if cursor is None:break
        self.assertEqual(actual,expected);self.assertEqual(len(actual),len(set(actual)))
    def test_empty_scanned_page_has_cursor_and_next_page_finds_older_match(self):
        expected=self.messages(['old needle']+['unrelated']*2000)
        first=search(self.uid,'needle');self.assertEqual(first['items'],[]);self.assertEqual(first['scanned_messages'],2000);self.assertTrue(first['partial'])
        self.assertEqual(first['next_cursor'],str(expected[-2]))
        second=search(self.uid,'needle',first['next_cursor']);self.assertEqual([row['seq'] for row in second['items']],[expected[-1]])
        self.assertEqual(second['scanned_messages'],1);self.assertIsNone(second['next_cursor']);self.assertFalse(second['partial'])
    def test_literal_queries_and_boundaries(self):
        literal="%_'; DELETE FROM messages; --";self.messages([literal,'plain','a'*120])
        self.assertEqual(search(self.uid,literal)['items'][0]['excerpt'],literal)
        self.assertEqual(len(search(self.uid,' aa ')['items']),1)
        self.assertEqual(len(search(self.uid,'a'*120)['items']),1)
        self.assertEqual(search(self.uid,'absent',str(module.MAX_SEQ))['items'],[])
        for query in ('','a',' '*5,'a'*121,None,12,True,[]):self.expect('search_query',query)
        for cursor in ('','0','-1','1.0','+1',' 1','1 ','\u0661',str(module.MAX_SEQ+1),0,-1,module.MAX_SEQ+1,True,1.0,[]):self.expect('search_cursor','aa',cursor)
        for limit in (0,21,-1,True,1.0,'1',None):self.expect('search_limit','aa',limit=limit)
    def test_read_only_authorizer_and_read_snapshot_allow_concurrent_writer(self):
        original=self.messages(['needle']*3);open_db=module.open_db;original_excerpt=module.excerpt;traces=[];actions=[];inserted=False
        denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE}
        def authorized_open():
            conn=open_db()
            def authorize(action,*args):
                actions.append(action)
                return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK
            conn.set_authorizer(authorize);conn.set_trace_callback(traces.append);return conn
        def insert_during_read(content,query):
            nonlocal inserted
            if not inserted:inserted=True;self.messages(['new needle'])
            return original_excerpt(content,query)
        with patch.object(module,'open_db',side_effect=authorized_open),patch.object(module,'excerpt',side_effect=insert_during_read):page=search(self.uid,'needle')
        self.assertEqual([row['seq'] for row in page['items']],original)
        self.assertEqual(page['scanned_messages'],3);self.assertIsNone(page['next_cursor'])
        self.assertIn('BEGIN',traces);self.assertNotIn('BEGIN IMMEDIATE',traces);self.assertFalse(denied.intersection(actions))
        with connect() as conn:
            contents=conn.execute('SELECT content FROM messages ORDER BY seq').fetchall()
            self.assertEqual([row['content'] for row in contents],['needle']*3+['new needle'])

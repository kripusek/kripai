"""HTTP wyszukiwania i przejścia do starszej wiadomości, sesja oraz owner ACL."""
import unittest
from uuid import uuid4
from unittest.mock import patch
import test_native
from app import conversation_search
from app.db import connect

class HistorySearchAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp();self.cid=self.base.post('/conversations',{'title':'Historia'}).json()['id'];self.rows=[]
        with connect() as conn:
            for index in range(110):
                text='Starsza wiadomość zażółć — kod HISTORIA_SLOWO' if index==4 else 'Wiadomość '+str(index)
                self.rows.append(conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'user',?) RETURNING seq",(str(uuid4()),self.cid,text)).fetchone()['seq'])
    def test_search_and_open_exact_old_hit_then_latest_page(self):
        client=self.base.client;route='/api/v1/conversations/'+self.cid+'/messages'
        latest=client.get(route,params={'limit':50}).json()['items'];self.assertFalse(any(r['seq']==self.rows[4] for r in latest))
        response=client.get('/api/v1/conversations/search',params={'q':'ZAŻÓŁĆ'});self.assertEqual(response.status_code,200,response.text);items=response.json()['items'];self.assertEqual(len(items),1);self.assertEqual(items[0]['seq'],self.rows[4])
        old=client.get(route,params={'limit':50,'at':items[0]['seq']});self.assertEqual(old.status_code,200,old.text);self.assertEqual(old.json()['items'][-1]['seq'],self.rows[4]);self.assertIn('HISTORIA_SLOWO',old.json()['items'][-1]['content'])
        self.assertEqual(client.get(route,params={'limit':50}).json()['items'][-1]['seq'],self.rows[-1])
    def test_acl_invalid_at_and_search_cursors(self):
        client=self.base.client;route='/api/v1/conversations/'+self.cid+'/messages'
        self.assertEqual(client.get(route,params={'at':self.rows[4],'cursor':'1'}).status_code,422);self.assertEqual(client.get(route,params={'at':9999999}).status_code,404)
        self.assertEqual(client.get('/api/v1/conversations/search',params={'q':'tekst','cursor':'invalid'}).status_code,422)
        with connect() as conn:
            hashed=conn.execute("SELECT password_hash FROM users WHERE username='owner'").fetchone()['password_hash'];conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',('foreign','foreign',hashed));conn.execute('UPDATE conversations SET owner_id=? WHERE id=?',('foreign',self.cid))
        self.assertEqual(client.get('/api/v1/conversations/search',params={'q':'HISTORIA_SLOWO'}).json()['items'],[]);self.assertEqual(client.get(route,params={'at':self.rows[4]}).status_code,404)
        client.cookies.clear();self.assertEqual(client.get('/api/v1/conversations/search',params={'q':'tekst'}).status_code,401)
    def test_empty_scan_page_keeps_cursor_for_older_hits(self):
        client=self.base.client
        with patch.object(conversation_search,'MAX_SCAN',10):
            first=client.get('/api/v1/conversations/search',params={'q':'HISTORIA_SLOWO'}).json();self.assertEqual(first['items'],[]);self.assertTrue(first['partial']);self.assertIsNotNone(first['next_cursor'])

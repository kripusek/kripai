"""Odgałęzienie HTTP: atomowe ponowienia, własność, prefiks bez uruchomienia AI."""
import concurrent.futures,unittest
from uuid import uuid4
import test_native
from app.db import connect

class BranchAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp();self.cid=self.base.post('/conversations',{'title':'Źródło'}).json()['id'];self.ids=[]
        with connect() as conn:
            for role,text in [('user','Początek'),('assistant','Wybrana odpowiedź'),('user','Późniejsza wiadomość')]:
                mid=str(uuid4());self.ids.append(mid);conn.execute('INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,?,?)',(mid,self.cid,role,text))
        self.route='/conversations/'+self.cid+'/branch';self.body={'message_id':self.ids[1]}
    def test_prefix_and_same_key_retry_return_one_new_conversation(self):
        key=str(uuid4());first=self.base.post(self.route,self.body,key);self.assertEqual(first.status_code,201,first.text);new=first.json();self.assertNotEqual(new['id'],self.cid);self.assertEqual(new['copied_messages'],2)
        self.assertEqual(self.base.post(self.route,self.body,key).json(),new)
        rows=self.base.client.get('/api/v1/conversations/'+new['id']+'/messages').json()['items'];self.assertEqual([r['content'] for r in rows],['Początek','Wybrana odpowiedź']);self.assertTrue(all(r['id'] not in self.ids for r in rows))
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM conversations').fetchone()['n'],2);self.assertEqual(conn.execute('SELECT count(*) AS n FROM runs').fetchone()['n'],0)
        self.assertEqual(self.base.post(self.route,{'message_id':self.ids[0]},key).status_code,409)
    def test_parallel_identical_requests_are_once_and_auth_is_required(self):
        key=str(uuid4())
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.base.post(self.route,self.body,key),range(2)))
        self.assertTrue(all(r.status_code==201 for r in results));self.assertEqual(results[0].json(),results[1].json())
        self.assertEqual(self.base.client.post('/api/v1'+self.route,json=self.body,headers={'X-CSRF-Token':'wrong','Idempotency-Key':str(uuid4())}).status_code,403)
        self.base.client.cookies.clear();self.assertEqual(self.base.post(self.route,self.body).status_code,401)
    def test_wrong_point_owner_and_failed_attempt_leave_no_cache_or_copy(self):
        self.assertEqual(self.base.post(self.route,{'message_id':self.ids[0]}).status_code,422)
        self.assertEqual(self.base.post(self.route,{'message_id':str(uuid4())}).status_code,404)
        with connect() as conn:
            hashed=conn.execute("SELECT password_hash FROM users WHERE username='owner'").fetchone()['password_hash'];conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',('other','other',hashed));conn.execute('UPDATE conversations SET owner_id=? WHERE id=?',('other',self.cid))
        self.assertEqual(self.base.post(self.route,self.body).status_code,404)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM conversations').fetchone()['n'],1);self.assertEqual(conn.execute("SELECT count(*) AS n FROM idempotency_keys WHERE route LIKE '%/branch'").fetchone()['n'],0)

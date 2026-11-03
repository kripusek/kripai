"""HTTP nazw i eksportów: prawdziwy SQLite, sesja/CSRF i brak danych innych osób."""
import json,unittest
from unittest.mock import patch
from uuid import uuid4
import test_native
from app import conversation_export
from app.db import connect

class ConversationAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp()
        self.cid=self.base.post('/conversations',{'title':'Pierwotna'}).json()['id']
        self.content='Pełny tekst — zażółć gęślą jaźń. '*400
        with connect() as conn:conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'assistant',?)",(str(uuid4()),self.cid,self.content))
    def test_rename_then_download_json_and_markdown_preserves_full_text(self):
        client=self.base.client;route='/api/v1/conversations/'+self.cid
        response=client.patch(route,json={'title':'  Moja rozmowa  '});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['title'],'Moja rozmowa')
        for format in ['json','md']:
            response=client.get(route+'/export',params={'format':format});self.assertEqual(response.status_code,200,response.text[:100]);self.assertEqual(response.headers['content-disposition'],'attachment; filename="kripai-'+self.cid+'.'+format+'"');self.assertEqual(response.headers['cache-control'],'no-store');self.assertEqual(response.headers['x-content-type-options'],'nosniff')
            if format=='json':
                body=response.json();self.assertEqual(body['conversation']['title'],'Moja rozmowa');self.assertEqual(body['messages'][0]['content'],self.content);self.assertNotIn('owner_id',body['conversation']);self.assertNotIn('sessions',body)
            else:self.assertIn(self.content,response.text)
    def test_owner_auth_origin_csrf_and_bad_title(self):
        client=self.base.client;route='/api/v1/conversations/'+self.cid
        self.assertEqual(client.patch(route,json={'title':'x'},headers={'X-CSRF-Token':'wrong'}).status_code,403)
        self.assertEqual(client.patch(route,json={'title':'x'},headers={'Origin':'https://outside.invalid'}).status_code,403)
        response=client.patch(route,json={'title':'PRIVATE TITLE\n'});self.assertEqual(response.status_code,422);self.assertNotIn('PRIVATE TITLE',response.text)
        with connect() as conn:
            hashed=conn.execute("SELECT password_hash FROM users WHERE username='owner'").fetchone()['password_hash'];conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',('other','other',hashed));conn.execute('UPDATE conversations SET owner_id=? WHERE id=?',('other',self.cid))
        self.assertEqual(client.patch(route,json={'title':'no'}).status_code,404);self.assertEqual(client.get(route+'/export').status_code,404)
        client.cookies.clear();self.assertEqual(client.get(route+'/export').status_code,401)
    def test_export_limits_and_bad_format_are_errors_never_partial_downloads(self):
        route='/api/v1/conversations/'+self.cid+'/export';client=self.base.client
        self.assertEqual(client.get(route,params={'format':'html'}).status_code,422)
        with patch.object(conversation_export,'MAX_BYTES',100):response=client.get(route,params={'format':'md'})
        self.assertEqual(response.status_code,413);self.assertNotIn('content-disposition',response.headers);self.assertEqual(response.json()['error']['code'],'conversation_export_too_large')

"""Eksport rozmowy: rzeczywista baza SQLite i pełne teksty, bez binariów."""
import json
import sqlite3
from unittest.mock import patch
from uuid import uuid4
from app import conversation_export as export
from app.db import connect
from test_native import DataCase


class ConversationExportTests(DataCase):
    def setUp(self):
        super().setUp()
        self.cid=self.conversation()
        self.uid=self.user()
        with connect() as conn:
            conn.execute('UPDATE conversations SET title=?,created_at=100,updated_at=200 WHERE id=?',('Zażółć gęślą 🐈',self.cid))

    def message(self,text='Treść',role='user',cid=None,created=300):
        identity=str(uuid4())
        with connect() as conn:conn.execute('INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES (?,?,?,?,?)',(identity,cid or self.cid,role,text,created))
        return identity

    def attachment(self,uid=None):
        identity=str(uuid4())
        with connect() as conn:
            conn.execute('INSERT INTO attachments(id,owner_id,filename,media_type,original,preview,pages,current_page,text_layer,analysis) VALUES (?,?,?,?,?,?,?,?,?,?)',(identity,uid or self.uid,'Źródło 🐈.pdf','application/pdf',b'PRIVATE_ORIGINAL',b'PRIVATE_PREVIEW',2,1,'PRIVATE_OCR','PRIVATE_ANALYSIS'))
        return identity

    def result(self,format='json'):
        return export.render(self.cid,self.uid,format)

    def test_full_long_utf8_text_in_both_formats_chronological_sequence(self):
        text='Zażółć 🐈\n```kod```\n'+'długi tekst '*20000
        first=self.message(text,created=900)
        second=self.message('Odpowiedź [W1] [D1]','assistant',created=300)
        value=self.result();body=json.loads(value['body'])
        self.assertEqual(body['version'],1)
        self.assertEqual(body['conversation']['title'],'Zażółć gęślą 🐈')
        self.assertEqual([row['id'] for row in body['messages']],[first,second])
        self.assertEqual(body['messages'][0]['content'],text)
        self.assertEqual(value['filename'],'kripai-'+self.cid+'.json')
        markdown=self.result('md')
        self.assertIn(text,markdown['body'].decode('utf-8'))
        self.assertIn('1970-01-01T00:01:40Z',markdown['body'].decode('utf-8'))
        self.assertEqual(markdown['filename'],'kripai-'+self.cid+'.md')
        self.assertEqual(markdown['media_type'],'text/markdown; charset=utf-8')

    def test_foreign_and_unknown_conversations_share_404_and_own_only(self):
        foreign=str(uuid4())
        with connect() as conn:
            conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(foreign,'other','PRIVATE_PASSWORD_HASH'))
            other=str(uuid4());conn.execute('INSERT INTO conversations(id,owner_id,title) VALUES (?,?,?)',(other,foreign,'PRIVATE_TITLE'))
        self.message('PRIVATE_OTHER_MESSAGE',cid=other)
        self.message('moje')
        for cid in (other,str(uuid4()),'../secret'):
            with self.assertRaises(export.ExportError) as error:export.render(cid,self.uid,'json')
            self.assertEqual((error.exception.code,error.exception.status),('conversation_not_found',404))
        self.assertNotIn(b'PRIVATE',self.result()['body'])

    def test_owned_attachment_metadata_and_tool_rag_citations_without_binary_or_session(self):
        mid=self.message('Patrz [W1] i [D1]','assistant');aid=self.attachment()
        foreign=str(uuid4())
        with connect() as conn:conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(foreign,'other','PRIVATE_PASSWORD_HASH'))
        other=self.attachment(foreign)
        with connect() as conn:
            conn.execute('INSERT INTO message_images(message_id,attachment_id) VALUES (?,?)',(mid,aid))
            conn.execute('INSERT INTO tool_sources VALUES (?,?,?,?,?,?)',(mid,1,'web','https://example.org/źródło','Tytuł WWW','Cytat W'))
            conn.execute('INSERT INTO message_sources VALUES (?,?,?,?,?)',(mid,1,aid,2,'Cytat D'))
            conn.execute('INSERT INTO message_sources VALUES (?,?,?,?,?)',(mid,2,other,1,'PRIVATE_FOREIGN_SOURCE'))
        value=self.result();row=json.loads(value['body'])['messages'][0]
        self.assertEqual(row['attachments'],[{'id':aid,'filename':'Źródło 🐈.pdf','media_type':'application/pdf','pages':2}])
        self.assertEqual([item['label'] for item in row['sources']],['W1','D1'])
        self.assertEqual(row['sources'][1]['attachment_id'],aid)
        for format in ('md','json'):
            body=self.result(format)['body'].decode('utf-8')
            for excluded in ('PRIVATE','session_id','password','original','preview','text_layer','owner_id'):
                self.assertNotIn(excluded,body)
            for included in ('Cytat W','Cytat D','Źródło 🐈.pdf','https://example.org/źródło','W1','D1'):
                self.assertIn(included,body)

    def test_foreign_attachment_reference_is_not_exported(self):
        mid=self.message();foreign=str(uuid4())
        with connect() as conn:conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(foreign,'other','hash'))
        aid=self.attachment(foreign)
        with connect() as conn:conn.execute('INSERT INTO message_images(message_id,attachment_id) VALUES (?,?)',(mid,aid))
        self.assertEqual(json.loads(self.result()['body'])['messages'][0]['attachments'],[])

    def test_bad_format_and_empty_conversation(self):
        for format in ('html','JSON','../md',''):
            with self.assertRaises(export.ExportError) as error:self.result(format)
            self.assertEqual((error.exception.code,error.exception.status),('conversation_export_format',422))
        self.assertEqual(json.loads(self.result()['body'])['messages'],[])

    def test_size_limit_is_explicit_in_utf8_output_and_individual_fields(self):
        self.message('ą'*500)
        for format in ('md','json'):
            with patch.object(export,'MAX_BYTES',900),self.assertRaises(export.ExportError) as error:self.result(format)
            self.assertEqual((error.exception.code,error.exception.status),('conversation_export_too_large',413))
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE conversation_id=?',('x'*400,self.cid))
        with patch.object(export,'MAX_BYTES',500),self.assertRaises(export.ExportError):self.result()

    def test_message_count_limit_is_explicit_not_truncated(self):
        for _ in range(3):self.message('krótko')
        for format in ('md','json'):
            with patch.object(export,'MAX_MESSAGES',2),self.assertRaises(export.ExportError) as error:self.result(format)
            self.assertEqual(error.exception.status,413)
        with connect() as conn:self.assertEqual(conn.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],3)

    def test_source_fields_also_respect_size_limit(self):
        mid=self.message()
        with connect() as conn:conn.execute('INSERT INTO tool_sources VALUES (?,?,?,?,?,?)',(mid,1,'web','https://example.org/'+'x'*2000,'tytuł','cytat'))
        with patch.object(export,'MAX_BYTES',1000),self.assertRaises(export.ExportError):self.result()

    def test_actual_eight_mib_limit_and_exact_output_boundary(self):
        self.message('x'*(8*1024*1024+1))
        for format in ('md','json'):
            with self.assertRaises(export.ExportError) as error:self.result(format)
            self.assertEqual(error.exception.status,413)
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE conversation_id=?',('ą 🐈',self.cid))
        for format in ('md','json'):
            expected=self.result(format)['body'];limit=len(expected)
            with patch.object(export,'MAX_BYTES',limit):self.assertEqual(self.result(format)['body'],expected)
            with patch.object(export,'MAX_BYTES',limit-1),self.assertRaises(export.ExportError):self.result(format)

    def test_export_connection_is_read_only(self):
        self.message('bez zmian')
        original=export.open_db;changes=[]
        def database():
            conn=original();conn.set_authorizer(lambda action,*args:sqlite3.SQLITE_DENY if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) else sqlite3.SQLITE_OK)
            # SQLite authorizer odrzuci INSERT/UPDATE/DELETE podczas eksportowania.
            changes.append(conn)
            return conn
        with patch.object(export,'open_db',side_effect=database):
            self.result('json');self.result('md')
        self.assertEqual(len(changes),2)

    def test_malformed_nontext_and_date_values_are_explicit_errors_in_both_formats(self):
        mid=self.message('tekst')
        for value in (b'BLOB_WITHOUT_TEXT_TYPE',):
            with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE id=?',(value,mid))
            for format in ('md','json'):
                with self.assertRaises(export.ExportError) as error:self.result(format)
                self.assertEqual((error.exception.code,error.exception.status),('conversation_export_invalid_data',500))
        with connect() as conn:conn.execute('UPDATE messages SET content=? WHERE id=?',('poprawny tekst',mid))
        for value in ('niepoprawna data',float('inf'),1e100):
            with connect() as conn:conn.execute('UPDATE conversations SET created_at=? WHERE id=?',(value,self.cid))
            for format in ('md','json'):
                with self.assertRaises(export.ExportError) as error:self.result(format)
                self.assertEqual((error.exception.code,error.exception.status),('conversation_export_invalid_data',500))

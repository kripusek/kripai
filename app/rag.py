"""Pamięć dokumentów: checkpoint strony, ACL przed KNN i źródła w historii."""
from contextlib import contextmanager
import json
import sqlite3
import threading
import time
from . import config,embeddings,media,maintenance
from .embeddings import RagError
from .db import connect
from .vectors import SPACE

STOP=threading.Event()
ENCODER_LOCK=threading.Lock()
THREAD=None
MAX_CHUNKS=20000

@contextmanager
def encoder(check):
    if not ENCODER_LOCK.acquire(blocking=False):raise RagError('rag_busy')
    try:
        with embeddings.session(check) as model:yield model
    finally:ENCODER_LOCK.release()

def validate_selection(conn,ids,uid):
    ids=list(dict.fromkeys(str(x) for x in ids))
    if not 1<=len(ids)<=5:raise RagError('rag_selection',422)
    for aid in ids:
        row=conn.execute('''SELECT d.* FROM rag_documents d JOIN attachments a ON a.id=d.attachment_id
           WHERE d.attachment_id=? AND d.owner_id=? AND a.owner_id=?''',(aid,uid,uid)).fetchone()
        if not row:raise RagError('file_not_found',404)
        if row['status']!='ready' or row['space']!=SPACE:raise RagError('rag_not_ready')
    return ids

def list_documents(uid):
    with connect() as conn:
        rows=conn.execute('''SELECT a.id,a.filename,a.pages,a.media_type,d.status,d.next_page,d.chunks,d.error_code,d.space
          FROM attachments a LEFT JOIN rag_documents d ON d.attachment_id=a.id
          WHERE a.owner_id=? AND a.media_type='application/pdf' ORDER BY a.created_at DESC LIMIT 50''',(uid,)).fetchall()
    return {'items':rows}

def queue(aid,user,rebuild=False):
    if rebuild:
        with connect() as conn:media.owned(conn,aid,user['id'])
        maintenance.backup()
    with connect() as conn:
        row=media.owned(conn,aid,user['id'])
        if conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']!='normal':raise RagError('gaming_mode')
        if row['media_type']!='application/pdf':raise RagError('rag_pdf_required',422)
        doc=conn.execute('SELECT * FROM rag_documents WHERE attachment_id=?',(aid,)).fetchone()
        if doc and doc['status']=='indexing':raise RagError('rag_busy')
        if doc and doc['space']!=SPACE and not rebuild:raise RagError('rag_model_changed')
        if rebuild:
            clear(conn,aid,user['id'])
            doc=None
        if not doc:
            conn.execute("INSERT INTO rag_documents(attachment_id,owner_id,session_id,space,status) VALUES (?,?,?,?,'queued')",(aid,user['id'],user['session_id'],SPACE))
        elif doc['status']!='ready':
            conn.execute("UPDATE rag_documents SET status='queued',session_id=?,error_code=NULL,updated_at=now() WHERE attachment_id=?",(user['session_id'],aid))
    return {'status':'queued' if not doc or doc['status']!='ready' else 'ready'}

def stop_decoder(aid,uid):
    # Po ustawieniu statusu DB przerywamy też aktualny proces PDF, nie cudzą operację panelu.
    with media.guard.lock:
        active=media.guard.active
        if active and active[0][1]==uid and active[0][2].startswith('rag-'+str(aid)+'-'):
            active[1].set()

def pause(aid,uid):
    with connect() as conn:
        media.owned(conn,aid,uid)
        conn.execute("UPDATE rag_documents SET status='paused',updated_at=now() WHERE attachment_id=? AND status IN ('queued','indexing')",(aid,))
    stop_decoder(aid,uid)

def clear(conn,aid,uid):
    media.owned(conn,aid,uid)
    conn.execute('DELETE FROM rag_vectors WHERE document_id=?',(str(aid),))
    conn.execute('DELETE FROM message_sources WHERE attachment_id=?',(aid,))
    for row in conn.execute("SELECT run_id,seq,payload FROM run_events WHERE type='rag.sources'").fetchall():
        payload=row['payload'];items=payload.get('items',[])
        remaining=[item for item in items if item.get('attachment_id')!=str(aid)]
        if len(remaining)!=len(items):
            conn.execute('UPDATE run_events SET payload=? WHERE run_id=? AND seq=?',(json.dumps(dict(payload,items=remaining),ensure_ascii=False),row['run_id'],row['seq']))
    conn.execute('DELETE FROM rag_documents WHERE attachment_id=?',(aid,))
    stop_decoder(aid,uid)

def remove(aid,uid):
    with connect() as conn:media.owned(conn,aid,uid)
    maintenance.backup()
    with connect() as conn:clear(conn,aid,uid)

def check_document(aid,uid,sid):
    if STOP.is_set():raise RagError('rag_paused')
    with connect() as conn:
        doc=conn.execute('SELECT status,space FROM rag_documents WHERE attachment_id=? AND owner_id=?',(aid,uid)).fetchone()
        session=conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',(sid,uid)).fetchone()
        mode=conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']
        attachment=conn.execute('SELECT 1 FROM attachments WHERE id=? AND owner_id=?',(aid,uid)).fetchone()
    if not session:raise RagError('login_required',401)
    if mode!='normal':raise RagError('gaming_mode')
    if not attachment or not doc or doc['status']!='indexing':raise RagError('rag_paused')
    if doc['space']!=SPACE:raise RagError('rag_model_changed')

@contextmanager
def decoding_task(key):
    # Wspólny limit dekodera z panelem plików, bez dwóch procesów parsujących PDF.
    with media.task(key) as cancelled:yield cancelled

def index_document(doc):
    aid,uid,sid=doc['attachment_id'],doc['owner_id'],doc['session_id']
    check=lambda:check_document(aid,uid,sid)
    key=(sid,uid,'rag-'+str(aid)+'-'+str(time.monotonic_ns()))
    check()
    with encoder(check) as model:
        while True:
            check()
            with connect() as conn:
                current=conn.execute('SELECT * FROM rag_documents WHERE attachment_id=?',(aid,)).fetchone()
                source=media.owned(conn,aid,uid)
            page=current['next_page']
            if page>source['pages']:
                if not current['chunks']:raise RagError('rag_no_text',422)
                with connect() as conn:
                    if conn.execute("SELECT 1 FROM rag_documents WHERE attachment_id=? AND status='indexing'",(aid,)).fetchone():
                        conn.execute("UPDATE rag_documents SET status='ready',error_code=NULL,updated_at=now() WHERE attachment_id=?",(aid,))
                return
            with decoding_task((sid,uid,key[2]+'-page-'+str(page))) as cancelled:
                check()
                # Klucz dekodera musi zachować (session,owner,job), reszta identyfikatora w job.
                details,_=media.decode(source['original'],page,(sid,uid,key[2]+'-page-'+str(page)),cancelled)
            check()
            if details.get('text_truncated'):raise RagError('rag_page_too_long',422)
            text=details['text_layer'].strip()
            if not text:raise RagError('rag_no_text',422)
            chunks=list(model.chunks(text))
            vectors=[model.embed(chunk) for chunk in chunks]
            check()
            with connect() as conn:
                # Usunięcie/anulowanie w trakcie obliczeń nie może odtworzyć indeksu.
                active=conn.execute("SELECT 1 FROM rag_documents WHERE attachment_id=? AND status='indexing' AND next_page=?",(aid,page)).fetchone()
                if not active:raise RagError('rag_paused')
                if conn.execute('SELECT count(*) AS n FROM rag_chunks').fetchone()['n']+len(chunks)>MAX_CHUNKS:raise RagError('rag_quota',409)
                for ordinal,(chunk,vector) in enumerate(zip(chunks,vectors)):
                    cid=conn.execute('INSERT INTO rag_chunks(attachment_id,page,ordinal,text) VALUES (?,?,?,?) RETURNING id',(aid,page,ordinal,chunk)).fetchone()['id']
                    conn.execute('INSERT INTO rag_vectors(chunk_id,owner_id,document_id,embedding) VALUES (?,?,?,?)',(cid,uid,aid,vector))
                conn.execute('UPDATE rag_documents SET next_page=?,chunks=chunks+?,updated_at=now() WHERE attachment_id=?',(page+1,len(chunks),aid))

def process_next():
    with connect() as conn:
        doc=conn.execute("SELECT * FROM rag_documents WHERE status='queued' ORDER BY updated_at,attachment_id LIMIT 1").fetchone()
        if not doc:return False
        conn.execute("UPDATE rag_documents SET status='indexing',error_code=NULL WHERE attachment_id=?",(doc['attachment_id'],))
    try:index_document(doc)
    except Exception as exc:
        code=exc.code if isinstance(exc,(RagError,media.MediaError)) else 'rag_index_failed'
        paused=code in {'rag_paused','gaming_mode','login_required','media_busy','media_cancelled','rag_busy'}
        with connect() as conn:
            conn.execute("UPDATE rag_documents SET status=?,error_code=?,updated_at=now() WHERE attachment_id=? AND status='indexing'",('paused' if paused else 'failed',code,doc['attachment_id']))
    return True

def start():
    global THREAD
    STOP.clear()
    with connect() as conn:conn.execute("UPDATE rag_documents SET status='queued' WHERE status='indexing'")
    def work():
        while not STOP.is_set():
            try:process_next()
            except sqlite3.Error:pass
            STOP.wait(.5)
    THREAD=threading.Thread(target=work,daemon=True,name='rag-index');THREAD.start()

def shutdown():
    STOP.set()
    if THREAD:THREAD.join(timeout=25)


def retrieve(ids,uid,query,check):
    with connect() as conn:ids=validate_selection(conn,ids,uid)
    with encoder(check) as model:vector=model.embed(query,query=True)
    candidates=[]
    with connect() as conn:
        validate_selection(conn,ids,uid)
        for aid in ids:
            # ACL i wybór dokumentu WEWNĄTRZ KNN, nie filtrowanie globalnego top-k.
            rows=conn.execute('''SELECT chunk_id,distance FROM rag_vectors WHERE embedding MATCH ? AND k=3
                AND owner_id=? AND document_id=? ORDER BY distance''',(vector,uid,aid)).fetchall()
            for result in rows:
                chunk=conn.execute('''SELECT c.*,a.filename FROM rag_chunks c JOIN attachments a ON a.id=c.attachment_id
                    WHERE c.id=? AND c.attachment_id=? AND a.owner_id=?''',(result['chunk_id'],aid,uid)).fetchone()
                if chunk:candidates.append(dict(chunk,distance=result['distance']))
    candidates.sort(key=lambda row:(row['distance'],row['id']))
    return [{'attachment_id':r['attachment_id'],'filename':r['filename'],'page':r['page'],'text':r['text']} for r in candidates[:3]]


def sources(conn,mid,uid):
    return conn.execute('''SELECT s.ordinal,s.attachment_id,a.filename,s.page,s.excerpt FROM message_sources s
      JOIN attachments a ON a.id=s.attachment_id WHERE s.message_id=? AND a.owner_id=? ORDER BY s.ordinal''',(mid,uid)).fetchall()

def save_sources(conn,mid,items):
    for ordinal,item in enumerate(items,1):
        # Plik mógł zostać usunięty w trakcie generowania odpowiedzi.
        if conn.execute("SELECT 1 FROM rag_documents WHERE attachment_id=? AND status='ready'",(item['attachment_id'],)).fetchone():
            conn.execute('INSERT INTO message_sources VALUES (?,?,?,?,?)',(mid,ordinal,item['attachment_id'],item['page'],item['text']))


def validate_storage(conn):
    """Kopia musi obejmować spójnie fragmenty i wszystkie partycje vec0."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='rag_documents'").fetchone():return
    checks=[
      "SELECT 1 FROM rag_chunks c LEFT JOIN rag_vectors v ON v.chunk_id=c.id JOIN rag_documents d ON d.attachment_id=c.attachment_id WHERE v.chunk_id IS NULL OR v.owner_id!=d.owner_id OR v.document_id!=c.attachment_id LIMIT 1",
      "SELECT 1 FROM rag_vectors v LEFT JOIN rag_chunks c ON c.id=v.chunk_id WHERE c.id IS NULL LIMIT 1",
      "SELECT 1 FROM rag_documents d WHERE d.chunks!=(SELECT count(*) FROM rag_chunks c WHERE c.attachment_id=d.attachment_id) LIMIT 1"
    ]
    if any(conn.execute(sql).fetchone() for sql in checks):raise ValueError('rag_index_inconsistent')

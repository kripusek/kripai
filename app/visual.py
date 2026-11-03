"""Indeks obrazów: strony, osobna przestrzeń, ACL wewnątrz KNN i checkpoint."""
from contextlib import contextmanager
import hashlib
import math
import sqlite3
import struct
import threading
import time
from uuid import uuid4
from . import media, maintenance, rag, visual_encoder
from .db import connect
from .visual_encoder import VisualError, SPACE, DIMENSIONS

STOP = threading.Event()
THREAD = None
MAX_IMAGES = 2500


def valid_vector(value):
    if type(value) is not bytes or len(value) != 4*DIMENSIONS:
        raise VisualError('visual_embedding_invalid', 503)
    values = struct.unpack('<'+str(DIMENSIONS)+'f', value)
    if not all(math.isfinite(x) for x in values):
        raise VisualError('visual_embedding_invalid', 503)
    norm = math.sqrt(sum(x*x for x in values))
    if not math.isfinite(norm) or abs(norm-1) > .0001:
        raise VisualError('visual_embedding_invalid', 503)
    return value


@contextmanager
def encoder(check):
    # Ten sam limit dla E5 i obrazu: dwa encodery CPU nie zajmują RAM równolegle.
    if not rag.ENCODER_LOCK.acquire(blocking=False):
        raise VisualError('visual_busy')
    try:
        check()
        with visual_encoder.session(check) as model:
            yield model
    finally:
        rag.ENCODER_LOCK.release()


def list_documents(uid):
    with connect() as conn:
        rows = conn.execute('''SELECT a.id,a.filename,a.pages,a.media_type,
          d.status,d.next_page,d.images,d.error_code,d.space
          FROM attachments a LEFT JOIN visual_documents d ON d.attachment_id=a.id
          WHERE a.owner_id=? ORDER BY a.created_at DESC,a.id LIMIT 50''', (uid,)).fetchall()
    return {'items': rows, 'space': SPACE, 'dimensions': DIMENSIONS}


def permitted(conn, sid, uid):
    if STOP.is_set():
        raise VisualError('visual_paused')
    if not conn.execute('''SELECT 1 FROM sessions WHERE id=? AND user_id=?
           AND revoked_at IS NULL AND expires_at>now()''', (sid, uid)).fetchone():
        raise VisualError('login_required', 401)
    if conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode'] != 'normal':
        raise VisualError('gaming_mode')


def queue(aid, user, rebuild=False):
    uid, sid = user['id'], user['session_id']
    with connect() as conn:
        media.owned(conn, aid, uid)
        permitted(conn, sid, uid)
        current = conn.execute('SELECT * FROM visual_documents WHERE attachment_id=?', (aid,)).fetchone()
        if current and current['status'] == 'indexing' and not rebuild:
            raise VisualError('visual_busy')
        if current and current['space'] != SPACE and not rebuild:
            raise VisualError('visual_model_changed')
        if rebuild:
            # Kopia i usunięcie dotyczą tego samego stanu, pod blokadą zapisu.
            maintenance.backup()
            clear(conn, aid, uid)
            current = None
        if not current:
            conn.execute('''INSERT INTO visual_documents
              (attachment_id,owner_id,session_id,generation,space,status)
              VALUES (?,?,?,?,?,'queued')''', (aid, uid, sid, uuid4().hex, SPACE))
        elif current['status'] != 'ready':
            # Nowa generacja odcina wynik starego procesu po pauzie lub przebudowie.
            conn.execute('''UPDATE visual_documents SET status='queued',session_id=?,
              generation=?,error_code=NULL,updated_at=now() WHERE attachment_id=?''',
              (sid, uuid4().hex, aid))
    return {'status': 'ready' if current and current['status'] == 'ready' else 'queued'}


def stop_decoder(aid, uid):
    with media.guard.lock:
        active = media.guard.active
        if active and active[0][1] == uid and active[0][2].startswith('visual-'+str(aid)+'-'):
            active[1].set()


def pause(aid, uid):
    with connect() as conn:
        media.owned(conn, aid, uid)
        conn.execute('''UPDATE visual_documents SET status='paused',generation=?,updated_at=now()
          WHERE attachment_id=? AND owner_id=? AND status IN ('queued','indexing')''',
          (uuid4().hex, aid, uid))
    stop_decoder(aid, uid)


def clear(conn, aid, uid):
    media.owned(conn, aid, uid)
    # vec0 nie ma kluczy obcych; czyścimy je jawnie przed kaskadą stron/metadanych.
    conn.execute('DELETE FROM visual_vectors WHERE document_id=?', (aid,))
    conn.execute('DELETE FROM visual_documents WHERE attachment_id=? AND owner_id=?', (aid, uid))
    stop_decoder(aid, uid)


def remove(aid, uid):
    with connect() as conn:
        media.owned(conn, aid, uid)
        maintenance.backup()
        clear(conn, aid, uid)


def active(conn, doc, page=None):
    permitted(conn, doc['session_id'], doc['owner_id'])
    current = conn.execute('''SELECT d.*,a.pages FROM visual_documents d
      JOIN attachments a ON a.id=d.attachment_id
      WHERE d.attachment_id=? AND d.owner_id=? AND a.owner_id=?''',
      (doc['attachment_id'], doc['owner_id'], doc['owner_id'])).fetchone()
    if not current or current['generation'] != doc['generation'] or current['status'] != 'indexing':
        raise VisualError('visual_paused')
    if current['session_id'] != doc['session_id']:
        raise VisualError('visual_paused')
    if current['space'] != SPACE:
        raise VisualError('visual_model_changed')
    if page is not None and current['next_page'] != page:
        raise VisualError('visual_paused')
    return current


def check_document(doc):
    with connect() as conn:
        active(conn, doc)


def index_document(doc):
    aid, uid, sid = doc['attachment_id'], doc['owner_id'], doc['session_id']
    check = lambda: check_document(doc)
    check()
    with encoder(check) as model:
        while True:
            with connect() as conn:
                current = active(conn, doc)
                source = media.owned(conn, aid, uid)
                page = current['next_page']
                if page > source['pages']:
                    conn.execute('''UPDATE visual_documents SET status='ready',error_code=NULL,
                      updated_at=now() WHERE attachment_id=? AND generation=?''', (aid, doc['generation']))
                    return
            key = (sid, uid, 'visual-'+aid+'-'+doc['generation']+'-'+str(page))
            with media.task(key) as cancelled:
                check()
                # Czytamy oryginał każdej strony; podgląd panelu może wskazywać inną stronę.
                _, preview = media.decode(source['original'], page, key, cancelled)
            check()
            vector = valid_vector(model.embed_image(preview))
            check()
            with connect() as conn:
                # Autoryzacja, Gaming i generacja są sprawdzane także w transakcji zapisu.
                active(conn, doc, page)
                if conn.execute('SELECT count(*) AS n FROM visual_pages').fetchone()['n'] >= MAX_IMAGES:
                    raise VisualError('visual_quota', 409)
                pid = conn.execute('''INSERT INTO visual_pages(attachment_id,page,preview_sha256)
                  VALUES (?,?,?) RETURNING id''', (aid, page, hashlib.sha256(preview).hexdigest())).fetchone()['id']
                conn.execute('''INSERT INTO visual_vectors(page_id,owner_id,document_id,space,embedding)
                  VALUES (?,?,?,?,?)''', (pid, uid, aid, SPACE, vector))
                conn.execute('''UPDATE visual_documents SET next_page=?,images=images+1,
                  updated_at=now() WHERE attachment_id=? AND generation=?''', (page+1, aid, doc['generation']))


def process_next():
    with connect() as conn:
        doc = conn.execute("SELECT * FROM visual_documents WHERE status='queued' ORDER BY updated_at,attachment_id LIMIT 1").fetchone()
        if not doc:
            return False
        conn.execute("UPDATE visual_documents SET status='indexing',error_code=NULL WHERE attachment_id=? AND generation=?",
                     (doc['attachment_id'], doc['generation']))
    try:
        index_document(doc)
    except Exception as exc:
        code = exc.code if isinstance(exc, (VisualError, media.MediaError)) else 'visual_index_failed'
        paused = code in {'visual_paused', 'visual_busy', 'gaming_mode', 'login_required', 'media_busy', 'media_cancelled'}
        with connect() as conn:
            # Stary proces nie może zmienić statusu zadania utworzonego już po nim.
            conn.execute('''UPDATE visual_documents SET status=?,error_code=?,updated_at=now()
              WHERE attachment_id=? AND generation=? AND status='indexing' ''',
              ('paused' if paused else 'failed', code, doc['attachment_id'], doc['generation']))
    return True


def start():
    global THREAD
    STOP.clear()
    with connect() as conn:
        conn.execute("UPDATE visual_documents SET status='queued' WHERE status='indexing'")
    def work():
        while not STOP.is_set():
            try:
                process_next()
            except sqlite3.Error:
                pass
            STOP.wait(.5)
    THREAD = threading.Thread(target=work, daemon=True, name='visual-index')
    THREAD.start()


def shutdown():
    STOP.set()
    with media.guard.lock:
        if media.guard.active and media.guard.active[0][2].startswith('visual-'):
            media.guard.active[1].set()
    if THREAD:
        THREAD.join(timeout=25)


def validate_selection(conn, ids, uid):
    if not isinstance(ids, (list, tuple)):
        raise VisualError('visual_selection', 422)
    ids = list(dict.fromkeys(str(x) for x in ids))
    if not 1 <= len(ids) <= 5:
        raise VisualError('visual_selection', 422)
    for aid in ids:
        row = conn.execute('''SELECT d.* FROM visual_documents d JOIN attachments a ON a.id=d.attachment_id
          WHERE d.attachment_id=? AND d.owner_id=? AND a.owner_id=?''', (aid, uid, uid)).fetchone()
        if not row:
            raise VisualError('file_not_found', 404)
        if row['space'] != SPACE:
            raise VisualError('visual_model_changed')
        if row['status'] != 'ready':
            raise VisualError('visual_not_ready')
    return ids


def retrieve(ids, uid, query, check):
    if type(query) is not str or not query.strip() or len(query) > 500:
        raise VisualError('visual_query_invalid', 422)
    check()
    with connect() as conn:
        ids = validate_selection(conn, ids, uid)
    with encoder(check) as model:
        vector = valid_vector(model.embed_text(query))
    check()
    candidates = []
    with connect() as conn:
        validate_selection(conn, ids, uid)
        for aid in ids:
            # Właściciel, zaznaczenie i wersja przestrzeni ograniczają samo KNN.
            rows = conn.execute('''SELECT page_id,distance FROM visual_vectors WHERE embedding MATCH ? AND k=3
              AND owner_id=? AND document_id=? AND space=? ORDER BY distance''', (vector, uid, aid, SPACE)).fetchall()
            for result in rows:
                item = conn.execute('''SELECT p.id,p.attachment_id,p.page,a.filename FROM visual_pages p
                  JOIN attachments a ON a.id=p.attachment_id WHERE p.id=? AND p.attachment_id=? AND a.owner_id=?''',
                  (result['page_id'], aid, uid)).fetchone()
                if item:
                    candidates.append(dict(item, distance=result['distance']))
    check()
    candidates.sort(key=lambda row: (row['distance'], row['id']))
    return [{key: row[key] for key in ('attachment_id', 'filename', 'page', 'distance')} for row in candidates[:3]]


def validate_storage(conn):
    """Online Backup obejmuje źródła i wszystkie partycje visual vec0."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='visual_documents'").fetchone():
        return
    checks = [
        '''SELECT 1 FROM visual_pages p LEFT JOIN visual_vectors v ON v.page_id=p.id
           JOIN visual_documents d ON d.attachment_id=p.attachment_id
           WHERE v.page_id IS NULL OR v.owner_id IS NOT d.owner_id
           OR v.document_id IS NOT p.attachment_id OR v.space IS NOT d.space LIMIT 1''',
        '''SELECT 1 FROM visual_vectors v LEFT JOIN visual_pages p ON p.id=v.page_id WHERE p.id IS NULL LIMIT 1''',
        '''SELECT 1 FROM visual_documents d JOIN attachments a ON a.id=d.attachment_id
           WHERE d.owner_id IS NOT a.owner_id OR d.images!=(SELECT count(*) FROM visual_pages p WHERE p.attachment_id=d.attachment_id)
           OR d.next_page!=d.images+1 OR d.images>a.pages OR (d.status='ready' AND d.images!=a.pages) LIMIT 1''',
        '''SELECT 1 FROM visual_pages p JOIN visual_documents d ON d.attachment_id=p.attachment_id
           WHERE p.page>=d.next_page LIMIT 1'''
    ]
    if any(conn.execute(sql).fetchone() for sql in checks):
        raise ValueError('visual_index_inconsistent')

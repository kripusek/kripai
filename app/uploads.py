"""Wznawialny upload w prywatnym SQLite. Finalny plik i potwierdzenie są atomowe."""
import hashlib,hmac,time
from . import media,maintenance
from .db import connect

CHUNK=512*1024
TTL=3600
MAX_ACTIVE=3

def session(conn,key,normal=False):
    if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',key[:2]).fetchone():raise media.MediaError('login_required',401)
    if normal and conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']!='normal':raise media.MediaError('gaming_mode',409)

def owned(conn,identity,key):
    session(conn,key)
    row=conn.execute('SELECT id,owner_id,session_id,filename,size,sha256,received,status,attachment_id,expires_at,generation FROM upload_sessions WHERE id=? AND owner_id=? AND session_id=?',(identity,key[1],key[0])).fetchone()
    if not row:raise media.MediaError('upload_not_found',404)
    if row['expires_at']<=time.time():raise media.MediaError('upload_expired',410)
    return row

def status(row):
    if row['status']=='completed' and row['attachment_id'] is None:raise media.MediaError('upload_file_gone',410)
    return {name:row[name] for name in ['id','filename','size','sha256','received','status','attachment_id','expires_at']}|{'chunk_size':CHUNK}

def cleanup():
    condition="expires_at<=? OR session_id IS NULL OR session_id IN (SELECT id FROM sessions WHERE revoked_at IS NOT NULL OR expires_at<=?)"
    cutoff=time.time();parameters=(cutoff,cutoff)
    with connect() as conn:
        count=conn.execute('SELECT count(*) AS n FROM upload_sessions WHERE ('+condition+') AND length(data)>0',parameters).fetchone()['n']
        # Blokada zapisu obejmuje kopię i usunięcie tych samych bajtów.
        if count:maintenance.backup()
        conn.execute('DELETE FROM upload_sessions WHERE '+condition,parameters)


def start(body,key):
    with connect() as conn:session(conn,key,normal=True)
    cleanup();identity=str(body.id);name=media.filename(body.name)
    with connect() as conn:
        session(conn,key,normal=True)
        existing=conn.execute('SELECT 1 FROM upload_sessions WHERE id=?',(identity,)).fetchone()
        if existing:
            row=owned(conn,identity,key)
            if (row['filename'],row['size'],row['sha256'])!=(name,body.size,body.sha256):raise media.MediaError('upload_conflict',409)
            return status(row)
        if conn.execute('SELECT 1 FROM attachments WHERE id=?',(identity,)).fetchone():raise media.MediaError('upload_expired',410)
        active=conn.execute("SELECT count(*) AS n FROM upload_sessions WHERE status='uploading'").fetchone()['n']
        if active>=MAX_ACTIVE:raise media.MediaError('upload_quota',409)
        media.quota(conn,0,1)
        conn.execute('INSERT INTO upload_sessions(id,owner_id,session_id,filename,size,sha256,expires_at) VALUES (?,?,?,?,?,?,?)',(identity,key[1],key[0],name,body.size,body.sha256,time.time()+TTL))
        return status(owned(conn,identity,key))

def get(identity,key):
    with connect() as conn:return status(owned(conn,identity,key))

def append(identity,offset,data,key):
    if type(offset) is not int or not 0<=offset<=media.MAX_UPLOAD:raise media.MediaError('upload_offset_conflict',422)
    if not 1<=len(data)<=CHUNK:raise media.MediaError('upload_chunk_size',413)
    with connect() as conn:
        session(conn,key,normal=True);row=owned(conn,identity,key)
        if row['status']!='uploading':raise media.MediaError('upload_completed',409)
        if offset<row['received']:
            previous=conn.execute('SELECT substr(data,?,?) AS part FROM upload_sessions WHERE id=?',(offset+1,len(data),identity)).fetchone()['part']
            if offset+len(data)<=row['received'] and previous==data:return status(row)
            raise media.MediaError('upload_offset_conflict',409)
        if offset!=row['received']:raise media.MediaError('upload_offset_conflict',409)
        if offset+len(data)>row['size']:raise media.MediaError('upload_chunk_size',413)
        media.quota(conn,len(data))
        conn.execute('UPDATE upload_sessions SET data=CAST(data||? AS BLOB),received=received+?,expires_at=? WHERE id=?',(data,len(data),time.time()+TTL,identity))
        return status(owned(conn,identity,key))

def finish(identity,key):
    with connect() as conn:
        receipt=owned(conn,identity,key)
        if receipt['status']=='completed':
            if receipt['attachment_id'] is None:raise media.MediaError('upload_file_gone',410)
            return media.metadata(media.owned(conn,receipt['attachment_id'],key[1]))
    with media.task(key) as cancelled:
        with connect() as conn:
            row=owned(conn,identity,key)
            if row['status']=='completed':
                if row['attachment_id'] is None:raise media.MediaError('upload_file_gone',410)
                return media.metadata(media.owned(conn,row['attachment_id'],key[1]))
            if row['received']!=row['size']:raise media.MediaError('upload_incomplete',409)
            data=conn.execute('SELECT data FROM upload_sessions WHERE id=?',(identity,)).fetchone()['data']
        if not hmac.compare_digest(hashlib.sha256(data).hexdigest(),row['sha256']):raise media.MediaError('upload_digest_mismatch',422)
        info,preview=media.decode(data,1,key,cancelled);media.guard.permitted(key,cancelled)
        with connect() as conn:
            session(conn,key,normal=True)
            if cancelled.is_set() or media.guard.stopping.is_set():raise media.MediaError('media_cancelled',409)
            current=owned(conn,identity,key)
            if current['generation']!=row['generation']:raise media.MediaError('upload_conflict',409)
            if current['status']=='completed':
                if current['attachment_id'] is None:raise media.MediaError('upload_file_gone',410)
                return media.metadata(media.owned(conn,current['attachment_id'],key[1]))
            if (current['filename'],current['size'],current['sha256'],current['received'])!=(row['filename'],row['size'],row['sha256'],row['received']):raise media.MediaError('upload_conflict',409)
            # INSERT załącznika i potwierdzenie uploadu w tej samej transakcji:
            # utracona odpowiedź/restart nie tworzą drugiego pliku przy ponowieniu.
            result=media.store(conn,data,row['filename'],info,preview,key[1],identity,staged_bytes=len(data))
            conn.execute("UPDATE upload_sessions SET status='completed',data=X'',received=size,attachment_id=?,expires_at=? WHERE id=?",(identity,time.time()+TTL,identity))
            return result

def list_pending(key):
    with connect() as conn:
        session(conn,key)
        rows=conn.execute("SELECT id,filename,size,received,expires_at FROM upload_sessions WHERE owner_id=? AND status='uploading' ORDER BY created_at",(key[1],)).fetchall()
        return {'items':rows}

def discard(key):
    with connect() as conn:
        session(conn,key);count=conn.execute("SELECT count(*) AS n FROM upload_sessions WHERE owner_id=? AND status='uploading' AND length(data)>0",(key[1],)).fetchone()['n']
        if count:maintenance.backup()
        cursor=conn.execute("DELETE FROM upload_sessions WHERE owner_id=? AND status='uploading'",(key[1],))
        return {'discarded':cursor.rowcount}

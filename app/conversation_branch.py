"""Niedestrukcyjna kopia prefiksu rozmowy w transakcji wywolujacego."""
from uuid import uuid4

MAX_MESSAGES=1000
MAX_TEXT_BYTES=8*1024*1024


class BranchError(Exception):
    def __init__(self,code,status=422):
        self.code,self.status=code,status
        super().__init__(code)


def branch(conn,cid,uid,message_id,session_id):
    if not conn.in_transaction:raise RuntimeError('branch requires an existing write transaction')
    if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',(session_id,uid)).fetchone():raise BranchError('login_required',401)
    source=conn.execute('SELECT title FROM conversations WHERE id=? AND owner_id=?',(cid,uid)).fetchone()
    if source is None:raise BranchError('not_found',404)
    if not isinstance(source['title'],str):raise BranchError('branch_invalid_data',500)
    point=conn.execute('SELECT seq,role FROM messages WHERE id=? AND conversation_id=?',(message_id,cid)).fetchone()
    if point is None:raise BranchError('not_found',404)
    if point['role']!='assistant':raise BranchError('branch_point')
    if conn.execute("SELECT 1 FROM runs WHERE conversation_id=? AND status NOT IN ('completed','cancelled','failed','expired','outcome_unknown') LIMIT 1",(cid,)).fetchone():raise BranchError('generation_busy',409)
    size=conn.execute('SELECT count(*) AS n,COALESCE(sum(length(CAST(content AS BLOB))),0) AS bytes FROM messages WHERE conversation_id=? AND seq<=?',(cid,point['seq'])).fetchone()
    if size['n']>MAX_MESSAGES or size['bytes']>MAX_TEXT_BYTES:raise BranchError('branch_too_large',413)
    suffix=' \u2014 nowa ga\u0142\u0105\u017a'
    title=(source['title'].strip() or 'Rozmowa')[:200-len(suffix)]+suffix
    result=conn.execute('INSERT INTO conversations(id,owner_id,title) VALUES (?,?,?) RETURNING id,title,created_at',(str(uuid4()),uid,title)).fetchone()
    rows=conn.execute('SELECT id,role,content,created_at FROM messages WHERE conversation_id=? AND seq<=? ORDER BY seq',(cid,point['seq'])).fetchall()
    for row in rows:
        if not isinstance(row['content'],str):raise BranchError('branch_invalid_data',500)
        mid=str(uuid4())
        conn.execute('INSERT INTO messages(id,conversation_id,role,content,created_at,client_message_id) VALUES (?,?,?,?,?,NULL)',(mid,result['id'],row['role'],row['content'],row['created_at']))
        conn.execute('INSERT INTO tool_sources(message_id,ordinal,name,url,title,excerpt) SELECT ?,ordinal,name,url,title,excerpt FROM tool_sources WHERE message_id=?',(mid,row['id']))
        # Wspoldzielimy tylko referencje do wlasnych plikow, nigdy bajty ani stare sesje.
        conn.execute('INSERT INTO message_sources(message_id,ordinal,attachment_id,page,excerpt) SELECT ?,s.ordinal,s.attachment_id,s.page,s.excerpt FROM message_sources s JOIN attachments a ON a.id=s.attachment_id WHERE s.message_id=? AND a.owner_id=?',(mid,row['id'],uid))
        conn.execute('INSERT INTO message_images(message_id,attachment_id,session_id,page) SELECT ?,i.attachment_id,?,i.page FROM message_images i JOIN attachments a ON a.id=i.attachment_id WHERE i.message_id=? AND a.owner_id=?',(mid,session_id,row['id'],uid))
    return result|{'copied_messages':size['n']}

"""Literalne wyszukiwanie w tresci wlasnych wiadomosci; stronicowany odczyt."""
from app.db import open_db

MAX_SCAN=2000
MAX_SEQ=9223372036854775807


class SearchError(Exception):
    def __init__(self,code,status=422):
        self.code,self.status=code,status
        super().__init__(code)


def parameters(query,cursor,limit):
    if not isinstance(query,str):raise SearchError('search_query')
    query=query.strip()
    if not 2<=len(query)<=120:raise SearchError('search_query')
    if type(limit) is not int or not 1<=limit<=20:raise SearchError('search_limit')
    if cursor is not None:
        if type(cursor) is str:
            if not cursor or len(cursor)>19 or any(char not in '0123456789' for char in cursor):raise SearchError('search_cursor')
            cursor=int(cursor)
        if type(cursor) is not int or not 1<=cursor<=MAX_SEQ:raise SearchError('search_cursor')
    return query.casefold(),cursor,limit


def excerpt(content,needle):
    match=content.casefold().find(needle)
    if match<0:return None
    # Casefold moze rozszerzyc znak (np. ss ze znaku sharp s). Liczymy pozycje
    # w oryginale, bez duzej tablicy mapowania i bez zmieniania tekstu zrodla.
    folded=0;start=None;end=len(content)
    for index,char in enumerate(content):
        folded+=len(char.casefold())
        if start is None and folded>match:start=index
        if folded>=match+len(needle):end=index+1;break
    center=(start+end)//2
    left=max(0,center-120);right=min(len(content),left+240)
    left=max(0,right-240)
    return content[left:right]


def search(uid,query,cursor=None,limit=20):
    needle,cursor,limit=parameters(query,cursor,limit)
    conn=open_db()
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        sql='SELECT c.id AS conversation_id,c.title,m.seq,m.role,m.content,m.created_at FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.owner_id=?'
        values=[uid]
        if cursor is not None:sql+=' AND m.seq<?';values.append(cursor)
        rows=conn.execute(sql+' ORDER BY m.seq DESC LIMIT ?',(*values,MAX_SCAN+1))
        items=[];scanned=0;last=None
        while scanned<MAX_SCAN and len(items)<limit:
            row=rows.fetchone()
            if row is None:break
            scanned+=1;last=row['seq']
            snippet=excerpt(row.pop('content'),needle)
            if snippet is not None:items.append(row|{'excerpt':snippet})
        # Ten rekord jest tylko podgladem: nastepna strona nadal go przetworzy.
        next_cursor=str(last) if last is not None and rows.fetchone() is not None else None
        return {'items':items,'next_cursor':next_cursor,'scanned_messages':scanned,'partial':next_cursor is not None}
    finally:
        conn.rollback();conn.close()

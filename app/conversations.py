"""Zmiana tytulu rozmowy z kontrola wlasciciela w transakcji SQLite."""
import unicodedata
from app.db import connect


class ConversationError(Exception):
    def __init__(self,code,status=422):
        self.code,self.status=code,status
        super().__init__(code)


def normalize_title(title):
    # Kontrola przed strip: koncowy znak nowej linii tez jest niedozwolony.
    if not isinstance(title,str) or any(unicodedata.category(char) in {'Cc','Cs'} or char in '\u2028\u2029' for char in title):
        raise ConversationError('conversation_title')
    title=title.strip()
    if not 1<=len(title)<=200:raise ConversationError('conversation_title')
    return title


def rename(cid,uid,title):
    with connect() as conn:
        if not conn.execute('SELECT 1 FROM conversations WHERE id=? AND owner_id=?',(cid,uid)).fetchone():
            raise ConversationError('not_found',404)
        title=normalize_title(title)
        return conn.execute('UPDATE conversations SET title=?,updated_at=now() WHERE id=? AND owner_id=? RETURNING id,title,updated_at',(title,cid,uid)).fetchone()

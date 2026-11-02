"""Jednorazowy import rozmów ze starego lokalnego panelu, bez poleceń WSL/Docker."""
import getpass
import ssl
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.db import connect
from app.maintenance import backup
from app.processes import InstanceLock
from manage import stop


def fetch(client):
    def pages(path):
        result=[];cursor=None
        while True:
            r=client.get(path,params={'limit':100,**({'cursor':cursor} if cursor else {})});r.raise_for_status()
            data=r.json();result.extend(data['items']);next_cursor=data['next_cursor']
            if next_cursor is None:return result
            if next_cursor==cursor:raise ValueError('Nieprawidłowa paginacja starego serwera')
            cursor=next_cursor
    return [(c,pages('/api/v1/conversations/'+c['id']+'/messages')) for c in pages('/api/v1/conversations')]


def import_rows(rows):
    # Najpierw sprawdzamy wszystkie dane, potem jeden atomowy zapis.
    normalized=[]
    def timestamp(value):
        return float(value) if isinstance(value,(float,int)) else datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    for conversation,messages in rows:
        cid=str(UUID(conversation['id']));title=conversation['title']
        if not isinstance(title,str) or len(title)>200:raise ValueError('Nieprawidłowy tytuł')
        data=[]
        for message in messages:
            role=message['role'];content=message['content']
            if role not in {'user','assistant'} or not isinstance(content,str):raise ValueError('Nieprawidłowa wiadomość')
            data.append((str(UUID(message['id'])),cid,role,content,timestamp(message['created_at'])))
        normalized.append((cid,title,timestamp(conversation['created_at']),data))
    with connect() as conn:
        owner=conn.execute("SELECT id FROM users WHERE username='owner'").fetchone()['id']
        for cid,title,created,messages in normalized:
            existing=conn.execute('SELECT owner_id FROM conversations WHERE id=?',(cid,)).fetchone()
            if existing and existing['owner_id']!=owner:raise ValueError('Konflikt właściciela')
            conn.execute('INSERT OR IGNORE INTO conversations(id,owner_id,title,created_at,updated_at) VALUES (?,?,?,?,?)',(cid,owner,title,created,created))
            for row in messages:
                existing=conn.execute('SELECT conversation_id,role,content FROM messages WHERE id=?',(row[0],)).fetchone()
                if existing and (existing['conversation_id'],existing['role'],existing['content'])!=row[1:4]:raise ValueError('Konflikt wiadomości; import cofnięty')
                conn.execute('INSERT OR IGNORE INTO messages(id,conversation_id,role,content,created_at) VALUES (?,?,?,?,?)',row)
    return len(normalized)


def main():
    print('Stary panel https://localhost:8443 musi byc uruchomiony tylko na czas importu.')
    password=getpass.getpass('Haslo owner w STAREJ instalacji: ')
    # Windows systemowy magazyn certyfikatów; nigdy verify=False.
    with httpx.Client(base_url='https://localhost:8443',verify=ssl.create_default_context(),trust_env=False,timeout=30,headers={'Origin':'https://localhost:8443'}) as client:
        r=client.post('/api/v1/auth/login',json={'username':'owner','password':password});r.raise_for_status()
        client.headers['X-CSRF-Token']=client.cookies.get('assistant_csrf')
        try:rows=fetch(client)
        finally:client.post('/api/v1/auth/logout')
    stop()
    with InstanceLock():
        backup();count=import_rows(rows);backup()
    print(f'Zaimportowano rozmow: {count}. Uruchom START.cmd. Stara baza pozostala nienaruszona.')

if __name__=='__main__':
    try:main()
    except Exception:
        print('Import przerwany. Sprawdź działanie starego panelu, jego hasło i zaufanie certyfikatu. Nie wyłączaj weryfikacji TLS.',file=sys.stderr);sys.exit(1)

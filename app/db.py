"""SQLite WAL: krótkie transakcje, klucze obce i atomowe zdarzenia."""
from contextlib import contextmanager
import hashlib
import json
import sqlite3
import time
from uuid import UUID,uuid4
from . import config
sqlite3.register_adapter(UUID,str)


def row_factory(cursor,row):
    value=dict(zip([c[0] for c in cursor.description],row))
    for name in ('payload','response_json'):
        if value.get(name) is not None:value[name]=json.loads(value[name])
    return value


def open_db(path=None):
    conn=sqlite3.connect(path or config.DATA/'kripai.sqlite3',timeout=10,isolation_level=None)
    from .vectors import load
    try:load(conn)
    except BaseException:conn.close();raise
    conn.row_factory=row_factory
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.create_function('now',0,time.time)
    return conn


@contextmanager
def connect():
    conn=open_db()
    try:
        # Rezerwacja zapisu od początku eliminuje wyścig sprawdź-potem-zapisz.
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback();raise
    finally:conn.close()


def migration_files():
    return [config.ROOT/'spec/etap-1/baza.sql', config.ROOT/'spec/etap-2.5a/002-pliki.sql', config.ROOT/'spec/etap-2.5a/003-obraz-w-rozmowie.sql', config.ROOT/'spec/etap-2.5b/004-rag.sql', config.ROOT/'spec/etap-4/005-tools.sql']


def migration_checksums():
    return [(n, hashlib.sha256(p.read_bytes()).hexdigest()) for n,p in enumerate(migration_files(),1)]


def known_migrations(rows):
    return bool(rows) and rows == migration_checksums()[:len(rows)]


def migrate():
    config.DATA.mkdir(parents=True,exist_ok=True)
    conn=open_db()
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        exists=conn.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
        rows=[(r['version'],r['checksum']) for r in conn.execute('SELECT version,checksum FROM schema_migrations ORDER BY version')] if exists else []
        if exists and not known_migrations(rows):raise RuntimeError('Nieznana lub zmieniona migracja SQLite')
        if rows and len(rows)<len(migration_files()):
            # Kopia powstaje przed rozpoczęciem transakcji i zmianą schematu.
            from .maintenance import backup
            backup()
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,checksum TEXT NOT NULL)')
        for (version,checksum),path in zip(migration_checksums(),migration_files()):
            if version<=len(rows):continue
            for statement in path.read_text(encoding='utf-8').split(';'):
                if statement.strip():conn.execute(statement)
            conn.execute('INSERT INTO schema_migrations VALUES (?,?)',(version,checksum))
        conn.commit()
    except BaseException:conn.rollback();raise
    finally:conn.close()


def event(conn,run_id,kind,payload):
    seq=conn.execute('SELECT COALESCE(max(seq),0)+1 AS n FROM run_events WHERE run_id=?',(run_id,)).fetchone()['n']
    conn.execute('INSERT INTO run_events(run_id,seq,event_id,type,payload) VALUES (?,?,?,?,?)',
                 (run_id,seq,uuid4(),kind,json.dumps(payload,ensure_ascii=False)))


def change_state(conn,run_id,state,error=None):
    conn.execute('UPDATE runs SET status=?,error_code=?,updated_at=now() WHERE id=?',(state,error,run_id))
    event(conn,run_id,'run.status',{'state':state,'error_code':error})

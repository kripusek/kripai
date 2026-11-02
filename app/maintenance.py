"""Kopie SQLite przez Online Backup API; żadnego kopiowania aktywnego WAL."""
import hashlib
import secrets
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
from . import config
from .db import connect,open_db,migrate,known_migrations
from .security import password_hash


def set_password(password):
    if not 14<=len(password)<=1024:raise ValueError('Hasło musi mieć 14–1024 znaki.')
    encoded=password_hash(password)
    with connect() as conn:
        if conn.execute("SELECT id FROM users WHERE username='owner'").fetchone():
            conn.execute("UPDATE users SET password_hash=? WHERE username='owner'",(encoded,))
        else:conn.execute('INSERT INTO users(id,username,password_hash) VALUES (?,?,?)',(uuid4(),'owner',encoded))
        conn.execute('DELETE FROM sessions')
        conn.execute('DELETE FROM idempotency_keys')
    ensure_key()


def ensure_key():
    key=config.DATA/'llm.key'
    if not key.exists():key.write_text(secrets.token_urlsafe(48),encoding='ascii')


def validate(path):
    conn=sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)
    try:
        from .vectors import load
        load(conn)
        if conn.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise ValueError('Uszkodzona kopia')
        if conn.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Niespójne relacje w kopii')
        if not known_migrations(conn.execute('SELECT version,checksum FROM schema_migrations ORDER BY version').fetchall()):raise ValueError('Nieobsługiwana wersja kopii')
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():raise ValueError('Nieoczekiwany schemat kopii')
        from .rag import validate_storage
        validate_storage(conn)
    finally:conn.close()


def backup():
    config.BACKUPS.mkdir(parents=True,exist_ok=True)
    target=config.BACKUPS/f'kripai-{time.strftime("%Y%m%d-%H%M%S")}-{uuid4().hex[:8]}.sqlite3'
    temporary=target.with_suffix('.partial')
    source=open_db();destination=sqlite3.connect(temporary)
    try:
        source.backup(destination)
        destination.close();source.close()
        validate(temporary)
        temporary.replace(target)
    except BaseException:
        destination.close();source.close();temporary.unlink(missing_ok=True);raise
    # Zachowujemy 14 ostatnich kompletnych kopii; obcych plików nie ruszamy.
    for old in sorted(config.BACKUPS.glob('kripai-*.sqlite3'),key=lambda p:p.stat().st_mtime,reverse=True)[14:]:old.unlink()
    (config.DATA/'backup.error').unlink(missing_ok=True)
    return target


def restore(path):
    validate(path)
    if (config.DATA/'kripai.sqlite3').exists():backup()
    temporary=config.DATA/'restore.partial'
    source=sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)
    destination=sqlite3.connect(temporary)
    try:source.backup(destination)
    finally:source.close();destination.close()
    validate(temporary)
    # Wywołujący musi posiadać blokadę aplikacji, więc nie ma aktywnych połączeń.
    for suffix in ('-wal','-shm'):(config.DATA/('kripai.sqlite3'+suffix)).unlink(missing_ok=True)
    temporary.replace(config.DATA/'kripai.sqlite3')
    migrate()
    with connect() as conn:
        conn.execute('DELETE FROM sessions')
        conn.execute("UPDATE runs SET status='failed',error_code='backup_restored' WHERE status IN ('queued','preparing_context','generating','cancelling')")
        conn.execute("UPDATE system_mode SET controller_state='offline'")

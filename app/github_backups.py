"""Kopia dziennika SQLite; odtwarzanie nigdy nie cofa wiedzy o publikacji."""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from uuid import UUID
from . import config

MAX_JOURNAL=256*1024**2

def companion(main):return Path(str(main)+'.github')
def checksum(main):return Path(str(main)+'.github.sha256')

def read_rows(path):
    if Path(path).stat().st_size>MAX_JOURNAL:raise ValueError('github_backup_too_large')
    conn=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        conn.execute('PRAGMA trusted_schema=OFF')
        if conn.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise ValueError('github_backup_integrity')
        objects=conn.execute("SELECT type,name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'").fetchall()
        if objects!=[('table','drafts')]:raise ValueError('github_backup_schema')
        if [r[1] for r in conn.execute('PRAGMA table_info(drafts)')]!=['id','owner','data','state','result']:raise ValueError('github_backup_schema')
        rows=conn.execute('SELECT id,owner,data,state,result FROM drafts').fetchall()
        for did,owner,raw,state,result in rows:
            if str(UUID(did))!=did or not isinstance(owner,str) or not 1<=len(owner)<=128 or any(ord(c)<32 for c in owner):raise ValueError('github_backup_owner')
            if state not in {'prepared','publishing','published','outcome_unknown','branch_only'}:raise ValueError('github_backup_state')
            if not isinstance(raw,str) or len(raw)>1024**2:raise ValueError('github_backup_data')
            data=json.loads(raw)
            if set(data)!={'repository','title','body','files','base','head'} or data['repository']!='kripusek/kripusek-autoexec':raise ValueError('github_backup_repository')
            if not isinstance(data['title'],str) or not 1<=len(data['title'])<=150 or not isinstance(data['body'],str) or len(data['body'])>2000:raise ValueError('github_backup_data')
            if not isinstance(data['base'],str) or not 1<=len(data['base'])<=255 or any(ord(c)<33 for c in data['base']) or not re.fullmatch(r'[0-9a-f]{40}',data['head']):raise ValueError('github_backup_head')
            files=data['files']
            if not isinstance(files,list) or not 1<=len(files)<=3:raise ValueError('github_backup_files')
            paths=[]
            for file in files:
                path=file['path'];paths.append(path)
                if not re.fullmatch(r'[A-Za-z0-9_./-]{1,200}',path) or any(p in {'','.','..'} or p.startswith('.') for p in path.split('/')) or path.lower().endswith(('.key','.pem','.sqlite3')):raise ValueError('github_backup_path')
                if file['mode'] not in {'100644','100755'} or not isinstance(file['content'],str) or not 1<=len(file['content'])<=20000 or '\0' in file['content']:raise ValueError('github_backup_content')
            if len(set(paths))!=len(paths):raise ValueError('github_backup_path')
            if result is not None:
                if not isinstance(result,str) or len(result)>16384:raise ValueError('github_backup_result')
                value=json.loads(result)
                if not isinstance(value,dict) or set(value)-{'url','branch','state','error','http_status'}:raise ValueError('github_backup_result')
                if 'branch' in value and value['branch']!='kripai/'+did:raise ValueError('github_backup_result')
                if 'url' in value and not re.fullmatch(r'https://github\.com/kripusek/kripusek-autoexec/(?:pull/[1-9][0-9]*|tree/kripai/'+re.escape(did)+')',value['url']):raise ValueError('github_backup_result')
                if state=='published' and not re.fullmatch(r'https://github\.com/kripusek/kripusek-autoexec/pull/[1-9][0-9]*',value.get('url','')):raise ValueError('github_backup_result')
            elif state=='published':raise ValueError('github_backup_result')
        return rows
    except (KeyError,TypeError,AttributeError) as exc:raise ValueError('github_backup_data') from None
    finally:conn.close()

def snapshot(main):
    source=config.DATA/'github-changes.sqlite3'
    if not source.exists():return
    target=companion(main);temporary=Path(str(target)+'.partial')
    src=None;dst=None
    deadline=time.monotonic()+20
    def progress(*args):
        if time.monotonic()>deadline:raise TimeoutError('github_backup_timeout')
    try:
        src=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(temporary)
        src.backup(dst,pages=256,progress=progress,sleep=.01)
        dst.execute('PRAGMA journal_mode=DELETE')
        dst.close();src.close();read_rows(temporary)
        digest=hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(target)
        checksum(main).write_text(digest,encoding='ascii')
    except BaseException:
        if src:src.close()
        if dst:dst.close()
        for file in (temporary,Path(str(temporary)+'-wal'),Path(str(temporary)+'-shm'),target,checksum(main)):file.unlink(missing_ok=True)
        raise

def load(main):
    file=companion(main);sha=checksum(main)
    if not file.exists() and not sha.exists():return []  # Starsza kopia rozmów.
    if not file.is_file() or not sha.is_file() or sha.stat().st_size!=64:raise ValueError('github_backup_incomplete')
    if file.stat().st_size>MAX_JOURNAL:raise ValueError('github_backup_too_large')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=sha.read_text(encoding='ascii'):raise ValueError('github_backup_checksum')
    return read_rows(file)

def merge(rows):
    if not rows:return
    from .github_changes import store
    with store() as conn:
        conn.execute('BEGIN IMMEDIATE')
        for did,owner,raw,state,result in rows:
            existing=conn.execute('SELECT owner,data,state FROM drafts WHERE id=?',(did,)).fetchone()
            if existing:
                # Nowsza wiedza o zewnętrznych działaniach jest ważniejsza od kopii.
                if existing['owner']!=owner or json.loads(existing['data'])!=json.loads(raw):raise ValueError('github_restore_conflict')
                # Potwierdzenie publikacji jest ważniejsze niż starszy stan
                # prepared/unknown, również gdy pochodzi z przywracanej kopii.
                if state=='published' and existing['state']!='published':conn.execute("UPDATE drafts SET state='published',result=? WHERE id=?",(result,did))
                continue
            if state!='published':
                state='outcome_unknown';result=json.dumps({'branch':'kripai/'+did,'url':'https://github.com/kripusek/kripusek-autoexec/tree/kripai/'+did})
            conn.execute('INSERT INTO drafts VALUES (?,?,?,?,?)',(did,owner,raw,state,result))

def remove(main):
    # Nazwy pochodzą z kontrolowanego katalogu kopii, nie z manifestu/rozmowy.
    companion(main).unlink(missing_ok=True);checksum(main).unlink(missing_ok=True)

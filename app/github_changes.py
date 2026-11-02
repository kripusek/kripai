"""Propozycje lokalne i PR: bez zapisu do istniejących gałęzi i bez merge."""
import json
import base64
import difflib
import http.client
import hashlib
import re
import sqlite3
from contextlib import contextmanager
from uuid import uuid4, UUID
from urllib.parse import quote, urlencode
from . import config
from .network import ToolError, PinnedHTTPS, resolve, body
from .integrations import ADAPTERS

WRITE_REPOSITORY='kripusek/kripusek-autoexec'

class GithubRejected(ToolError):
    """GitHub zwrócił jednoznaczną odmowę; bez treści odpowiedzi i sekretów."""
    def __init__(self,code,status):
        self.status=status
        super().__init__(code)

def api(repo, suffix, method='GET', payload=None):
    if method not in {'GET','POST'} or method=='POST' and (repo!=WRITE_REPOSITORY or suffix not in {'git/trees','git/commits','git/refs','pulls'}):raise ToolError('tool_permission_denied')
    token=ADAPTERS['github'].token(repo)
    if method!='GET' and not token:raise ToolError('github_write_not_configured')
    conn=PinnedHTTPS('api.github.com',resolve('api.github.com'))
    try:
        headers={'User-Agent':'KripAI/1.0','Accept':'application/vnd.github+json','Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        conn.request(method,'/repos/'+repo+('/'+suffix if suffix else ''),body=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        response=conn.getresponse()
        if response.status==404 and method=='GET':return None
        if response.status not in (200,201):
            limited=response.status==429 or response.status==403 and (response.getheader('X-RateLimit-Remaining')=='0' or response.getheader('Retry-After') is not None)
            code='github_credential_invalid' if response.status==401 else 'github_rate_limited' if limited else 'github_write_denied' if response.status==403 and method=='POST' else 'github_remote_rejected'
            raise GithubRejected(code,response.status)
        data,_=body(response)
        return json.loads(data)
    except (OSError,ValueError,http.client.HTTPException):raise ToolError('github_network_failed') from None
    finally:conn.close()

@contextmanager
def store():
    config.DATA.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(config.DATA/'github-changes.sqlite3',timeout=5)
    conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY,owner TEXT NOT NULL,data TEXT NOT NULL,state TEXT NOT NULL,result TEXT)')
    try:
        with conn:yield conn
    finally:conn.close()

def draft(args,scope):
    repo=args['repository'].lower()
    if not scope.get('github') or repo not in scope['repositories'] or not scope.get('owner'):raise ToolError('tool_resource_not_authorized')
    if repo!=WRITE_REPOSITORY:raise ToolError('github_write_repository_denied')
    files=args['files']
    if not files or len(files)>3 or len({f['path'] for f in files})!=len(files):raise ToolError('tool_arguments_invalid')
    for f in files:
        path=f['path']
        if not re.fullmatch(r'[A-Za-z0-9_./-]{1,200}',path) or any(p in {'','.','..'} or p.startswith('.') for p in path.split('/')) or path.lower().endswith(('.key','.pem','.sqlite3')):raise ToolError('github_path_denied')
        if not f['content'] or len(f['content'])>20000:raise ToolError('tool_arguments_invalid')
        if repo+'/'+path not in scope.get('github_files',{}):raise ToolError('github_read_file_first')
    meta=api(repo,'')
    if not meta:raise ToolError('github_remote_rejected')
    base=meta['default_branch'];head=api(repo,'git/ref/heads/'+quote(base,safe=''))['object']['sha']
    for f in files:
        original=api(repo,'contents/'+quote(f['path'],safe='/')+'?'+urlencode({'ref':head}))
        if not original or original.get('type')!='file' or original['sha']!=scope['github_files'][repo+'/'+f['path']]:raise ToolError('github_file_changed')
        if original.get('encoding')!='base64':raise ToolError('tool_format_denied')
        try:old=base64.b64decode(original['content']).decode('utf-8')
        except (ValueError,UnicodeError):raise ToolError('tool_format_denied') from None
        if '\x00' in old or '\x00' in f['content']:raise ToolError('tool_format_denied')
        f['diff']=''.join(difflib.unified_diff(old.splitlines(True),f['content'].splitlines(True),fromfile='a/'+f['path'],tofile='b/'+f['path']))
        if not f['diff']:raise ToolError('github_no_changes')
        # Obecny zakres zachowuje zwykłe pliki; symlinki nie mogą zostać zastąpione.
        commit=api(repo,'git/commits/'+head)
        tree=api(repo,'git/trees/'+commit['tree']['sha']+'?recursive=1')
        if tree.get('truncated'):raise ToolError('tool_response_too_large')
        f['mode']=next((r['mode'] for r in tree['tree'] if r['path']==f['path']),None)
        if f['mode'] not in {'100644','100755'}:raise ToolError('github_path_denied')
    data=dict(args,repository=repo,base=base,head=head)
    did=str(uuid4())
    with store() as conn:conn.execute('INSERT INTO drafts VALUES (?,?,?, ?,NULL)',(did,str(scope['owner']),json.dumps(data),'prepared'))
    return {'url':'https://github.com/'+repo,'title':'Lokalna propozycja PR · '+args['title'],'text':'Przygotowano propozycję '+did+'. Publikacja w panelu Integracje; niczego jeszcze nie wysłano do GitHuba.','draft_id':did}

def list_drafts(owner):
    with store() as conn:rows=conn.execute('SELECT * FROM drafts WHERE owner=? ORDER BY rowid DESC LIMIT 20',(str(owner),)).fetchall()
    return [dict(id=r['id'],state=r['state'],proposal=json.loads(r['data']),result=json.loads(r['result']) if r['result'] else None) for r in rows]

def publish(did,owner):
    did=str(UUID(did))
    with store() as conn:
        # Rezerwacja operacji przed HTTP; utrata odpowiedzi nie powoduje ślepego powtórzenia POST.
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM drafts WHERE id=? AND owner=?',(did,str(owner))).fetchone()
        if not row:raise ToolError('github_draft_not_found')
        if row['state']=='published':return json.loads(row['result'])
        if row['state']!='prepared':raise ToolError('github_outcome_unknown')
        data=json.loads(row['data']);repo=data['repository']
        conf=ADAPTERS['github'].configuration()
        if repo!=WRITE_REPOSITORY or repo not in conf.get('write_repositories',[]):raise ToolError('github_write_not_configured')
        if not ADAPTERS['github'].token(repo):raise ToolError('github_write_not_configured')
        conn.execute("UPDATE drafts SET state='publishing' WHERE id=?",(did,))
    branch='kripai/'+did;mutated=False
    try:
        # Konflikt z nowszą pracą zatrzymuje publikację przed pierwszą mutacją.
        current=api(repo,'git/ref/heads/'+quote(data['base'],safe=''))
        if current['object']['sha']!=data['head']:raise ToolError('github_base_changed')
        commit=api(repo,'git/commits/'+data['head'])
        tree=api(repo,'git/trees','POST',{'base_tree':commit['tree']['sha'],'tree':[{'path':f['path'],'mode':f['mode'],'type':'blob','content':f['content']} for f in data['files']]})
        mutated=True
        new=api(repo,'git/commits','POST',{'message':data['title'],'tree':tree['sha'],'parents':[data['head']]})
        api(repo,'git/refs','POST',{'ref':'refs/heads/'+branch,'sha':new['sha']})
        pr=api(repo,'pulls','POST',{'title':data['title'],'body':data['body']+'\n\nPrzygotowane przez lokalny KripAI. Testy kodu repozytorium nie zostały uruchomione.','head':branch,'base':data['base']})
        result={'url':pr['html_url'],'branch':branch}
        with store() as conn:conn.execute("UPDATE drafts SET state='published',result=? WHERE id=?",(json.dumps(result),did))
        return result
    except Exception as exc:
        # Utrata odpowiedzi lub błąd po pierwszej mutacji pozostaje niepewny.
        # Jawna odmowa 4xx przed jakąkolwiek mutacją pozwala ręcznie wrócić
        # do tej samej propozycji po poprawieniu konfiguracji; bez auto-retry.
        rejected=not mutated and isinstance(exc,GithubRejected) and exc.status in {401,403,404,409,422,429}
        state='prepared' if rejected else 'outcome_unknown'
        result={'error':exc.code,'http_status':exc.status} if rejected else {'branch':branch,'url':'https://github.com/'+repo+'/tree/'+branch}
        with store() as conn:conn.execute('UPDATE drafts SET state=?,result=? WHERE id=?',(state,json.dumps(result),did))
        raise

def _reconcile(did,owner):
    """Po utracie odpowiedzi sprawdzamy stan zdalny wyłącznie przez GET."""
    did=str(UUID(did))
    with store() as conn:
        row=conn.execute('SELECT * FROM drafts WHERE id=? AND owner=?',(did,str(owner))).fetchone()
    if not row:raise ToolError('github_draft_not_found')
    if row['state']=='published':return dict(json.loads(row['result']),state='published')
    if row['state'] not in {'publishing','outcome_unknown','branch_only'}:raise ToolError('github_reconcile_not_needed')
    data=json.loads(row['data']);repo=data['repository'];branch='kripai/'+did
    if repo!=WRITE_REPOSITORY:raise ToolError('github_write_repository_denied')
    reference=api(repo,'git/ref/heads/'+quote(branch,safe=''))
    state='outcome_unknown';url='https://github.com/'+repo+'/tree/'+branch
    if reference:
        sha=reference['object']['sha'];commit=api(repo,'git/commits/'+sha)
        if [parent['sha'] for parent in commit['parents']]!=[data['head']]:raise ToolError('github_reconcile_mismatch')
        tree=api(repo,'git/trees/'+commit['tree']['sha']+'?recursive=1')
        if tree.get('truncated'):raise ToolError('tool_response_too_large')
        entries={entry['path']:entry for entry in tree['tree']}
        original=api(repo,'git/commits/'+data['head'])
        original_tree=api(repo,'git/trees/'+original['tree']['sha']+'?recursive=1')
        if original_tree.get('truncated'):raise ToolError('tool_response_too_large')
        expected_entries={entry['path']:(entry['mode'],entry['type'],entry['sha']) for entry in original_tree['tree'] if entry['type']!='tree'}
        for file in data['files']:
            raw=file['content'].encode('utf-8')
            expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            entry=entries.get(file['path'],{})
            if entry.get('type')!='blob' or entry.get('sha')!=expected or entry.get('mode')!=file['mode']:raise ToolError('github_reconcile_mismatch')
            expected_entries[file['path']]=(file['mode'],'blob',expected)
        actual_entries={entry['path']:(entry['mode'],entry['type'],entry['sha']) for entry in tree['tree'] if entry['type']!='tree'}
        if actual_entries!=expected_entries:raise ToolError('github_reconcile_mismatch')
        state='branch_only'
        pulls=api(repo,'pulls?'+urlencode({'state':'all','head':repo.split('/')[0]+':'+branch,'base':data['base'],'per_page':10}))
        for pr in pulls:
            if pr['head']['ref']==branch and pr['head']['sha']==sha and pr['base']['ref']==data['base'] and re.fullmatch('https://github.com/'+re.escape(repo)+r'/pull/[1-9][0-9]*',pr['html_url']):
                state='published';url=pr['html_url'];break
    result={'state':state,'url':url,'branch':branch}
    with store() as conn:
        conn.execute('BEGIN IMMEDIATE')
        # Trwająca publikacja mogła w międzyczasie zapisać potwierdzony wynik.
        current=conn.execute('SELECT state,result FROM drafts WHERE id=?',(did,)).fetchone()
        if current['state']=='published':return dict(json.loads(current['result']),state='published')
        conn.execute('UPDATE drafts SET state=?,result=? WHERE id=?',(state,json.dumps(result),did))
    return result

def reconcile(did,owner):
    try:return _reconcile(did,owner)
    except (KeyError,TypeError,ValueError):raise ToolError('github_reconcile_invalid') from None

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from uuid import UUID, uuid4

import httpx
import sqlite3
from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.encoders import jsonable_encoder
from .db import connect, event, change_state, migrate
from . import config
from .context import prepare, ContextTooLarge
from .model_process import control
from . import voice, media, rag, tools, gpu, uploads, visual
from fastapi.staticfiles import StaticFiles
from .models import Login, ConversationCreate, MessageCreate, Mode, GPUReport, Speech, MediaPage, ImageQuestion, RagIndex, GithubConnect, McpFilesConnect, UploadStart, ConversationRename, ConversationBranch, VisualSearch
from .security import digest, password_hash, verify_password

ORIGIN = config.ORIGIN
LLM = config.LLM
TERMINAL = {'completed','cancelled','failed','expired','outcome_unknown'}
stop_worker = threading.Event()
login_attempts = deque()
login_lock = threading.Lock()
DUMMY_HASH = password_hash(secrets.token_urlsafe(32))


def fail(status, code):
    raise HTTPException(status, code)


def identity(request: Request):
    token = request.cookies.get('assistant_session','')
    if len(token) > 256 or not token:
        fail(401,'login_required')
    with connect() as conn:
        user = conn.execute('''SELECT u.id,u.username,s.id AS session_id,s.csrf_token_hash
          FROM sessions s JOIN users u ON u.id=s.user_id
          WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>now()''', (digest(token),)).fetchone()
    if not user:
        fail(401,'login_required')
    if request.method not in {'GET','HEAD'}:
        csrf = request.headers.get('x-csrf-token','')
        if not 16 <= len(csrf) <= 256 or not hmac.compare_digest(digest(csrf),bytes(user['csrf_token_hash'])):
            fail(403,'csrf_invalid')
    return user


def owned(conn, cid, uid):
    row = conn.execute('SELECT * FROM conversations WHERE id=? AND owner_id=?',(cid,uid)).fetchone()
    if not row:
        fail(404,'not_found')
    return row


def owned_run(conn,rid,uid):
    row = conn.execute('''SELECT r.* FROM runs r JOIN conversations c ON c.id=r.conversation_id
                         WHERE r.id=? AND c.owner_id=?''',(rid,uid)).fetchone()
    if not row:
        fail(404,'not_found')
    return row


def key_from(request):
    try:
        return UUID(request.headers.get('idempotency-key',''))
    except ValueError:
        fail(422,'idempotency_key_required')


def idempotent(conn,uid,route,key,body):
    sha = digest(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')))
    conn.execute('DELETE FROM idempotency_keys WHERE owner_id=? AND route=? AND key=? AND expires_at<=now()', (uid,route,key))
    row = conn.execute('SELECT * FROM idempotency_keys WHERE owner_id=? AND route=? AND key=?',(uid,route,key)).fetchone()
    if row:
        if not hmac.compare_digest(bytes(row['request_sha256']),sha):
            fail(409,'idempotency_conflict')
        return row['response_json']
    conn.execute('INSERT INTO idempotency_keys(owner_id,route,key,request_sha256,expires_at) VALUES (?,?,?,?,now()+86400)',(uid,route,key,sha))
    return None


def remember(conn,uid,route,key,result,status=202):
    conn.execute('UPDATE idempotency_keys SET response_json=? WHERE owner_id=? AND route=? AND key=?',(json.dumps(result),uid,route,key))
    return JSONResponse(result,status_code=status)


def infer(run):
    rid = run['id']
    try:
        with connect() as conn:
            image=conn.execute('SELECT i.*,c.owner_id FROM message_images i JOIN messages m ON m.id=i.message_id JOIN conversations c ON c.id=m.conversation_id WHERE i.message_id=?',(run['user_message_id'],)).fetchone()
        if image:
            infer_image(run,image);return
        with connect() as conn:
            state = conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
            if state == 'cancelling':
                change_state(conn,rid,'cancelled'); return
            change_state(conn,rid,'preparing_context')
            history = conn.execute('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY seq DESC LIMIT 200',(run['conversation_id'],)).fetchall()[::-1]
            total=conn.execute('SELECT count(*) AS n FROM messages WHERE conversation_id=?',(run['conversation_id'],)).fetchone()['n']
        readings=None
        if run.get('allow_web') or run.get('allow_github') or run.get('allow_mcp'):
            def check_tools():
                with connect() as conn:
                    state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
                    mode=conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']
                    session=conn.execute('SELECT 1 FROM sessions WHERE id=? AND revoked_at IS NULL AND expires_at>now()',(run['tool_session_id'],)).fetchone()
                if state=='cancelling' or stop_worker.is_set():raise tools.ToolError('tool_cancelled')
                if mode!='normal':raise tools.ToolError('gaming_mode')
                if not session:raise tools.ToolError('login_required')
            def activity(name,state):
                with connect() as conn:event(conn,rid,'tool.activity',{'name':name,'state':state})
            scope=tools.policy(history[-1]['content'],run['allow_web'],run['allow_github'],run.get('allow_mcp',False))
            scope=tools.bind_integrations(scope)
            with connect() as conn:scope['owner']=conn.execute('SELECT owner_id FROM conversations WHERE id=?',(run['conversation_id'],)).fetchone()['owner_id']
            with httpx.Client(timeout=30,headers=config.llm_headers(),trust_env=False) as planner:
                # Planer nie dostaje prywatnej historii ani PDF; tylko bieżącą prośbę.
                planning,_,_=prepare([history[-1]],planner,tool_definitions=tools.schemas(scope),budget=config.CONTEXT-512-128)
                readings=tools.plan(planner,planning,scope,check_tools,activity)
            check_tools()
        selected=json.loads(run.get('rag_selection','[]'))
        citations=None
        if selected:
            def check_rag():
                with connect() as conn:
                    current=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
                    mode=conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']
                if current=='cancelling' or stop_worker.is_set() or rag.STOP.is_set():raise rag.RagError('rag_paused')
                if mode!='normal':raise rag.RagError('gaming_mode')
            with connect() as conn:uid=conn.execute('SELECT owner_id FROM conversations WHERE id=?',(run['conversation_id'],)).fetchone()['owner_id']
            citations=rag.retrieve(selected,uid,history[-1]['content'],check_rag)
        with httpx.Client(timeout=20,headers=config.llm_headers(),trust_env=False) as tokenizer:
            messages,omitted,tokens=prepare(history,tokenizer,citations,network=readings)
        if readings is not None:
            with connect() as conn:event(conn,rid,'tool.sources',{'items':[dict(item,ordinal=i) for i,item in enumerate(readings,1) if 'error' not in item]})
        if citations is not None:
            with connect() as conn:
                rag.validate_selection(conn,selected,uid)
                event(conn,rid,'rag.sources',{'items':[dict(c,ordinal=i) for i,c in enumerate(citations,1)]})
        with connect() as conn:
            event(conn,rid,'context.info',{'omitted_messages':omitted+total-len(history),'input_tokens':tokens})
        with connect() as conn:
            state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
            if state=='cancelling':
                change_state(conn,rid,'cancelled'); return
            change_state(conn,rid,'generating')
        from .generation import generate, GenerationInterrupted
        answer=''; pending=''; last=time.monotonic()
        def check_generation():
            with connect() as conn:
                state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
                mode=conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']
            if state=='cancelling' or stop_worker.is_set():raise tools.ToolError('tool_cancelled')
            if mode!='normal':raise tools.ToolError('gaming_mode')
        def emit(piece):
            nonlocal pending,last
            pending+=piece
            if time.monotonic()-last>=0.1 or len(pending)>=128:
                with connect() as conn:event(conn,rid,'assistant.text.delta',{'text':pending})
                pending='';last=time.monotonic()
        def continuing(segment):
            with connect() as conn:event(conn,rid,'assistant.continuing',{'segment':segment})
        def replace_answer(text):
            nonlocal pending
            pending=''
            with connect() as conn:event(conn,rid,'assistant.text.snapshot',{'text':text})
        interrupted=False
        with httpx.Client(timeout=httpx.Timeout(120,connect=10),headers=config.llm_headers(),trust_env=False) as client:
            try:answer,finish_reason=generate(client,messages,check_generation,emit,continuing,replace_answer)
            except GenerationInterrupted as exc:
                answer=exc.text;finish_reason='interrupted';interrupted=True
                if not answer:raise
        with connect() as conn:
            state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
            if state=='cancelling':
                change_state(conn,rid,'cancelled');return
            if pending:
                event(conn,rid,'assistant.text.delta',{'text':pending})
            mid=uuid4()
            conn.execute('INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,\'assistant\',?)',(mid,run['conversation_id'],answer))
            if citations:rag.save_sources(conn,mid,citations)
            if readings:tools.save_sources(conn,mid,readings)
            conn.execute('UPDATE conversations SET updated_at=now() WHERE id=?',(run['conversation_id'],))
            change_state(conn,rid,'failed' if interrupted else 'completed','inference_interrupted' if interrupted else 'output_limit' if finish_reason=='length' else None)
    except Exception as exc:
        # Nie logujemy promptu, treści odpowiedzi ani wyjątków zawierających dane.
        with connect() as conn:
            row=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()
            if row and row['status'] not in TERMINAL:
                change_state(conn,rid,'cancelled' if row['status']=='cancelling' else 'failed','context_too_large' if isinstance(exc,ContextTooLarge) else exc.code if isinstance(exc,(media.MediaError,rag.RagError,tools.ToolError)) else 'inference_interrupted')


def infer_image(run,image):
    rid=run['id']
    def check():
        with connect() as conn:state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
        if state=='cancelling' or stop_worker.is_set():raise media.MediaError('media_cancelled',409)
    def delta(text):
        with connect() as conn:
            state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
            if state in TERMINAL or state=='cancelling':return
            event(conn,rid,'assistant.text.delta',{'text':text})
    check()
    with connect() as conn:
        question=conn.execute('SELECT content FROM messages WHERE id=?',(run['user_message_id'],)).fetchone()['content']
        change_state(conn,rid,'generating')
    key=(image['session_id'],image['owner_id'],str(rid))
    result=media.analyze(image['attachment_id'],'question',question,key,run_id=rid,on_delta=delta,check=check,page=image['page'])
    check()
    with connect() as conn:
        state=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()['status']
        if state=='cancelling':change_state(conn,rid,'cancelled');return
        conn.execute("INSERT INTO messages(id,conversation_id,role,content) VALUES (?,?,'assistant',?)",(uuid4(),run['conversation_id'],result['text']))
        conn.execute('UPDATE conversations SET updated_at=now() WHERE id=?',(run['conversation_id'],))
        change_state(conn,rid,'completed','output_limit' if result.get('truncated') else None)


def worker():
    while not stop_worker.is_set():
        try:
            with connect() as conn:
                # Ten wątek wykonuje infer synchronicznie. Stan aktywny na początku
                # nowej iteracji oznacza przerwanie poprzedniej próby (np. awarię DB).
                interrupted=conn.execute("SELECT id FROM runs WHERE status IN ('preparing_context','generating')").fetchall()
                for previous in interrupted:
                    change_state(conn,previous['id'],'failed','worker_interrupted')
                row=conn.execute("SELECT * FROM runs WHERE status IN ('queued','cancelling') ORDER BY created_at LIMIT 1").fetchone()
            if row:
                infer(row)
        except Exception:
            pass  # Kolejna próba po przerwie; readiness pokazuje awarię bazy.
        stop_worker.wait(0.3)


@asynccontextmanager
async def lifespan(app):
    migrate()
    voice.service.reset()
    media.reset()
    tools.reset()
    with connect() as conn:conn.execute("UPDATE system_mode SET requested_profile='text',loaded_profile='none',controller_state='offline'")
    with connect() as conn:
        for row in conn.execute("SELECT id FROM runs WHERE status NOT IN ('completed','cancelled','failed','expired','outcome_unknown')").fetchall():
            change_state(conn,row['id'],'failed','server_restarted')
    stop_worker.clear()
    rag.start()
    visual.start()
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    model_thread=threading.Thread(target=control,args=(stop_worker,),daemon=True);model_thread.start()
    yield
    visual.shutdown()
    rag.shutdown()
    voice.service.shutdown()
    media.guard.shutdown()
    stop_worker.set()
    model_thread.join(timeout=20)
    thread.join(timeout=5)

app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)


@app.middleware('http')
async def boundary(request,call_next):
    # Dostęp z tunelu/LAN wymaga oddzielnego, świadomego wdrożenia.
    if request.headers.get('host','') not in {f'localhost:{config.PORT}',f'127.0.0.1:{config.PORT}'} or any(h in request.headers for h in ('forwarded','x-forwarded-for','x-forwarded-host','cf-connecting-ip')):
        return JSONResponse({'error':{'code':'host_denied','message':'Niedozwolony host','request_id':str(uuid4())}},400)
    if request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('origin') != ORIGIN:
        return JSONResponse({'error':{'code':'origin_denied','message':'Niedozwolone źródło','request_id':str(uuid4())}},403)
    try:
        length=int(request.headers.get('content-length','0'))
    except ValueError:
        return Response(status_code=400)
    if length<0: return Response(status_code=400)
    audio_upload = request.method == 'POST' and re.fullmatch(r'/api/v1/voice/jobs/[0-9a-fA-F-]{36}/transcribe', request.url.path)
    file_upload=request.method=='POST' and re.fullmatch(r'/api/v1/media/jobs/[0-9a-fA-F-]{36}/files',request.url.path)
    chunk_upload=request.method=='PUT' and re.fullmatch(r'/api/v1/media/uploads/[0-9a-fA-F-]{36}/chunks',request.url.path)
    limit = uploads.CHUNK if chunk_upload else media.MAX_UPLOAD if file_upload else voice.MAX_AUDIO if audio_upload else 16384
    if audio_upload or file_upload or chunk_upload:
        # Duży upload dopuszczamy dopiero po autoryzacji i CSRF, przed buforowaniem.
        try:
            identity(request)
        except HTTPException as exc:
            return await error(request, exc)
    if length > limit: return Response(status_code=413)
    if request.method in {'POST','PUT','PATCH'}:
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>limit:return Response(status_code=413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    try:
        response=await call_next(request)
    except sqlite3.Error:
        return JSONResponse({'error':{'code':'database_unavailable','message':'Baza jest niedostępna','request_id':str(uuid4())}},503)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' blob:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['Permissions-Policy']='microphone=(self), camera=()'
    response.headers['Referrer-Policy']='no-referrer'
    return response


@app.exception_handler(HTTPException)
async def error(request,exc):
    return JSONResponse({'error':{'code':str(exc.detail),'message':str(exc.detail),'request_id':str(uuid4())}},exc.status_code)

@app.exception_handler(RequestValidationError)
async def invalid(request,exc):
    # Domyślny błąd walidatora mógłby odbić podane hasło w odpowiedzi.
    return JSONResponse({'error':{'code':'invalid_request','message':'Sprawdź wymagane pola','request_id':str(uuid4())}},422)

@app.get('/api/v1/health/live')
def live(): return {'status':'alive','app':'KripAI-native'}

@app.get('/api/v1/health/ready')
def ready():
    with connect() as conn: conn.execute('SELECT 1')
    return {'status':'ready'}

@app.post('/api/v1/auth/login')
def login(body:Login):
    now=time.monotonic()
    with login_lock:
        while login_attempts and login_attempts[0][0]<now-60:
            login_attempts.popleft()
        if len(login_attempts)>=30 or sum(name==body.username for _,name in login_attempts)>=5:
            fail(429,'login_rate_limited')
        login_attempts.append((now,body.username))
    with connect() as conn:
        user=conn.execute('SELECT * FROM users WHERE username=?',(body.username,)).fetchone()
        valid=verify_password(body.password,user['password_hash'] if user else DUMMY_HASH)
        if not user or not valid: fail(401,'invalid_credentials')
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        conn.execute('INSERT INTO sessions(id,user_id,token_hash,csrf_token_hash,expires_at) VALUES (?,?,?,?,now()+43200)',(uuid4(),user['id'],digest(token),digest(csrf)))
    response=Response(status_code=204)
    response.set_cookie('assistant_session',token,secure=False,httponly=True,samesite='strict',max_age=43200)
    response.set_cookie('assistant_csrf',csrf,secure=False,httponly=False,samesite='strict',max_age=43200)
    return response

@app.post('/api/v1/auth/logout')
def logout(user=Depends(identity)):
    with connect() as conn: conn.execute('UPDATE sessions SET revoked_at=now() WHERE id=?',(user['session_id'],))
    response=Response(status_code=204)
    response.delete_cookie('assistant_session',secure=False,httponly=True,samesite='strict')
    response.delete_cookie('assistant_csrf',secure=False,samesite='strict')
    return response

@app.get('/api/v1/integrations')
def integrations_status(user=Depends(identity)):
    from .integrations import ADAPTERS
    return {'items':[adapter.status() for adapter in ADAPTERS.values()]}

def time_session_check(user):
    def check():
        with connect() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',(user['session_id'],user['id'])).fetchone():raise tools.ToolError('login_required')
    return check

@app.post('/api/v1/integrations/mcp-time/prepare')
def mcp_time_prepare(user=Depends(identity)):
    mcp_files_owner(user)
    from scripts.setup_mcp_time import prepare
    try:
        prepare(time_session_check(user));return {'prepared':True,'read_only':True}
    except tools.ToolError as exc:fail(401,exc.code)
    except Exception as exc:
        code=str(exc) if str(exc) in {'mcp_time_python_unavailable','mcp_time_installation_conflict','mcp_time_lock_invalid'} else 'mcp_time_prepare_failed'
        fail(409,code)

@app.post('/api/v1/integrations/mcp-time/test')
def mcp_time_test(body:tools.McpTime,user=Depends(identity)):
    check=time_session_check(user)
    try:
        check();scope=tools.bind_integrations(tools.policy('',mcp=True))
        if not scope.get('mcp_time_available'):raise tools.ToolError('mcp_time_unavailable')
        result=tools.read('mcp_time',body.model_dump(),scope,check);check()
        return dict(result,available=True,read_only=True)
    except tools.ToolError as exc:
        if exc.code=='login_required':fail(401,exc.code)
        return {'available':False,'error':exc.code,'read_only':True}

@app.get('/api/v1/integrations/mcp-time/result')
def mcp_time_result(data:str=Query(max_length=1800),user=Depends(identity)):
    from .mcp_time import decode
    try:snapshot=decode(data)
    except tools.ToolError as exc:fail(422,exc.code)
    return Response('Zapisany wynik odczytu czasu; ten link nie odświeża zegara.\n'+json.dumps(snapshot,ensure_ascii=False,indent=2),media_type='text/plain',headers={'X-Content-Type-Options':'nosniff'})

@app.post('/api/v1/integrations/feeds/test')
def feed_test(body:tools.WebRead,user=Depends(identity)):
    def check_session():
        with connect() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',(user['session_id'],user['id'])).fetchone():raise tools.ToolError('login_required')
    try:
        scope=tools.policy(body.url,True,False)
        result=tools.read('feed_read',{'url':body.url},scope,check_session)
        check_session()
        return dict(result,available=True,read_only=True)
    except tools.ToolError as exc:
        if exc.code=='login_required':fail(401,exc.code)
        return {'available':False,'error':exc.code,'read_only':True}

@app.post('/api/v1/integrations/mcp/test')
def mcp_test(user=Depends(identity)):
    from .mcp_client import execute
    try:
        result=execute('list');return {'available':True,'documents':len(result['paths']),'read_only':True}
    except tools.ToolError as exc:return {'available':False,'error':exc.code}

@app.get('/api/v1/integrations/mcp/catalog')
def mcp_catalog(user=Depends(identity)):
    from .mcp_documents import catalog
    return catalog(config.ROOT)

@app.get('/api/v1/integrations/mcp/document')
def mcp_document(path:str=Query(max_length=200),user=Depends(identity)):
    from .mcp_documents import document
    try:return Response(document(config.ROOT,path)['text'],media_type='text/plain')
    except tools.ToolError as exc:fail(404,exc.code)

def mcp_files_owner(user):
    if user['username']!='owner':fail(403,'integration_owner_required')

@app.get('/api/v1/integrations/mcp-files/config')
def mcp_files_config(user=Depends(identity)):
    mcp_files_owner(user)
    from . import mcp_files
    try:
        data=mcp_files.settings()
        return dict(mcp_files.status(),root=str(data['root']) if data else '')
    except tools.ToolError as exc:fail(409,exc.code)
    except OSError:fail(503,'mcp_files_configuration_invalid')

@app.post('/api/v1/integrations/mcp-files/config')
def mcp_files_connect(body:McpFilesConnect,user=Depends(identity)):
    mcp_files_owner(user)
    from .mcp_files import configure
    try:return configure(body.root,body.label)
    except tools.ToolError as exc:fail(422,exc.code)
    except OSError:fail(422,'mcp_files_configuration_invalid')

@app.post('/api/v1/integrations/mcp-files/disconnect',status_code=204)
def mcp_files_disconnect(user=Depends(identity)):
    mcp_files_owner(user)
    from .mcp_files import disconnect
    try:disconnect()
    except tools.ToolError as exc:fail(409,exc.code)
    except OSError:fail(503,'mcp_files_configuration_invalid')
    return Response(status_code=204)

@app.post('/api/v1/integrations/mcp-files/prepare')
def mcp_files_prepare(user=Depends(identity)):
    mcp_files_owner(user)
    from scripts.setup_mcp_filesystem import prepare
    from .mcp_files import status
    try:prepare();return status()
    except Exception:fail(503,'mcp_files_install_failed')

@app.post('/api/v1/integrations/mcp-files/test')
def mcp_files_test(user=Depends(identity)):
    mcp_files_owner(user)
    from .mcp_files import execute,configured_id
    try:
        result=execute('list',root_id=configured_id())
        return {'available':True,'documents':len(result['paths']),'read_only':True,'omitted_entries':result['omitted_entries']}
    except tools.ToolError as exc:return {'available':False,'error':exc.code}
    except OSError:return {'available':False,'error':'mcp_files_document_missing'}

@app.get('/api/v1/integrations/mcp-files/catalog')
@app.get('/api/v1/integrations/mcp-files/document')
def mcp_files_source(request:Request,root:UUID,path:str=Query(default='',max_length=200),user=Depends(identity)):
    from .mcp_files import execute
    try:
        document=request.url.path.endswith('/document')
        result=execute('read' if document else 'list',path,str(root))
        return Response(result['document'],media_type='text/plain') if document else result
    except tools.ToolError as exc:fail(404,exc.code)
    except OSError:fail(404,'mcp_files_document_missing')

@app.get('/api/v1/integrations/mcp-files/search')
def mcp_files_search(root:UUID,query:str=Query(min_length=2,max_length=80),user=Depends(identity)):
    from .mcp_files import execute
    try:return execute('search',root_id=str(root),query=query)
    except tools.ToolError as exc:fail(404,exc.code)
    except OSError:fail(404,'mcp_files_document_missing')

@app.get('/api/v1/integrations/github/drafts')
def github_drafts(user=Depends(identity)):
    from .github_changes import list_drafts
    return {'items':list_drafts(user['id'])}

@app.post('/api/v1/integrations/github/connect')
def github_connect(body: 'GithubConnect', user=Depends(identity)):
    if user['username']!='owner':fail(403,'integration_owner_required')
    from .github_connect import connect as configure
    def check_connection_session():
        with connect() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND revoked_at IS NULL AND expires_at>now()',(user['session_id'],)).fetchone():raise tools.ToolError('login_required')
    try:return configure(body.repositories,body.token.get_secret_value(),body.write,check_connection_session)
    except tools.ToolError as exc:fail(409,exc.code)
    except OSError:fail(503,'integration_configuration_failed')

@app.post('/api/v1/integrations/github/disconnect',status_code=204)
def github_disconnect(user=Depends(identity)):
    if user['username']!='owner':fail(403,'integration_owner_required')
    from .github_connect import disconnect
    try:disconnect()
    except OSError:fail(503,'integration_configuration_failed')
    return Response(status_code=204)

@app.post('/api/v1/integrations/github/drafts/{did}/publish')
def github_publish(did:UUID,user=Depends(identity)):
    from .github_changes import publish
    try:return publish(str(did),user['id'])
    except tools.ToolError as exc:fail(409,exc.code)

@app.post('/api/v1/integrations/github/drafts/{did}/reconcile')
def github_reconcile(did:UUID,user=Depends(identity)):
    from .github_changes import reconcile
    try:return reconcile(str(did),user['id'])
    except tools.ToolError as exc:fail(409,exc.code)

@app.post('/api/v1/integrations/github/test')
def integration_test(body: tools.GithubRead, user=Depends(identity)):
    try:
        scope=tools.policy(body.repository,False,True)
        tools.read('github_read',{'repository':body.repository,'section':'tree','path':''},scope,lambda:None)
        return {'available':True,'read_only':True}
    except tools.ToolError as exc: return {'available':False,'error':exc.code}

@app.get('/api/v1/me')
def me(user=Depends(identity)): return {'id':user['id'],'username':user['username']}

@app.post('/api/v1/conversations',status_code=201)
def new_conversation(body:ConversationCreate,user=Depends(identity)):
    with connect() as conn:
        return conn.execute('INSERT INTO conversations(id,owner_id,title) VALUES (?,?,?) RETURNING id,title,created_at',(uuid4(),user['id'],body.title)).fetchone()


def offset(cursor):
    if cursor is None: return 0
    if not cursor.isdigit() or len(cursor)>19 or int(cursor)>9223372036854775807: fail(422,'invalid_cursor')
    return int(cursor)

@app.get('/api/v1/conversations')
def conversations(limit:int=Query(20,ge=1,le=100),cursor:str|None=None,user=Depends(identity)):
    start=offset(cursor)
    with connect() as conn:
        rows=conn.execute('SELECT id,title,created_at FROM conversations WHERE owner_id=? ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?',(user['id'],limit+1,start)).fetchall()
    return {'items':rows[:limit],'next_cursor':str(start+limit) if len(rows)>limit else None}

@app.get('/api/v1/conversations/search')
def search_conversations(q:str=Query(min_length=2,max_length=120),cursor:str|None=None,user=Depends(identity)):
    from .conversation_search import search,SearchError
    try:return search(user['id'],q,cursor)
    except SearchError as exc:fail(exc.status,exc.code)

@app.get('/api/v1/conversations/{cid}')
def conversation(cid:UUID,user=Depends(identity)):
    with connect() as conn: return owned(conn,cid,user['id'])

@app.patch('/api/v1/conversations/{cid}')
def rename_conversation(cid:UUID,body:ConversationRename,user=Depends(identity)):
    from .conversations import rename,ConversationError
    try:return rename(str(cid),user['id'],body.title)
    except ConversationError as exc:fail(exc.status,exc.code)

@app.get('/api/v1/conversations/{cid}/export')
def export_conversation(cid:UUID,format:str=Query(default='md'),user=Depends(identity)):
    from .conversation_export import render,ExportError
    try:result=render(str(cid),user['id'],format)
    except ExportError as exc:fail(exc.status,exc.code)
    return Response(result['body'],media_type=result['media_type'],headers={'Content-Disposition':'attachment; filename="'+result['filename']+'"','X-Content-Type-Options':'nosniff'})

@app.post('/api/v1/conversations/{cid}/branch',status_code=201)
def branch_conversation(cid:UUID,body:ConversationBranch,request:Request,user=Depends(identity)):
    from .conversation_branch import branch,BranchError
    key=key_from(request);route=request.url.path
    with connect() as conn:
        if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',(user['session_id'],user['id'])).fetchone():fail(401,'login_required')
        cached=idempotent(conn,user['id'],route,key,body.model_dump(mode='json'))
        if cached is not None:
            owned(conn,cached['id'],user['id'])
            return JSONResponse(cached,201)
        try:result=branch(conn,str(cid),user['id'],str(body.message_id),user['session_id'])
        except BranchError as exc:fail(exc.status,exc.code)
        return remember(conn,user['id'],route,key,result,status=201)

@app.get('/api/v1/conversations/{cid}/messages')
def messages(cid:UUID,limit:int=Query(20,ge=1,le=100),cursor:str|None=None,at:int|None=Query(default=None,ge=1,le=9223372036854775807),user=Depends(identity)):
    if at is not None and cursor is not None:fail(422,'invalid_cursor')
    before=offset(cursor) if cursor else 9223372036854775807
    with connect() as conn:
        owned(conn,cid,user['id'])
        if at is not None and not conn.execute('SELECT 1 FROM messages WHERE conversation_id=? AND seq=?',(cid,at)).fetchone():fail(404,'message_not_found')
        comparison='<=' if at is not None else '<'
        rows=conn.execute('SELECT m.seq,m.id,m.role,m.content,m.created_at,i.attachment_id,i.page AS attachment_page,a.media_type AS attachment_media_type FROM messages m LEFT JOIN message_images i ON i.message_id=m.id LEFT JOIN attachments a ON a.id=i.attachment_id AND a.owner_id=? WHERE m.conversation_id=? AND m.seq'+comparison+'? ORDER BY m.seq DESC LIMIT ?',(user['id'],cid,at if at is not None else before,limit+1)).fetchall()
        for row in rows:
            row['sources']=rag.sources(conn,row['id'],user['id'])
            row['tool_sources']=tools.sources(conn,row['id'])
    selected=rows[:limit]
    return {'items':list(reversed(selected)),'next_cursor':str(selected[-1]['seq']) if len(rows)>limit else None}

@app.post('/api/v1/conversations/{cid}/messages')
def send(cid:UUID,body:MessageCreate,request:Request,user=Depends(identity)):
    key=key_from(request);route=str(request.url.path)
    with connect() as conn:
        owned(conn,cid,user['id'])
        # Nowa flaga false ma identyczne znaczenie jak brak flagi w starym UI.
        cached=idempotent(conn,user['id'],route,key,body.model_dump(mode='json',exclude=({'allow_mcp'} if not body.allow_mcp else set()) | ({'attachment_page'} if body.attachment_page is None else set())))
        if cached is not None: return JSONResponse(cached,202)
        if conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']!='normal': fail(503,'gaming_mode')
        if conn.execute('SELECT requested_profile FROM system_mode').fetchone()['requested_profile']!='text':fail(409,'vision_busy')
        if conn.execute('SELECT controller_state FROM system_mode').fetchone()['controller_state']!='ready':fail(503,'model_unavailable')
        if conn.execute("SELECT 1 FROM runs WHERE status NOT IN ('completed','cancelled','failed','expired','outcome_unknown') LIMIT 1").fetchone(): fail(409,'generation_busy')
        if conn.execute('SELECT 1 FROM messages WHERE conversation_id=? AND client_message_id=?',(cid,body.client_message_id)).fetchone(): fail(409,'client_message_conflict')
        if body.attachment_page is not None and not body.attachment_id:fail(422,'file_page')
        if body.attachment_id and (body.allow_web or body.allow_github or body.allow_mcp):fail(422,'tool_image_combination')
        if body.document_ids:
            if body.attachment_id:fail(422,'rag_image_combination')
            rag.validate_selection(conn,body.document_ids,user['id'])
        if body.attachment_id:
            attachment=media.owned(conn,body.attachment_id,user['id'])
            if attachment['media_type'] not in {'image/png','image/jpeg','application/pdf'}:fail(422,'chat_image_format')
            if (body.attachment_page or 1)>attachment['pages']:fail(422,'file_page')
            if not all((config.DATA/'models'/name).is_file() for name in ('vision-model.gguf','vision-mmproj.gguf')):fail(503,'vision_not_installed')
        mid=uuid4();rid=uuid4()
        conn.execute('INSERT INTO messages(id,conversation_id,role,content,client_message_id) VALUES (?,?,\'user\',?,?)',(mid,cid,body.text,body.client_message_id))
        if body.attachment_id:
            conn.execute('INSERT INTO message_images(message_id,attachment_id,session_id,page) VALUES (?,?,?,?)',(mid,body.attachment_id,user['session_id'],body.attachment_page or 1))
        conn.execute('INSERT INTO runs(id,conversation_id,user_message_id,status) VALUES (?,?,?,\'queued\')',(rid,cid,mid))
        conn.execute('UPDATE runs SET rag_selection=?,allow_web=?,allow_github=?,allow_mcp=?,tool_session_id=? WHERE id=?',(json.dumps([str(x) for x in body.document_ids]),int(body.allow_web),int(body.allow_github),int(body.allow_mcp),user['session_id'] if body.allow_web or body.allow_github or body.allow_mcp else None,rid))
        conn.execute("UPDATE conversations SET updated_at=now(),title=CASE WHEN title='' THEN ? ELSE title END WHERE id=?",(body.text[:60],cid))
        event(conn,rid,'run.status',{'state':'queued'})
        return remember(conn,user['id'],route,key,{'message_id':str(mid),'run_id':str(rid),'status':'queued'})

@app.get('/api/v1/runs/{rid}')
def snapshot(rid:UUID,user=Depends(identity)):
    with connect() as conn: return owned_run(conn,rid,user['id'])

@app.post('/api/v1/runs/{rid}/cancel')
def cancel(rid:UUID,request:Request,user=Depends(identity)):
    key=key_from(request);route=str(request.url.path)
    with connect() as conn:
        owned_run(conn,rid,user['id'])
        cached=idempotent(conn,user['id'],route,key,{})
        if cached is not None: return JSONResponse(cached,202)
        run=conn.execute('SELECT status FROM runs WHERE id=?',(rid,)).fetchone()
        if run['status'] not in TERMINAL: change_state(conn,rid,'cancelling')
        return remember(conn,user['id'],route,key,{'accepted':True})

@app.get('/api/v1/runs/{rid}/events')
def events(rid:UUID,request:Request,user=Depends(identity)):
    raw=request.headers.get('last-event-id','0')
    if not raw.isdigit() or len(raw)>18: fail(410,'invalid_event_cursor')
    seq=int(raw)
    with connect() as conn:
        owned_run(conn,rid,user['id'])
        max_seq=conn.execute('SELECT COALESCE(max(seq),0) AS n FROM run_events WHERE run_id=?',(rid,)).fetchone()['n']
        if seq>max_seq: fail(410,'invalid_event_cursor')
    def stream():
        nonlocal seq
        for _ in range(240):
            with connect() as conn:
                session=conn.execute('SELECT 1 FROM sessions WHERE id=? AND revoked_at IS NULL AND expires_at>now()',(user['session_id'],)).fetchone()
                if not session: return
                run=owned_run(conn,rid,user['id'])
                rows=conn.execute('SELECT seq,type,payload FROM run_events WHERE run_id=? AND seq>? ORDER BY seq LIMIT 100',(rid,seq)).fetchall()
            for row in rows:
                seq=row['seq']
                yield f"id: {seq}\nevent: {row['type']}\ndata: {json.dumps(row['payload'],ensure_ascii=False)}\n\n"
            if run['status'] in TERMINAL and not rows: return
            yield ': heartbeat\n\n';time.sleep(0.5)
    return StreamingResponse(stream(),media_type='text/event-stream')

@app.get('/api/v1/system/status')
def status(user=Depends(identity)):
    with connect() as conn:
        row=conn.execute('SELECT requested_mode,controller_state,requested_profile FROM system_mode').fetchone()
    state=row['controller_state']
    if state not in {'error','offline'}:
        if row['requested_mode']=='gaming' and state!='stopped':state='stopping'
        elif row['requested_mode']=='normal' and state!='ready':state='starting'
    model={'ready':'ready','stopped':'unloaded','starting':'loading'}.get(state,'unavailable')
    return {'profile':row['requested_profile'],'mode':row['requested_mode'],'database':'ready','model':model,'controller':state,'backup':'error' if (config.DATA/'backup.error').exists() else 'ready'}

@app.get('/api/v1/system/gpu')
def gpu_status(user=Depends(identity)):
    return gpu.snapshot()

@app.post('/api/v1/system/mode')
def mode(body:Mode,request:Request,user=Depends(identity)):
    key=key_from(request);route=str(request.url.path)
    with connect() as conn:
        cached=idempotent(conn,user['id'],route,key,body.model_dump())
        if cached is not None:return JSONResponse(cached,202)
        conn.execute("UPDATE system_mode SET requested_mode=?,controller_state=?,updated_at=now()",(body.mode,'stopping' if body.mode=='gaming' else 'starting'))
        if body.mode=='gaming':
            for run in conn.execute("SELECT id FROM runs WHERE status IN ('queued','preparing_context','generating') ORDER BY id").fetchall():
                change_state(conn,run['id'],'cancelling')
        return remember(conn,user['id'],route,key,{'requested_mode':body.mode})


@app.exception_handler(voice.VoiceError)
async def voice_error(request, exc):
    return JSONResponse({'error': {'code': exc.code, 'message': exc.code}}, exc.status)


def voice_key(user, job_id):
    return (str(user['session_id']), str(user['id']), str(job_id))


async def voice_execute(kind, key, language, value):
    try:
        return await asyncio.to_thread(voice.service.execute, kind, key, language, value)
    except asyncio.CancelledError:
        voice.service.cancel(key)
        raise
    except voice.VoiceError:
        raise
    except Exception:
        # Nie ujawniamy audio, tekstu ani ścieżek z błędów procesu.
        raise voice.VoiceError('voice_engine_failed', 503) from None


@app.post('/api/v1/voice/jobs/{job_id}/transcribe')
async def transcribe(job_id:UUID, request:Request, language:str=Query('pl', pattern='^(pl|en)$'), user=Depends(identity)):
    if request.headers.get('content-type', '').split(';')[0] != 'audio/wav':
        fail(415, 'audio_format')
    return await voice_execute('transcribe', voice_key(user, job_id), language, await request.body())


@app.post('/api/v1/voice/jobs/{job_id}/speak')
async def speak(job_id:UUID, body:Speech, user=Depends(identity)):
    data = await voice_execute('speak', voice_key(user, job_id), body.language, body.text)
    return Response(data, media_type='audio/wav')


@app.post('/api/v1/voice/jobs/{job_id}/cancel', status_code=204)
def cancel_voice(job_id:UUID, user=Depends(identity)):
    voice.service.cancel(voice_key(user, job_id))
    return Response(status_code=204)


@app.exception_handler(media.MediaError)
async def media_error(request,exc):
    return JSONResponse({'error':{'code':exc.code,'message':exc.code}},exc.status)


async def media_execute(function,key,*args):
    try:return await asyncio.to_thread(function,*args,key)
    except asyncio.CancelledError:
        media.guard.cancel(key);raise
    except media.MediaError:raise
    except Exception:raise media.MediaError('file_operation_failed',503) from None


@app.get('/api/v1/files')
def files(user=Depends(identity)):
    with connect() as conn:
        rows=conn.execute('SELECT id,filename,media_type,pages,current_page,created_at FROM attachments WHERE owner_id=? ORDER BY created_at DESC LIMIT 50',(user['id'],)).fetchall()
    return {'items':rows}


@app.post('/api/v1/media/uploads')
def start_file_upload(body:UploadStart,user=Depends(identity)):
    return uploads.start(body,(user['session_id'],user['id']))

@app.get('/api/v1/media/uploads')
def pending_uploads(user=Depends(identity)):
    return uploads.list_pending((user['session_id'],user['id']))

@app.post('/api/v1/media/uploads/discard')
def discard_uploads(user=Depends(identity)):
    try:return uploads.discard((user['session_id'],user['id']))
    except OSError:raise media.MediaError('backup_failed',503) from None

@app.get('/api/v1/media/uploads/{upload_id}')
def file_upload_status(upload_id:UUID,user=Depends(identity)):
    return uploads.get(str(upload_id),(user['session_id'],user['id']))

@app.put('/api/v1/media/uploads/{upload_id}/chunks')
async def file_upload_chunk(upload_id:UUID,request:Request,offset:int=Query(ge=0,le=8388608),user=Depends(identity)):
    return await asyncio.to_thread(uploads.append,str(upload_id),offset,await request.body(),(user['session_id'],user['id']))

@app.post('/api/v1/media/jobs/{job_id}/uploads/{upload_id}/complete')
async def finish_file_upload(job_id:UUID,upload_id:UUID,user=Depends(identity)):
    return await media_execute(uploads.finish,voice_key(user,job_id),str(upload_id))

@app.post('/api/v1/media/jobs/{job_id}/files',status_code=201)
async def upload_file(job_id:UUID,request:Request,name:str=Query(min_length=1,max_length=180),user=Depends(identity)):
    return await media_execute(media.upload,voice_key(user,job_id),await request.body(),name)


@app.get('/api/v1/files/{aid}')
def file_metadata(aid:UUID,user=Depends(identity)):
    with connect() as conn:return media.metadata(media.owned(conn,aid,user['id']))


@app.get('/api/v1/files/{aid}/preview')
def file_preview(aid:UUID,user=Depends(identity)):
    with connect() as conn:row=media.owned(conn,aid,user['id'])
    return Response(row['preview'],media_type='image/png')


@app.get('/api/v1/files/{aid}/download')
def file_download(aid:UUID,user=Depends(identity)):
    from pathlib import PurePath
    from urllib.parse import quote
    with connect() as conn:row=media.owned(conn,aid,user['id'])
    extension={'image/png':'.png','image/jpeg':'.jpg','application/pdf':'.pdf'}[row['media_type']]
    name=PurePath(row['filename']).stem+extension
    return Response(row['original'],media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(name,safe='')})


@app.delete('/api/v1/files/{aid}',status_code=204)
def delete_file(aid:UUID,user=Depends(identity)):
    try:media.delete(aid,user['id'])
    except OSError:raise media.MediaError('backup_failed',503) from None
    return Response(status_code=204)


@app.post('/api/v1/media/jobs/{job_id}/files/{aid}/page')
async def file_page(job_id:UUID,aid:UUID,body:MediaPage,user=Depends(identity)):
    return await media_execute(media.render_page,voice_key(user,job_id),str(aid),body.page)


@app.post('/api/v1/media/jobs/{job_id}/files/{aid}/analyze')
async def file_analyze(job_id:UUID,aid:UUID,body:ImageQuestion,user=Depends(identity)):
    return await media_execute(media.analyze,voice_key(user,job_id),str(aid),body.mode,body.question)


@app.post('/api/v1/media/jobs/{job_id}/cancel',status_code=204)
def cancel_media(job_id:UUID,user=Depends(identity)):
    media.guard.cancel(voice_key(user,job_id));return Response(status_code=204)


@app.exception_handler(rag.RagError)
async def rag_error(request,exc):
    return JSONResponse({'error':{'code':exc.code,'message':exc.code}},exc.status)

@app.get('/api/v1/rag/documents')
def rag_documents(user=Depends(identity)):
    return rag.list_documents(user['id'])

@app.post('/api/v1/rag/documents/{aid}/index',status_code=202)
def rag_index(aid:UUID,body:RagIndex,user=Depends(identity)):
    return rag.queue(str(aid),user,body.rebuild)

@app.post('/api/v1/rag/documents/{aid}/pause',status_code=204)
def rag_pause(aid:UUID,user=Depends(identity)):
    rag.pause(str(aid),user['id']);return Response(status_code=204)

@app.delete('/api/v1/rag/documents/{aid}',status_code=204)
def rag_remove(aid:UUID,user=Depends(identity)):
    try:rag.remove(str(aid),user['id'])
    except OSError:raise rag.RagError('backup_failed',503) from None
    return Response(status_code=204)


@app.exception_handler(visual.VisualError)
async def visual_error(request,exc):
    return JSONResponse({'error':{'code':exc.code,'message':exc.code}},exc.status)


def visual_check(user):
    def check():
        with connect() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()',
                                (user['session_id'],user['id'])).fetchone():raise visual.VisualError('login_required',401)
            if conn.execute('SELECT requested_mode FROM system_mode').fetchone()['requested_mode']!='normal':raise visual.VisualError('gaming_mode')
        if visual.STOP.is_set():raise visual.VisualError('visual_paused')
    return check


@app.get('/api/v1/visual/status')
def visual_status(user=Depends(identity)):
    from scripts.setup_visual import installed
    return {'installed':installed() is not None,'space':visual.SPACE,'dimensions':768,'cpu_only':True}


@app.post('/api/v1/visual/prepare')
def visual_prepare(user=Depends(identity)):
    mcp_files_owner(user)
    from scripts.setup_visual import prepare
    try:
        prepare(visual_check(user))
    except visual.VisualError:raise
    except Exception:
        raise visual.VisualError('visual_prepare_failed',503) from None
    return {'installed':True,'space':visual.SPACE,'dimensions':768,'cpu_only':True}


@app.get('/api/v1/visual/documents')
def visual_documents(user=Depends(identity)):
    return visual.list_documents(user['id'])


@app.post('/api/v1/visual/documents/{aid}/index',status_code=202)
def visual_index(aid:UUID,body:RagIndex,user=Depends(identity)):
    return visual.queue(str(aid),user,body.rebuild)


@app.post('/api/v1/visual/documents/{aid}/pause',status_code=204)
def visual_pause(aid:UUID,user=Depends(identity)):
    visual.pause(str(aid),user['id']);return Response(status_code=204)


@app.delete('/api/v1/visual/documents/{aid}',status_code=204)
def visual_remove(aid:UUID,user=Depends(identity)):
    try:visual.remove(str(aid),user['id'])
    except OSError:raise visual.VisualError('backup_failed',503) from None
    return Response(status_code=204)


@app.post('/api/v1/visual/search')
def visual_search(body:VisualSearch,user=Depends(identity)):
    check=visual_check(user);check()
    items=visual.retrieve([str(aid) for aid in body.attachment_ids],user['id'],body.query,check)
    check();return {'items':items}


app.mount('/',StaticFiles(directory=config.ROOT/'web',html=True),name='web')

"""Lokalny kreator połączenia; token nigdy nie jest częścią rozmowy."""
import base64
import ctypes as c
from ctypes import wintypes as w
import json
import os
import shutil
import threading
from uuid import uuid4
from . import config
from .network import ToolError,fetch,valid_repo

LOCK=threading.Lock()

def protect(token):
    if os.name!='nt':raise ToolError('integration_windows_required')
    class Blob(c.Structure):
        _fields_=[('size',w.DWORD),('data',c.POINTER(c.c_byte))]
    raw=token.encode('utf-8');buffer=c.create_string_buffer(raw)
    source=Blob(len(raw),c.cast(buffer,c.POINTER(c.c_byte)));result=Blob()
    crypt=c.WinDLL('crypt32');kernel=c.WinDLL('kernel32')
    crypt.CryptProtectData.argtypes=[c.POINTER(Blob),w.LPCWSTR,c.c_void_p,c.c_void_p,c.c_void_p,w.DWORD,c.POINTER(Blob)]
    kernel.LocalFree.argtypes=[c.c_void_p]
    try:
        if not crypt.CryptProtectData(c.byref(source),None,None,None,None,1,c.byref(result)):raise ToolError('integration_credential_unavailable')
        try:return base64.b64encode(c.string_at(result.data,result.size)).decode('ascii')
        finally:kernel.LocalFree(result.data)
    finally:c.memset(buffer,0,c.sizeof(buffer))

def backup_configuration(path):
    if path.exists():
        folder=config.BACKUPS/'credentials';folder.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,folder/('github-'+str(uuid4())+'.json'))

def connect(repositories,token,write=False,check=lambda:None):
    repos=list(dict.fromkeys(r.strip().lower() for r in repositories))
    if not 1<=len(repos)<=5 or any(not valid_repo(r) for r in repos):raise ToolError('integration_repositories_invalid')
    if write and 'kripusek/kripusek-autoexec' not in repos:raise ToolError('github_write_repository_denied')
    if not token or len(token)>512 or any(ord(ch)<33 or ord(ch)>126 for ch in token):raise ToolError('integration_token_invalid')
    with LOCK:
        check()
        # Sprawdzenie przed zastąpieniem sprawnej konfiguracji. Wyłącznie GET.
        try:
            account=json.loads(fetch('https://api.github.com/user',token=token)['data'])
            login=account['login']
            for repo in repos:fetch('https://api.github.com/repos/'+repo,token=token)
        except (ValueError,KeyError,TypeError):raise ToolError('integration_account_invalid') from None
        encrypted=protect(token)
        check()
        path=config.DATA/'github.json';config.DATA.mkdir(parents=True,exist_ok=True)
        temporary=config.DATA/('github-'+str(uuid4())+'.tmp')
        try:
            temporary.write_text(json.dumps({'repositories':repos,'credential':encrypted,'write_repositories':['kripusek/kripusek-autoexec'] if write else [],'login':login}),encoding='utf-8')
            backup_configuration(path)
            os.replace(temporary,path)
        finally:temporary.unlink(missing_ok=True)
    return {'connected':True,'login':login,'repositories':repos,'write_repositories':['kripusek/kripusek-autoexec'] if write else []}

def disconnect():
    with LOCK:
        path=config.DATA/'github.json'
        backup_configuration(path)
        path.unlink(missing_ok=True)

"""Jeden przypięty zewnętrzny serwer MCP; tylko list_directory/read_text_file."""
import json,os,shutil
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID,uuid4
from . import config
from .network import ToolError
from .mcp_client import StdioClient
from scripts import setup_mcp_filesystem as setup

MAX_BYTES=32768;MAX_TEXT=12000
READ_TOOLS={'list_directory','read_text_file'}

def no_links(path):
    cursor=Path(path.anchor)
    for part in path.parts[1:]:
        cursor=cursor/part;stat=cursor.lstat()
        if cursor.is_symlink() or getattr(stat,'st_file_attributes',0)&0x400:raise ToolError('mcp_files_path_denied')

def root_path(value):
    if not isinstance(value,str) or not value or len(value)>1024 or value.startswith(('\\\\','//')):raise ToolError('mcp_files_configuration_invalid')
    path=Path(value).expanduser()
    if not path.is_absolute() or '..' in path.parts or path.parent==path:raise ToolError('mcp_files_configuration_invalid')
    no_links(path);path=path.resolve()
    if not path.is_dir():raise ToolError('mcp_files_configuration_invalid')
    for protected in [config.DATA.resolve(),config.BACKUPS.resolve()]:
        if path.is_relative_to(protected) or protected.is_relative_to(path):raise ToolError('mcp_files_path_denied')
    return path

def settings():
    path=config.DATA/'mcp-filesystem.json'
    if not path.exists():return None
    try:
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ValueError()
        if path.stat().st_size>8192:raise ValueError()
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if set(data)!={'root','id','label'} or str(UUID(data['id']))!=data['id']:raise ValueError()
        if not isinstance(data['label'],str) or not 1<=len(data['label'])<=60 or any(ord(c)<32 for c in data['label']):raise ValueError()
        return dict(data,root=root_path(data['root']))
    except (OSError,ValueError,TypeError,KeyError):raise ToolError('mcp_files_configuration_invalid') from None

def backup_configuration():
    path=config.DATA/'mcp-filesystem.json'
    if path.exists():
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ToolError('mcp_files_configuration_invalid')
        config.BACKUPS.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,config.BACKUPS/('mcp-filesystem-before-'+str(uuid4())+'.json'))

def configure(root,label):
    path=root_path(root)
    if not isinstance(label,str) or not 1<=len(label.strip())<=60 or any(ord(c)<32 for c in label):raise ToolError('mcp_files_configuration_invalid')
    data={'root':str(path),'label':label.strip(),'id':str(uuid4())}
    config.DATA.mkdir(parents=True,exist_ok=True);backup_configuration()
    target=config.DATA/'mcp-filesystem.json';temporary=config.DATA/('mcp-filesystem-'+str(uuid4())+'.tmp')
    try:temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)
    return status()

def disconnect():
    backup_configuration();(config.DATA/'mcp-filesystem.json').unlink(missing_ok=True)

def status():
    try:
        data=settings();available=bool(setup.node() and setup.installed())
        return {'name':'mcp_files','provider':'MCP filesystem '+setup.VERSION,'configured':bool(data),'available':available,'read_only':True,'label':data['label'] if data else None,'root_id':data['id'] if data else None}
    except ToolError as exc:return {'name':'mcp_files','configured':False,'available':False,'read_only':True,'error':exc.code}

def local_path(data,relative,read=False):
    if not isinstance(relative,str) or len(relative)>200:raise ToolError('mcp_files_path_denied')
    relative=relative.replace('\\','/')
    parts=relative.split('/') if relative else []
    if len(parts)>6 or any(p in {'','.','..'} or p.startswith('.') for p in parts) or any(ord(c)<32 or ord(c)==127 or c in ':<>|?*' or c.isspace() and c!=' ' for c in relative):raise ToolError('mcp_files_path_denied')
    root=data['root'];path=root.joinpath(*parts);no_links(path)
    if not path.resolve().is_relative_to(root):raise ToolError('mcp_files_path_denied')
    if read:
        if not parts or path.suffix.lower() not in {'.md','.txt'} or not path.is_file():raise ToolError('mcp_files_path_denied')
        if path.stat().st_size>MAX_BYTES:raise ToolError('mcp_files_too_large')
    elif not path.is_dir():raise ToolError('mcp_files_path_denied')
    return path,relative

def configured_id():
    data=settings();return data['id'] if data else None

def execute(action,relative='',root_id=None):
    if action not in {'list','read'}:raise ToolError('mcp_tool_denied')
    data=settings()
    if not data:raise ToolError('mcp_files_not_configured')
    if root_id!=data['id']:raise ToolError('mcp_files_scope_changed')
    try:path,relative=local_path(data,relative,read=action=='read')
    except OSError:raise ToolError('mcp_files_document_missing') from None
    if action=='list':
        for index,_ in enumerate(path.iterdir()):
            if index>=200:raise ToolError('mcp_files_directory_large')
    runtime=setup.installed();node=setup.node()
    if runtime is None or node is None:raise ToolError('mcp_files_unavailable')
    def check():
        if configured_id()!=root_id:raise ToolError('mcp_files_scope_changed')
    client=StdioClient(check,command=[str(node),str(runtime/'node_modules/@modelcontextprotocol/server-filesystem/dist/index.js'),str(data['root'])],root=data['root'],timeout=15,max_frame=262144)
    try:
        catalog=client.initialize(required=READ_TOOLS)
        for name in READ_TOOLS:
            matches=[tool for tool in catalog['tools'] if isinstance(tool,dict) and tool.get('name')==name]
            annotations=matches[0].get('annotations') if len(matches)==1 else None
            if not isinstance(annotations,dict) or annotations.get('readOnlyHint') is not True or annotations.get('destructiveHint') is True:raise ToolError('mcp_tool_denied')
        result=client.request('tools/call',{'name':'list_directory' if action=='list' else 'read_text_file','arguments':{'path':str(path)}})
        check()
        if result.get('isError'):raise ToolError('mcp_remote_error')
        content=result.get('content')
        if not isinstance(content,list) or len(content)!=1 or not isinstance(content[0],dict) or content[0].get('type')!='text' or not isinstance(content[0].get('text'),str):raise ToolError('mcp_protocol_invalid')
        value=content[0]['text']
        source='/api/v1/integrations/mcp-files/'+('catalog' if action=='list' else 'document')+'?'+urlencode({'root':root_id,'path':relative})
        if action=='read':
            if '\x00' in value:raise ToolError('tool_format_denied')
            return {'url':source,'title':'MCP · '+data['label']+' · '+relative,'text':value[:1200],'excerpt':value[:1200],'document':value[:MAX_TEXT],'document_characters':len(value),'truncated':len(value)>MAX_TEXT,'content_kind':'local_document'}
        entries=[];paths=[];omitted=0
        for line in value.splitlines():
            prefix='[FILE] ' if line.startswith('[FILE] ') else '[DIR] ' if line.startswith('[DIR] ') else None
            if prefix is None:raise ToolError('mcp_protocol_invalid')
            name=line[len(prefix):]
            if '/' in name or '\\' in name:omitted+=1;continue
            candidate=(relative+'/' if relative else '')+name
            try:local_path(data,candidate,read=prefix=='[FILE] ')
            except (ToolError,OSError):omitted+=1;continue
            entries.append(prefix+candidate)
            if prefix=='[FILE] ':paths.append(candidate)
        return {'url':source,'title':'MCP · '+data['label']+' · katalog '+(relative or '/'),'text':'\n'.join(entries) or 'Brak obsługiwanych dokumentów w tym katalogu.','paths':paths,'content_kind':'directory','truncated':False,'omitted_entries':omitted,'scope_note':'Tylko .md/.txt do 32 KiB; listowanie bez rekursji.'}
    finally:client.close()

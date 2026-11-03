"""Adaptery odczytu. Konfiguracja pochodzi wyłącznie z prywatnego dysku."""
import json
from typing import Protocol
from . import config
from .network import ToolError, valid_repo


class ReadAdapter(Protocol):
    name: str
    def read(self, name, arguments, scope): ...
    def status(self): ...


class GithubAdapter:
    name = 'github'

    def read(self, name, arguments, scope):
        from .network import execute
        return execute(name, arguments, scope)

    def configuration(self):
        path = config.DATA / 'github.json'
        if not path.exists():
            return {'repositories': [], 'credential': None}
        try:
            if path.stat().st_size > 16384: raise ValueError()
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            repos = data['repositories']
            if not isinstance(repos, list) or not repos or any(not valid_repo(r) for r in repos): raise ValueError()
            writes=data.get('write_repositories',[])
            if not isinstance(writes,list) or any(r!='kripusek/kripusek-autoexec' or r not in [p.lower() for p in repos] for r in writes):raise ValueError()
            return {'repositories': [r.lower() for r in repos], 'credential': data['credential'],'write_repositories':writes,'login':data.get('login')}
        except (OSError, ValueError, KeyError, TypeError):
            raise ToolError('integration_configuration_invalid') from None

    def token(self, repository):
        data = self.configuration()
        if repository.lower() not in data['repositories']: return None
        # DPAPI CurrentUser: sekret odszyfrowuje tylko konto Windows właściciela.
        try:
            import ctypes as c
            from ctypes import wintypes as w
            import base64
            class Blob(c.Structure):
                _fields_ = [('size', w.DWORD), ('data', c.POINTER(c.c_byte))]
            raw = base64.b64decode(data['credential'], validate=True)
            buf = c.create_string_buffer(raw)
            source = Blob(len(raw), c.cast(buf, c.POINTER(c.c_byte))); result = Blob()
            crypt = c.WinDLL('crypt32'); kernel = c.WinDLL('kernel32')
            crypt.CryptUnprotectData.argtypes = [c.POINTER(Blob), c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p, w.DWORD, c.POINTER(Blob)]
            kernel.LocalFree.argtypes = [c.c_void_p]
            if not crypt.CryptUnprotectData(c.byref(source), None, None, None, None, 1, c.byref(result)): raise ValueError()
            try: token = c.string_at(result.data, result.size).decode('utf-8')
            finally: kernel.LocalFree(result.data)
            if not token or any(ord(ch) < 33 or ord(ch) > 126 for ch in token): raise ValueError()
            return token
        except Exception: raise ToolError('integration_credential_unavailable') from None

    def status(self):
        try:
            data = self.configuration()
            return {'name': self.name, 'public': True, 'configured': bool(data['repositories']), 'repositories': data['repositories'], 'read_only': not bool(data.get('write_repositories')), 'write_repositories':data.get('write_repositories',[]),'login':data.get('login')}
        except ToolError as exc: return {'name': self.name, 'error': exc.code, 'read_only': True}

class WebAdapter:
    name = 'web'

    def read(self, name, arguments, scope):
        from .network import execute
        return execute(name, arguments, scope)

    def status(self):
        return {'name': self.name, 'configured': True, 'provider': 'Bing RSS', 'read_only': True}


class McpAdapter:
    name='mcp'
    def status(self):return {'name':self.name,'configured':True,'available':(config.ROOT/'scripts/mcp_docs_server.py').is_file(),'read_only':True,'provider':'Dokumentacja KripAI · MCP stdio'}
    def read(self,name,arguments,scope):
        if not scope.get('mcp'):raise ToolError('tool_permission_denied')
        if arguments['action']=='read' and arguments['path'] not in scope.get('documents',[]):raise ToolError('tool_resource_not_authorized')
        from .mcp_client import execute
        return execute(arguments['action'],arguments.get('path',''))

class McpFilesAdapter:
    name='mcp_files'
    def status(self):
        from .mcp_files import status
        return status()
    def read(self,name,arguments,scope):
        if not scope.get('mcp'):raise ToolError('tool_permission_denied')
        if arguments['action']=='read' and arguments['path'] not in scope.get('local_documents',[]):raise ToolError('tool_resource_not_authorized')
        from .mcp_files import execute
        return execute(arguments['action'],arguments.get('path',''),scope.get('mcp_files_root'))

ADAPTERS: dict[str, ReadAdapter] = {'github': GithubAdapter(), 'web': WebAdapter(),'mcp':McpAdapter(),'mcp_files':McpFilesAdapter()}
TOOL_ADAPTERS = {'github_read':'github','github_find':'github','web_read':'web','web_search':'web'}

def read(name, arguments, scope):
    if name=='mcp_docs':return ADAPTERS['mcp'].read(name,arguments,scope)
    if name=='mcp_files':return ADAPTERS['mcp_files'].read(name,arguments,scope)
    if name=='github_draft':
        from .github_changes import draft
        return draft(arguments,scope)
    if name not in TOOL_ADAPTERS: raise ToolError('tool_not_allowed')
    return ADAPTERS[TOOL_ADAPTERS[name]].read(name, arguments, scope)

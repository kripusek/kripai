"""Opcjonalny serwer MCP czasu: odizolowane, przypięte wheels, bez pip w runtime."""
import hashlib,json,os,re,shutil,sys,tempfile,threading,time,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config
from scripts.downloads import extract

VERSION='2026.10.28'
DIRECTORY='mcp-time-'+VERSION+'-py313'
MARKER='.kripai-mcp-time.json'
_lock=threading.Lock()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('mcp_time_download_denied')


def lock_bytes():
    return (config.ROOT/'scripts/mcp-time-lock.json').read_bytes()


def inventory(folder):
    result={};total=0
    def visit(path,depth=0):
        nonlocal total
        stat=path.lstat()
        if path.is_symlink() or getattr(stat,'st_file_attributes',0)&0x400 or depth>20:raise ValueError('linked runtime')
        if path.is_dir():
            for child in path.iterdir():
                if child!=folder/MARKER:visit(child,depth+1)
        else:
            total+=stat.st_size
            if len(result)>=6000 or total>128*1024**2:raise ValueError('runtime limit')
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(65536),b''):digest.update(block)
            result[path.relative_to(folder).as_posix()]=digest.hexdigest()
    visit(folder)
    return result


def verify(folder):
    try:
        if sys.platform!='win32' or sys.version_info[:2]!=(3,13):return False
        marker=folder/MARKER
        if marker.is_symlink() or getattr(marker.lstat(),'st_file_attributes',0)&0x400 or marker.stat().st_size>1024**2:return False
        data=json.loads(marker.read_text(encoding='utf-8'))
        if not all((folder/'deps'/name/'__init__.py').is_file() for name in ['mcp_server_time','mcp']):return False
        return data['version']==VERSION and data['lock_sha256']==hashlib.sha256(lock_bytes()).hexdigest() and data['inventory']==inventory(folder)
    except (OSError,ValueError,KeyError,TypeError,RecursionError):return False


def installed():
    for base in [config.ROOT,config.LOCAL/'KripAI']:
        folder=base/'runtime'/DIRECTORY
        if verify(folder):return folder
    return None


def prepare(check=lambda:None):
    with _lock:
        check()
        if sys.platform!='win32' or sys.version_info[:2]!=(3,13):raise ValueError('mcp_time_python_unavailable')
        lock=lock_bytes();data=json.loads(lock)
        if data.get('server_version')!=VERSION or data.get('sdk_version')!='2.3.0' or data.get('python')!='3.13' or not 1<=len(data.get('wheels',[]))<=50:raise ValueError('mcp_time_lock_invalid')
        if sum(item.get('size',64*1024**2) for item in data['wheels'])>64*1024**2:raise ValueError('mcp_time_lock_invalid')
        names={item.get('name') for item in data['wheels']}
        if not {'mcp_server_time-'+VERSION+'-py3-none-any.whl','mcp-2.3.0-py3-none-any.whl'}<=names:raise ValueError('mcp_time_lock_invalid')
        runtime=config.ROOT/'runtime';runtime.mkdir(exist_ok=True)
        if runtime.is_symlink() or getattr(runtime.lstat(),'st_file_attributes',0)&0x400:raise ValueError('mcp_time_installation_conflict')
        runtime=runtime.resolve();target=runtime/DIRECTORY
        if verify(target):return target
        if target.exists() and (target.is_symlink() or getattr(target.lstat(),'st_file_attributes',0)&0x400 or not (target/MARKER).is_file()):raise ValueError('mcp_time_installation_conflict')
        stage=Path(tempfile.mkdtemp(prefix='mcp-time-stage-',dir=runtime))
        try:
            deps=stage/'deps';deps.mkdir();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());deadline=time.monotonic()+180
            for item in data['wheels']:
                check()
                name=item['name'];url=urlsplit(item['url'])
                if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.whl',name) or not re.fullmatch(r'[a-f0-9]{64}',item['sha256']) or type(item['size']) is not int or not 0<item['size']<=32*1024**2 or url.scheme!='https' or url.netloc!='files.pythonhosted.org' or not url.path.startswith('/packages/') or url.query or url.fragment:raise ValueError('mcp_time_lock_invalid')
                if time.monotonic()>deadline:raise ValueError('mcp_time_prepare_timeout')
                file=stage/name;digest=hashlib.sha256();size=0
                with opener.open(item['url'],timeout=20) as response,file.open('wb') as out:
                    if response.geturl()!=item['url']:raise ValueError('mcp_time_download_denied')
                    while True:
                        chunk=response.read(65536)
                        if not chunk:break
                        size+=len(chunk)
                        if size>item['size'] or time.monotonic()>deadline:raise ValueError('mcp_time_download_denied')
                        digest.update(chunk);out.write(chunk)
                if size!=item['size'] or digest.hexdigest()!=item['sha256']:raise ValueError('mcp_time_download_denied')
                check();extract(file,deps);file.unlink()
            marker={'version':VERSION,'lock_sha256':hashlib.sha256(lock).hexdigest(),'inventory':inventory(stage)}
            (stage/MARKER).write_bytes(json.dumps(marker,sort_keys=True).encode())
            if not verify(stage):raise ValueError('mcp_time_installation_invalid')
            check()
            previous=None
            # Przenosimy wyłącznie własne katalogi w sprawdzonym runtime; stary zachowujemy.
            if target.resolve().parent!=runtime or stage.resolve().parent!=runtime:raise ValueError('mcp_time_installation_conflict')
            if target.exists():
                previous=runtime/(DIRECTORY+'-previous-'+str(uuid4()))
                if previous.resolve().parent!=runtime:raise ValueError('mcp_time_installation_conflict')
                target.rename(previous)
            try:stage.rename(target)
            except OSError:
                if previous is not None and not target.exists():previous.rename(target)
                raise
            return target
        finally:
            if stage.exists() and stage.resolve().parent==runtime and stage.name.startswith('mcp-time-stage-'):shutil.rmtree(stage)


if __name__=='__main__':
    try:prepare();print('MCP time prepared.')
    except Exception:print('MCP time preparation failed.',file=sys.stderr);sys.exit(1)

"""Opcjonalny, przypięty serwer MCP. Bez npx, kont npm i skryptów instalacyjnych."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,threading
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config

VERSION='2.1.0'
PACKAGE='@modelcontextprotocol/server-filesystem'
DIRECTORY='mcp-filesystem-'+VERSION
_lock=threading.Lock()

def node():
    if sys.platform!='win32':return None
    path=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'nodejs/node.exe'
    return path if path.is_file() else None

def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):result.update(chunk)
    return result.hexdigest()

def inventory(folder):
    result={}
    def visit(path):
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ValueError('linked runtime')
        if path.is_dir():
            for child in path.iterdir():visit(child)
        else:result[path.relative_to(folder).as_posix()]=digest(path)
        if len(result)>8000:raise ValueError('runtime file limit')
    visit(folder/'node_modules')
    return result

def lock_path():return config.ROOT/'scripts/mcp-filesystem/package-lock.json'

def verify(folder):
    try:
        marker=folder/'.kripai-mcp-filesystem.json'
        for path in [folder,marker]:
            if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:return False
        if marker.stat().st_size>2*1024**2:return False
        data=json.loads(marker.read_text(encoding='utf-8'))
        return data.get('version')==VERSION and data.get('lock_sha256')==digest(lock_path()) and data.get('files')==inventory(folder)
    except (OSError,ValueError,TypeError,AttributeError,RecursionError):return False

def installed():
    for root in [config.ROOT,config.LOCAL/'KripAI']:
        path=root/'runtime'/DIRECTORY
        if verify(path):return path
    return None

def npm_environment(stage,runtime):
    for name in ['user.npmrc','global.npmrc']:(stage/name).write_text('',encoding='ascii')
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP'}}
    env.update(PATH=str(node().parent)+os.pathsep+str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'),
        NPM_CONFIG_USERCONFIG=str(stage/'user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(stage/'global.npmrc'),
        NPM_CONFIG_CACHE=str(runtime/'mcp-npm-cache'),NPM_CONFIG_REGISTRY='https://registry.npmjs.org/',
        NPM_CONFIG_IGNORE_SCRIPTS='true',NPM_CONFIG_AUDIT='false',NPM_CONFIG_FUND='false')
    return env

def prepare():
    with _lock:return _prepare()

def _prepare():
    executable=node()
    if executable is None:raise ValueError('mcp_node_unavailable')
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP'}}
    version=subprocess.check_output([str(executable),'--version'],env=env,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW,timeout=5).decode('ascii').strip()
    if not version.startswith('v') or int(version[1:].split('.')[0])<24:raise ValueError('mcp_node_unavailable')
    runtime=config.ROOT/'runtime';runtime.mkdir(exist_ok=True)
    if runtime.is_symlink() or getattr(runtime.lstat(),'st_file_attributes',0)&0x400:raise ValueError('mcp_installation_conflict')
    target=runtime/DIRECTORY
    if verify(target):return target
    if target.exists() and not (target/'.kripai-mcp-filesystem.json').is_file():raise ValueError('mcp_installation_conflict')
    lock=json.loads(lock_path().read_text(encoding='utf-8'))
    for name,entry in lock['packages'].items():
        if name and (not entry.get('resolved','').startswith('https://registry.npmjs.org/') or not entry.get('integrity','').startswith('sha512-')):raise ValueError('mcp_lock_invalid')
    stage=Path(tempfile.mkdtemp(prefix='mcp-filesystem-stage-',dir=runtime))
    try:
        for name in ['package.json','package-lock.json']:shutil.copy2(lock_path().parent/name,stage/name)
        npm=executable.parent/'node_modules/npm/bin/npm-cli.js'
        result=subprocess.run([str(executable),str(npm),'ci','--ignore-scripts','--no-audit','--no-fund','--prefix',str(stage)],
            env=npm_environment(stage,runtime),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        if result.returncode:raise ValueError('mcp_install_failed')
        marker={'version':VERSION,'lock_sha256':digest(lock_path()),'files':inventory(stage)}
        (stage/'.kripai-mcp-filesystem.json').write_text(json.dumps(marker),encoding='utf-8')
        # Przenosimy wyłącznie znany pakiet pod runtime, zachowując poprzednią wersję.
        if stage.resolve().parent!=runtime.resolve() or target.resolve().parent!=runtime.resolve():raise ValueError('mcp_installation_conflict')
        if target.exists():target.rename(runtime/(DIRECTORY+'-before-'+str(uuid4())))
        stage.rename(target);return target
    finally:
        if stage.exists() and stage.resolve().parent==runtime.resolve() and stage.name.startswith('mcp-filesystem-stage-'):shutil.rmtree(stage)

if __name__=='__main__':
    try:prepare();print('Serwer MCP filesystem przygotowany (tylko odczyt przez KripAI).')
    except Exception:print('Nie przygotowano MCP. Wymagany Node 24+ i dostęp do publicznego npm.',file=sys.stderr);sys.exit(1)

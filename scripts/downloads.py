"""Pobieranie przypiętych plików z weryfikacją SHA-256 i wznowieniem."""
import hashlib
import json
import re
from urllib.parse import urlsplit
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import zipfile
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import config


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def extract(archive,destination):
    destination=Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path=Path(item.filename.replace('\\','/'))
            if path.is_absolute() or '..' in path.parts or ':' in item.filename:
                raise ValueError('Niedozwolona ścieżka w archiwum')
        z.extractall(destination)


def download(meta,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if sha256(path)==meta['sha256']:return path
        raise RuntimeError('Istniejący plik ma zmieniony SHA-256: '+path.name)
    partial=path.with_suffix(path.suffix+'.part')
    offset=partial.stat().st_size if partial.exists() else 0
    if offset and meta.get('size')==offset:
        if sha256(partial)==meta['sha256']:partial.replace(path);return path
        partial.unlink();offset=0
    request=urllib.request.Request(meta['url'],headers={'Range':f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(request,timeout=60) as response:
        append=offset>0 and response.status==206
        if append and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
            raise RuntimeError('Nieprawidłowy zakres pobierania')
        total=offset if append else 0;last=0
        with partial.open('ab' if append else 'wb') as f:
            while True:
                block=response.read(4*1024*1024)
                if not block:break
                f.write(block);total+=len(block)
                if time.monotonic()-last>5:
                    print(f'{path.name}: {total//(1024*1024)} MiB',flush=True);last=time.monotonic()
    if sha256(partial)!=meta['sha256']:
        partial.unlink();raise RuntimeError('Błąd SHA-256. Uruchom START.cmd ponownie; wadliwy fragment usunięto.')
    partial.replace(path)
    return path



def wheel_metadata(item):
    """PyPI podaje adres, ale zaufany hash i nazwa pochodzą wyłącznie z locka."""
    name=item['name']
    match=re.fullmatch(r'([A-Za-z0-9_]+)-([0-9][A-Za-z0-9_.]*)-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+\.whl',name)
    if not match:raise ValueError('Nieprawidłowa nazwa wheel w locku')
    project,version=match.group(1,2)
    with urllib.request.urlopen(f'https://pypi.org/pypi/{project}/{version}/json',timeout=30) as response:
        raw=response.read(2*1024**2+1)
    if len(raw)>2*1024**2:raise RuntimeError('Za duża odpowiedź metadanych PyPI')
    assets=[asset for asset in json.loads(raw)['urls']
            if asset.get('filename')==name and asset.get('digests',{}).get('sha256')==item['sha256']]
    if len(assets)!=1:raise RuntimeError('PyPI nie zawiera przypiętego pliku: '+name)
    asset=assets[0];url=urlsplit(asset['url'])
    if url.scheme!='https' or url.netloc!='files.pythonhosted.org' or not url.path.startswith('/packages/'):
        raise RuntimeError('Niedozwolony adres biblioteki')
    return {'url':asset['url'],'sha256':item['sha256']}


def dependencies():
    target=ROOT/'runtime/deps';target.mkdir(parents=True,exist_ok=True)
    for item in json.loads((ROOT/'scripts/vendor-lock.json').read_text()):
        if item['name'].endswith('.whl'):
            path=ROOT/'vendor'/item['name']
            if not path.exists():
                download(wheel_metadata(item),path)
            if sha256(path)!=item['sha256']:raise RuntimeError('Uszkodzona biblioteka: '+path.name)
            extract(path,target)


def binaries():
    meta=json.loads((ROOT/'scripts/llama-lock.json').read_text())
    destination=ROOT/'runtime/llama';destination.mkdir(parents=True,exist_ok=True)
    receipt=destination/'release.json'
    if not receipt.exists() or json.loads(receipt.read_text())!=meta:
        for asset in meta['assets']:
            archive=download(asset,ROOT/'runtime/cache'/asset['name'])
            extract(archive,destination)
        # Paczki upstream mogą mieć jeden dodatkowy katalog.
        executables=list(destination.rglob('llama-server.exe'))
        if len(executables)!=1:raise RuntimeError('Nie znaleziono jednoznacznie llama-server.exe')
        for source in list(destination.rglob('*.dll'))+executables:
            if source.parent!=destination:shutil.copy2(source,destination/source.name)
        receipt.write_text(json.dumps(meta))
    result=subprocess.run([str(destination/'llama-server.exe'),'--list-devices'],cwd=destination,capture_output=True,text=True,timeout=30)
    if result.returncode or 'CUDA' not in result.stdout+result.stderr:
        raise RuntimeError('CUDA niedostępna. Zaktualizuj sterownik NVIDIA dla Windows. Nie uruchamiam ukrytego trybu CPU.')
    model_meta=json.loads((ROOT/'scripts/model-lock.json').read_text())
    model=config.DATA/'models/model.gguf'
    if not model.exists() and shutil.disk_usage(config.DATA).free<model_meta['size']+2*1024**3:
        raise RuntimeError('Za mało miejsca: model potrzebuje około 5 GB i zapasu 2 GB.')
    print('Przygotowuję model; przy pierwszym starcie pobieram około 5 GB.',flush=True)
    download(model_meta,model)


def voice_files():
    meta=json.loads((ROOT/'scripts/voice-lock.json').read_text(encoding='utf-8'))
    destination=ROOT/'runtime/whisper'/meta['release']
    receipt=destination/'release.json'
    if not receipt.exists() or json.loads(receipt.read_text())!=meta:
        archive=download(meta['binary'],ROOT/'runtime/cache'/meta['binary']['name'])
        # Rozpakowanie do czystego katalogu zapobiega mieszaniu DLL różnych wersji.
        import tempfile
        with tempfile.TemporaryDirectory(dir=archive.parent) as temporary:
            unpacked=Path(temporary)
            extract(archive,unpacked)
            executables=list(unpacked.rglob('whisper-cli.exe'))
            if len(executables)!=1:raise RuntimeError('Nie znaleziono whisper-cli.exe')
            destination.mkdir(parents=True,exist_ok=True)
            for source in [executables[0],*executables[0].parent.glob('*.dll')]:
                shutil.copy2(source,destination/source.name)
        receipt.write_text(json.dumps(meta),encoding='utf-8')
    print('Przygotowuję lokalny głos: Whisper small, około 488 MB, CPU.',flush=True)
    download(meta['model'],config.DATA/'models'/meta['model']['name'])

def vision_files():
    meta=json.loads((ROOT/'scripts/vision-lock.json').read_text(encoding='utf-8'))
    folder=config.DATA/'models';folder.mkdir(parents=True,exist_ok=True)
    missing=sum(item['size'] for item in meta['assets'] if not (folder/item['name']).exists())
    if missing and shutil.disk_usage(folder).free<missing+2*1024**3:
        raise RuntimeError('Za mało miejsca na model obrazu i zapas 2 GB.')
    print('Przygotowuję model obrazu Qwen3-VL; pierwsze pobranie około 3.34 GB.',flush=True)
    for item in meta['assets']:download(item,folder/item['name'])


if __name__=='__main__':
    try:
        if sys.argv[1]=='deps':dependencies()
        elif sys.argv[1]=='model':binaries()
        elif sys.argv[1]=='voice':voice_files()
        elif sys.argv[1]=='vision':vision_files()
        else:raise ValueError('Nieznana operacja')
    except Exception as exc:
        print('Przygotowanie przerwane: '+str(exc),file=sys.stderr);sys.exit(1)

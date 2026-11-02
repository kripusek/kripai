"""Odcisk kodu uruchomionej paczki; bez modeli, danych i poświadczeń."""
import hashlib
from pathlib import Path

FOLDERS=('app','scripts','web','spec')
SUFFIXES={'.py','.ps1','.cmd','.json','.yaml','.yml','.sql','.js','.css','.html','.svg','.md'}

def fingerprint(root):
    root=Path(root);files=[];directories=0
    def visit(folder,depth=0):
        nonlocal directories
        directories+=1
        if depth>16 or directories>2000:raise ValueError('program directory limit')
        if folder.is_symlink() or getattr(folder.lstat(),'st_file_attributes',0)&0x400:raise ValueError('linked program directory')
        for item in folder.iterdir():
            if item.name=='__pycache__':continue
            if item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&0x400:raise ValueError('linked program file')
            if item.is_dir():visit(item,depth+1)
            elif item.suffix.lower() in SUFFIXES:files.append(item)
            if len(files)>2000:raise ValueError('program file limit')
    for name in FOLDERS:visit(root/name)
    files.extend(root.glob('*.cmd'))
    digest=hashlib.sha256();total=0
    for path in sorted(files,key=lambda p:p.relative_to(root).as_posix()):
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ValueError('linked launcher')
        with path.open('rb') as stream:raw=stream.read(2*1024**2+1)
        total+=len(raw)
        if len(raw)>2*1024**2 or total>16*1024**2:raise ValueError('program size limit')
        name=path.relative_to(root).as_posix().encode('utf-8')
        digest.update(len(name).to_bytes(4,'big'));digest.update(name);digest.update(hashlib.sha256(raw).digest())
    return digest.hexdigest()

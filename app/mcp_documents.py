"""Stały zakres MCP: publiczne Markdown programu, bez danych i poświadczeń."""
import re
from pathlib import Path
from .network import ToolError

MAX_BYTES=128*1024
MAX_TEXT=12000

def document(root,path):
    if not isinstance(path,str) or not re.fullmatch(r'[A-Za-z0-9_./-]{1,200}\.md',path) or any(p in {'','.','..'} or p.startswith('.') for p in path.split('/')):raise ToolError('mcp_path_denied')
    if path not in {'README.md','STATUS.md','PROJECT_STATE.md'} and not path.startswith(('docs/','spec/')):raise ToolError('mcp_path_denied')
    root=Path(root).resolve();target=root
    try:
        for part in path.split('/'):
            target=target/part;stat=target.lstat()
            if target.is_symlink() or getattr(stat,'st_file_attributes',0)&0x400:raise ToolError('mcp_path_denied')
        if not target.resolve().is_relative_to(root) or not target.is_file():raise ToolError('mcp_path_denied')
        with target.open('rb') as stream:raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ToolError('mcp_document_too_large')
        text=raw.decode('utf-8-sig')
        if '\x00' in text:raise ValueError()
        return {'path':path,'text':text[:MAX_TEXT],'excerpt':text[:1200],'truncated':len(text)>MAX_TEXT,'document_characters':len(text)}
    except FileNotFoundError:raise ToolError('mcp_document_missing') from None
    except (OSError,UnicodeError,ValueError):raise ToolError('mcp_document_unreadable') from None

def catalog(root):
    root=Path(root);candidates=['README.md','PROJECT_STATE.md','STATUS.md']
    # Nie przechodzimy przez dowiązania katalogów ani poza stały katalog programu.
    def visit(folder,depth=0):
        if depth>5:return
        try:entries=sorted(folder.iterdir(),key=lambda p:p.name)
        except OSError:return
        for entry in entries:
            try:
                if entry.name.startswith('.'):continue
                if entry.is_symlink() or getattr(entry.lstat(),'st_file_attributes',0)&0x400:continue
                if entry.is_dir():yield from visit(entry,depth+1)
                elif entry.suffix=='.md':yield entry.relative_to(root).as_posix()
            except OSError:continue
    for name in ['docs','spec']:
        folder=root/name
        try:
            if folder.is_symlink() or getattr(folder.lstat(),'st_file_attributes',0)&0x400:continue
        except OSError:continue
        candidates.extend(visit(folder))
    paths=[]
    for path in candidates:
        if len(paths)>=80:return {'paths':paths,'truncated':True}
        file=root/path
        try:
            if file.is_symlink() or getattr(file.lstat(),'st_file_attributes',0)&0x400:continue
            if re.fullmatch(r'[A-Za-z0-9_./-]{1,200}\.md',path) and file.is_file():paths.append(path)
        except OSError:continue
    return {'paths':paths,'truncated':False}

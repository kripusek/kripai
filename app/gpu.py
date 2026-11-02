"""Opcjonalny, tylko odczytowy pomiar całej karty przez zaufany nvidia-smi."""
import copy,csv,io,os,subprocess,sys,threading,time
from pathlib import Path
from . import config

_lock=threading.Lock();_cached=None;_expires=0

def command():
    if sys.platform!='win32':return None
    roots=[Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32',Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'NVIDIA Corporation/NVSMI']
    for root in roots:
        path=root/'nvidia-smi.exe'
        if path.is_file() and not path.is_symlink() and not getattr(path.lstat(),'st_file_attributes',0)&0x400:
            return [str(path),'--query-gpu=index,name,memory.used,memory.total,memory.free','--format=csv,noheader,nounits']
    return None

def parse(raw):
    if len(raw)>16384:raise ValueError('GPU output limit')
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))));devices=[];seen=set()
    for row in rows:
        if not row:continue
        if len(row)!=5:raise ValueError('GPU CSV shape')
        index=int(row[0].strip());name=row[1].strip();used,total,free=(int(value.strip()) for value in row[2:])
        if index<0 or index in seen or not name or not 0<total<=1048576 or not 0<=used<=total or not 0<=free<=total or used+free>total+2:raise ValueError('GPU values')
        seen.add(index);devices.append({'index':index,'name':name[:100],'used_mib':used,'total_mib':total,'free_mib':free})
    if not devices:raise ValueError('GPU absent')
    return {'available':True,'devices':devices[:16],'truncated':len(devices)>16}

def probe():
    try:
        args=command()
        if not args:return {'available':False,'error':'gpu_probe_unavailable'}
        result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=3,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if result.returncode:return {'available':False,'error':'gpu_driver_unavailable'}
        return parse(result.stdout)
    except subprocess.TimeoutExpired:return {'available':False,'error':'gpu_probe_timeout'}
    except (ValueError,UnicodeError,csv.Error):return {'available':False,'error':'gpu_data_invalid'}
    except OSError:return {'available':False,'error':'gpu_probe_failed'}

def snapshot():
    global _cached,_expires
    with _lock:
        if _cached is None or time.monotonic()>=_expires:
            _cached=dict(probe(),sampled_at=time.time());_expires=time.monotonic()+5
        result=copy.deepcopy(_cached)
    result.update(context_tokens=config.CONTEXT,output_tokens_per_segment=config.OUTPUT)
    return result

def reset():
    global _cached,_expires
    with _lock:_cached=None;_expires=0

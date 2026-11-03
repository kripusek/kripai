"""Lokalne wektory obrazu i tekstu: odizolowany proces CPU, bez sieci i GPU."""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
from . import config
from .processes import ModelJob

DIM=768
DIMENSIONS=DIM
SPACE='siglip2-base-p16-224-int8-ba1f3b0843f2-v1-768'


class VisualError(Exception):
    def __init__(self,code,status=409):self.code,self.status=code,status;super().__init__(code)


def encode(values):
    if not isinstance(values,list) or len(values)!=DIM or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise VisualError('visual_vector_invalid',422)
    norm=math.sqrt(sum(v*v for v in values))
    if not math.isfinite(norm) or norm<1e-12:raise VisualError('visual_vector_invalid',422)
    return struct.pack('<'+str(DIM)+'f',*(value/norm for value in values))


class Encoder:
    def __init__(self,folder,process,check):self.folder,self.process,self.check=folder,process,check
    def wait(self,name,timeout):
        deadline=time.monotonic()+timeout
        while True:
            self.check()
            if self.process.poll() is not None:raise VisualError('visual_encoder_failed',503)
            path=self.folder/name
            if path.is_file():
                if path.stat().st_size>64*1024:raise VisualError('visual_encoder_failed',503)
                try:return json.loads(path.read_text(encoding='utf-8'))
                except (OSError,ValueError):raise VisualError('visual_encoder_failed',503) from None
            if time.monotonic()>deadline:raise VisualError('visual_encoder_timeout',504)
            time.sleep(.05)
    def request(self,body):
        self.check()
        (self.folder/'request.tmp').write_bytes(json.dumps(body,ensure_ascii=False).encode())
        (self.folder/'request.tmp').replace(self.folder/'request.json')
        result=self.wait('response.json',30)
        (self.folder/'response.json').unlink()
        self.check()
        if isinstance(result,dict) and result.get('error') in {'visual_query_invalid','visual_query_too_large','visual_image_invalid','visual_vector_invalid','visual_request_invalid','visual_encode_failed'}:raise VisualError(result['error'],422)
        if not isinstance(result,dict):raise VisualError('visual_encoder_failed',503)
        return encode(result.get('embedding'))
    def embed_text(self,text):
        if not isinstance(text,str) or not 1<=len(text.strip())<=500:raise VisualError('visual_query_invalid',422)
        return self.request({'action':'text','text':text.strip()})
    def embed_image(self,image):
        if not isinstance(image,bytes) or not 1<=len(image)<=4*1024**2 or not image.startswith(b'\x89PNG\r\n\x1a\n'):raise VisualError('visual_image_invalid',422)
        self.check();(self.folder/'image.png').write_bytes(image)
        return self.request({'action':'image'})


@contextmanager
def session(check):
    from scripts.setup_visual import installed
    check();runtime=installed()
    if runtime is None:raise VisualError('visual_not_installed',503)
    check()
    root=config.DATA/'visual-tmp';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='job-',dir=root) as directory:
        folder=Path(directory);process=None;job=ModelJob(memory_limit=3*1024**3)
        try:
            env={key:value for key,value in os.environ.items() if key.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP','LOCALAPPDATA'}}
            env.update({'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false','PYTHONDONTWRITEBYTECODE':'1'})
            flags=(subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name=='nt' else 0
            process=subprocess.Popen([sys.executable,'-B',str(config.ROOT/'scripts/visual_worker.py'),str(runtime)],cwd=folder,
                                     env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
            job.attach(process);(folder/'job.ready').write_bytes(b'1')
            encoder=Encoder(folder,process,check)
            if encoder.wait('ready.json',60)!={'ready':True}:raise VisualError('visual_encoder_failed',503)
            yield encoder
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            job.close()

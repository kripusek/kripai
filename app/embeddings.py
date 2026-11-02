"""Mały encoder E5 na CPU, localhost i prywatny klucz. Proces żyje tylko na czas zadania."""
from contextlib import contextmanager
import hashlib
import os
import subprocess
import time
import httpx
from . import config
from .processes import ModelJob
from .vectors import LOCK,encode

class RagError(Exception):
    def __init__(self,code,status=409):self.code,self.status=code,status;super().__init__(code)

class Encoder:
    def __init__(self,client,check):self.client,self.check=client,check
    def tokens(self,text):
        self.check();r=self.client.post('/tokenize',json={'content':text,'add_special':True});r.raise_for_status()
        return len(r.json()['tokens'])
    def chunks(self,text):
        # Krótkie fragmenty i kontrola prawdziwym tokenizerem; bez cichego obcięcia.
        start=0
        while start<len(text):
            end=min(start+700,len(text))
            while self.tokens('passage: '+text[start:end])>480:
                end=start+(end-start)//2
                if end<=start:raise RagError('rag_chunk_too_large',422)
            yield text[start:end]
            if end==len(text):break
            start=max(start+1,end-80)
    def embed(self,text,query=False):
        self.check();value=('query: ' if query else 'passage: ')+text
        if self.tokens(value)>500:raise RagError('rag_query_too_large',422)
        r=self.client.post('/v1/embeddings',json={'input':value,'encoding_format':'float'});r.raise_for_status()
        self.check();return encode(r.json()['data'][0]['embedding'])

@contextmanager
def session(check):
    model=config.DATA/'models'/LOCK['model']['name']
    executable=config.ROOT/'runtime/llama/llama-server.exe'
    if not model.is_file() or not executable.is_file():raise RagError('rag_not_installed',503)
    # Hash przed startem, nie tylko przy pobraniu; modele nie pochodzą ze ścieżki pliku użytkownika.
    digest=hashlib.sha256()
    with model.open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):check();digest.update(block)
    if digest.hexdigest()!=LOCK['model']['sha256']:raise RagError('rag_model_checksum',503)
    command=[str(executable),'--model',str(model),'--host','127.0.0.1','--port','8767',
        '--device','none','--n-gpu-layers','0','--no-op-offload','--embedding','--pooling','mean',
        '--ctx-size','512','--batch-size','512','--ubatch-size','512','--parallel','1','--threads','4',
        '--api-key-file',str(config.DATA/'llm.key'),'--log-disable','--no-webui',
        '--override-kv',LOCK['metadata_override']]
    process=None;job=ModelJob(memory_limit=1536*1024**2)
    try:
        check()
        process=subprocess.Popen(command,cwd=config.ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        job.attach(process)
        with httpx.Client(base_url='http://127.0.0.1:8767',headers=config.llm_headers(),trust_env=False,timeout=10) as client:
            deadline=time.monotonic()+60
            while True:
                check()
                if process.poll() is not None:raise RagError('rag_encoder_failed',503)
                try:
                    if client.get('/v1/models').status_code==200:break
                except httpx.HTTPError:pass
                if time.monotonic()>deadline:raise RagError('rag_encoder_timeout',504)
                time.sleep(.1)
            yield Encoder(client,check)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        job.close()

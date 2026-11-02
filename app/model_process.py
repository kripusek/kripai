"""Właściciel procesu llama-server; dane rozmowy nigdy nie tworzą poleceń."""
import subprocess
import time
import httpx
from . import config
from .db import connect
from .processes import ModelJob

# Cache KV q8 oszczędza VRAM na karcie 8 GB; kontekst i wagi modelu bez zmian.
TEXT_OPTIONS=['--jinja','--chat-template-kwargs','{"enable_thinking":false}',
    '--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0']

class ModelProcess:
    def __init__(self,command=None,launch=subprocess.Popen,health=None,clock=time.monotonic):
        self.custom_command=command
        self.profile='text'
        self.command=command or [str(config.ROOT/'runtime/llama/llama-server.exe'),
            '--model',str(config.DATA/'models/model.gguf'),'--host','127.0.0.1','--port','8766',
            '--ctx-size',str(config.CONTEXT),'--n-gpu-layers','99','--parallel','1',
            '--api-key-file',str(config.DATA/'llm.key'),'--log-disable']+TEXT_OPTIONS
        self.launch=launch;self.health=health or self.probe;self.clock=clock
        self.process=None;self.started=0;self.state='offline';self.retry_at=0
        self.job=ModelJob()
    def command_for(self,profile):
        if self.custom_command:return self.custom_command
        command=[str(config.ROOT/'runtime/llama/llama-server.exe'),
            '--model',str(config.DATA/'models'/('model.gguf' if profile=='text' else 'vision-model.gguf')),
            '--host','127.0.0.1','--port','8766','--ctx-size',str(config.CONTEXT),
            '--n-gpu-layers','99','--parallel','1','--api-key-file',str(config.DATA/'llm.key'),'--log-disable']
        if profile=='text':command+=TEXT_OPTIONS
        else:command+=['--mmproj',str(config.DATA/'models/vision-mmproj.gguf'),'--no-mmproj-offload','--image-max-tokens','1024']
        return command
    def probe(self):
        with httpx.Client(timeout=2,headers=config.llm_headers(),trust_env=False) as client:
            # Endpoint chroniony kluczem: nie uznajemy obcej usługi /health za model.
            return client.get(config.LLM+'/v1/models').status_code==200 and client.get(config.LLM+'/health').status_code==200
    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
            self.process=None
        self.state='stopped'
    def step(self,mode,profile='text'):
        if profile not in {'text','vision'}:raise ValueError('Nieprawidłowy profil')
        if mode not in {'normal','gaming'}:raise ValueError('Nieprawidłowy tryb')
        if mode=='gaming':self.stop();self.retry_at=0;return self.state
        if profile!=self.profile:
            self.stop();self.profile=profile;self.command=self.command_for(profile);self.retry_at=0
        if self.clock()<self.retry_at:return 'error'
        try:
            if self.process is not None and self.process.poll() is not None:
                self.process=None;raise RuntimeError('Proces modelu zakończył się')
            if self.process is None:
                self.process=self.launch(self.command,cwd=config.ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.job.attach(self.process);self.started=self.clock()
            self.state='starting'
            try:
                if self.health():self.state='ready'
            except httpx.HTTPError:pass
            if self.state!='ready' and self.clock()-self.started>180:raise RuntimeError('Timeout modelu')
        except (OSError,RuntimeError,subprocess.SubprocessError):
            self.stop();self.state='error';self.retry_at=self.clock()+30
        return self.state
    def close(self):
        try:self.stop()
        finally:self.job.close()


def control(stop_event):
    manager=ModelProcess()
    try:
        while not stop_event.is_set():
            with connect() as conn:row=conn.execute('SELECT requested_mode,requested_profile FROM system_mode').fetchone()
            mode,profile=row['requested_mode'],row['requested_profile']
            state=manager.step(mode,profile)
            with connect() as conn:
                # Zmiana trybu podczas startu nie może nadpisać nowego żądania.
                conn.execute('UPDATE system_mode SET loaded_profile=?',(manager.profile if manager.process else 'none',))
                conn.execute('UPDATE system_mode SET controller_state=? WHERE requested_mode=? AND requested_profile=?',(state,mode,profile))
            stop_event.wait(.5)
    finally:
        manager.close()
        with connect() as conn:conn.execute("UPDATE system_mode SET controller_state='offline',loaded_profile='none'")

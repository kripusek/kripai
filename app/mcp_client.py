"""Ograniczony klient MCP stdio dla jednego wbudowanego serwera odczytu."""
import json
import os
import queue
import subprocess
import sys
import threading
import time
from urllib.parse import urlencode
from . import config
from .network import ToolError
from .processes import ModelJob

PROTOCOL='2025-11-25'
MAX_FRAME=65536

class StdioClient:
    def __init__(self,check=lambda:None,command=None,root=None,timeout=10):
        self.check=check;self.deadline=time.monotonic()+timeout;self.serial=0
        self.queue=queue.Queue(maxsize=4);self.stopped=threading.Event();self.job=ModelJob(memory_limit=128*1024**2);self.process=None
        root=root or config.ROOT
        command=command or [sys.executable,str(config.ROOT/'scripts/mcp_docs_server.py'),str(root)]
        env={key:value for key,value in os.environ.items() if key.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP'}}
        try:
            check();self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=root,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.job.attach(self.process)
            self.thread=threading.Thread(target=self.receive,daemon=True);self.thread.start()
        except BaseException:self.close();raise

    def receive(self):
        try:
            while not self.stopped.is_set():
                line=self.process.stdout.readline(MAX_FRAME+1)
                if not line:raise ToolError('mcp_disconnected')
                if len(line)>MAX_FRAME or not line.endswith(b'\n'):raise ToolError('mcp_protocol_invalid')
                value=json.loads(line.decode('utf-8'))
                while not self.stopped.is_set():
                    try:self.queue.put(value,timeout=.1);break
                    except queue.Full:continue
        except Exception as exc:
            error=exc if isinstance(exc,ToolError) else ToolError('mcp_protocol_invalid')
            while not self.stopped.is_set():
                try:self.queue.put(error,timeout=.1);break
                except queue.Full:continue

    def send(self,message):
        self.check()
        if time.monotonic()>self.deadline:raise ToolError('mcp_timeout')
        raw=json.dumps(message,ensure_ascii=False).encode('utf-8')+b'\n'
        if len(raw)>MAX_FRAME:raise ToolError('mcp_protocol_invalid')
        try:self.process.stdin.write(raw);self.process.stdin.flush()
        except OSError:raise ToolError('mcp_disconnected') from None

    def request(self,method,params):
        self.serial+=1;rid=self.serial
        self.send({'jsonrpc':'2.0','id':rid,'method':method,'params':params})
        for _ in range(32):
            while True:
                self.check()
                if time.monotonic()>self.deadline:raise ToolError('mcp_timeout')
                try:value=self.queue.get(timeout=.05);break
                except queue.Empty:continue
            if isinstance(value,Exception):raise value
            if not isinstance(value,dict) or value.get('jsonrpc')!='2.0':raise ToolError('mcp_protocol_invalid')
            if 'method' in value:
                if 'id' in value:self.send({'jsonrpc':'2.0','id':value['id'],'error':{'code':-32601,'message':'Client capability not available'}})
                continue
            if type(value.get('id')) is not int or value['id']!=rid or 'error' in value or not isinstance(value.get('result'),dict):raise ToolError('mcp_protocol_invalid')
            return value['result']
        raise ToolError('mcp_protocol_invalid')

    def initialize(self):
        result=self.request('initialize',{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'KripAI','version':'1.0.0'}})
        if result.get('protocolVersion')!=PROTOCOL or not isinstance(result.get('capabilities',{}).get('tools'),dict):raise ToolError('mcp_protocol_invalid')
        self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
        catalog=self.request('tools/list',{})
        names={tool.get('name') for tool in catalog.get('tools',[]) if isinstance(tool,dict)}
        if not {'list_documents','read_document'}<=names:raise ToolError('mcp_protocol_invalid')

    def close(self):
        self.stopped.set()
        if self.process:
            if self.process.stdin:
                try:self.process.stdin.close()
                except OSError:pass
            if self.process.poll() is None:
                try:self.process.wait(timeout=.3)
                except subprocess.TimeoutExpired:
                    self.job.close()
                    try:self.process.terminate()
                    except OSError:pass
                    try:self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
            self.job.close()
            if self.process.stdout:self.process.stdout.close()
        self.job.close()
        if hasattr(self,'thread'):self.thread.join(timeout=1)

def execute(action,path='',check=lambda:None):
    if action not in {'list','read'}:raise ToolError('mcp_tool_denied')
    client=StdioClient(check)
    try:
        client.initialize()
        result=client.request('tools/call',{'name':'list_documents' if action=='list' else 'read_document','arguments':{} if action=='list' else {'path':path}})
        content=result.get('content')
        if result.get('isError'):raise ToolError('mcp_remote_error')
        if not isinstance(content,list) or len(content)!=1 or not isinstance(content[0],dict) or content[0].get('type')!='text':raise ToolError('mcp_protocol_invalid')
        data=json.loads(content[0]['text'])
        if action=='list':
            paths=data['paths']
            if not isinstance(paths,list) or len(paths)>80 or any(not isinstance(p,str) or len(p)>200 for p in paths):raise ToolError('mcp_protocol_invalid')
            return {'url':'/api/v1/integrations/mcp/catalog','title':'MCP · dokumentacja KripAI','text':'\n'.join(paths),'paths':paths,'truncated':bool(data['truncated'])}
        if data['path']!=path or not isinstance(data['text'],str) or len(data['text'])>12000:raise ToolError('mcp_protocol_invalid')
        return {'url':'/api/v1/integrations/mcp/document?'+urlencode({'path':path}),'title':'MCP · '+path,'text':data['text'][:1200],'document':data['text'],'excerpt':data['text'][:1200],'truncated':bool(data['truncated']),'document_characters':data['document_characters'],'content_kind':'local_document'}
    except (ValueError,KeyError,TypeError):raise ToolError('mcp_protocol_invalid') from None
    finally:client.close()

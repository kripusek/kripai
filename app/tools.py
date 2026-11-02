"""Mały rejestr odczytu; zgody są z żądania właściciela, nie z tekstu modelu."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Literal
from pydantic import Field,ValidationError
from . import config
from .models import Strict
from .network import policy,ToolError
from .processes import ModelJob

class WebRead(Strict):
    url:str=Field(min_length=1,max_length=2048)
class GithubRead(Strict):
    repository:str=Field(min_length=3,max_length=201)
    section:Literal['readme','issues']
class GithubFind(Strict):
    query:str=Field(min_length=3,max_length=120)
REGISTRY={
 'web_read':(WebRead,'Read a public HTTPS URL explicitly present in the current user request. No JavaScript.'),
 'github_read':(GithubRead,'Read public README or open issues of owner/repo explicitly present in the current user request.'),
 'github_find':(GithubFind,'Search public GitHub repositories. Query must be a verbatim fragment of the current user request.')
}

def schemas(scope):
    allowed=['web_read'] if scope['web'] else []
    if scope['github']:allowed+=['github_read','github_find']
    return [{'type':'function','function':{'name':name,'description':REGISTRY[name][1],'parameters':REGISTRY[name][0].model_json_schema()}} for name in allowed]

def read(name,arguments,scope,check):
    allowed={tool['function']['name'] for tool in schemas(scope)}
    if name not in allowed:raise ToolError('tool_permission_denied')
    try:arguments=REGISTRY[name][0].model_validate(arguments).model_dump()
    except (ValidationError,TypeError):raise ToolError('tool_arguments_invalid') from None
    root=config.DATA/'tools-tmp';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='read-',dir=root) as directory:
        folder=Path(directory);(folder/'request.json').write_text(json.dumps({'name':name,'arguments':arguments,'scope':scope},ensure_ascii=False),encoding='utf-8')
        job=ModelJob(memory_limit=256*1024**2);process=None
        try:
            check();process=subprocess.Popen([sys.executable,str(config.ROOT/'scripts/read_web.py')],cwd=folder,
              stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            job.attach(process);(folder/'job.ready').touch();deadline=time.monotonic()+18
            while process.poll() is None:
                check()
                if time.monotonic()>deadline:raise ToolError('tool_timeout')
                time.sleep(.05)
            check();path=folder/'result.json'
            if process.returncode or not path.is_file() or path.stat().st_size>16000:raise ToolError('tool_read_failed')
            result=json.loads(path.read_text(encoding='utf-8'))
            if 'error' in result:raise ToolError(result['error'])
            return result['result']
        finally:
            if process is not None and process.poll() is None:process.kill();process.wait(timeout=5)
            job.close()

def plan(client,messages,scope,check,activity):
    definitions=schemas(scope)
    if not definitions:return []
    check();r=client.post(config.LLM+'/v1/chat/completions',json={'messages':messages,'tools':definitions,'tool_choice':'auto',
        'parallel_tool_calls':False,'stream':False,'max_tokens':256,'temperature':0,'chat_template_kwargs':{'enable_thinking':False}})
    r.raise_for_status();check();data=r.json();choice=data['choices'][0]
    if choice.get('finish_reason')=='length':raise ToolError('tool_plan_limit')
    calls=choice['message'].get('tool_calls') or []
    if not isinstance(calls,list) or len(calls)>2:raise ToolError('tool_call_limit')
    results=[]
    for call in calls:
        check();function=call['function'];name=function['name']
        if name not in {item['function']['name'] for item in definitions}:raise ToolError('tool_permission_denied')
        try:arguments=json.loads(function['arguments'])
        except (ValueError,TypeError):raise ToolError('tool_arguments_invalid') from None
        activity(name,'reading')
        try:
            result=read(name,arguments,scope,check);results.append(dict(result,name=name));activity(name,'completed')
        except ToolError as exc:
            results.append({'name':name,'error':exc.code});activity(name,exc.code)
    return results


def reset():
    import shutil
    folder=config.DATA/'tools-tmp'
    if folder.exists():shutil.rmtree(folder)

def sources(conn,mid):
    return conn.execute('SELECT ordinal,name,url,title,excerpt FROM tool_sources WHERE message_id=? ORDER BY ordinal',(mid,)).fetchall()

def save_sources(conn,mid,readings):
    for ordinal,item in enumerate(readings,1):
        if 'error' not in item:
            conn.execute('INSERT INTO tool_sources VALUES (?,?,?,?,?,?)',(mid,ordinal,item['name'],item['url'],item['title'],item['text']))

"""Rzeczywista próba CUDA, sieci i planera; bez prywatnej bazy i kont."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os, subprocess, tempfile, time, json
import httpx
from app import config, tools, network

def main():
    local=Path(os.environ['LOCALAPPDATA']); config.LLM='http://127.0.0.1:8768'
    command=[str(local/'KripAI/runtime/llama/llama-server.exe'),'--model',str(local/'KripAI-data/models/model.gguf'),'--host','127.0.0.1','--port','8768','--ctx-size','4096','--n-gpu-layers','99','--parallel','1','--jinja','--chat-template-kwargs','{"enable_thinking":false}','--log-disable']
    process=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        with httpx.Client(timeout=90,trust_env=False) as client:
            for _ in range(120):
                if process.poll() is not None:raise RuntimeError('model exited')
                try:
                    if client.get(config.LLM+'/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(1)
            else:raise RuntimeError('model readiness timeout')
            print('CUDA ready; context 4096',flush=True)
            print(subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.total','--format=csv']).decode(),flush=True)
            with tempfile.TemporaryDirectory(dir=config.ROOT/'reports') as folder:
                config.DATA=Path(folder)
                question='Odczytaj README repozytorium kripusek/kripai i podaj jego temat.'
                scope=network.policy(question,False,True)
                results=tools.plan(client,[{'role':'user','content':question}],scope,lambda:None,lambda name,state:print(name,state,flush=True))
                print(json.dumps([{'name':r['name'],'url':r.get('url'),'error':r.get('error')} for r in results]),flush=True)
                if not any(r.get('url') for r in results):raise RuntimeError('no real source')
                response=client.post(config.LLM+'/v1/chat/completions',json={'messages':[{'role':'user','content':question+'\n'+results[0].get('text','')[:1500]}],'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False}})
                response.raise_for_status();print(response.json()['choices'][0]['message']['content'],flush=True)
    finally:process.terminate();process.wait(timeout=20)

if __name__=='__main__':main()

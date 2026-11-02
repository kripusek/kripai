"""Regresja rzeczywistego CUDA: zwykła prośba przy włączonych narzędziach."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import re
import httpx
from unittest.mock import patch
from app import config,tools,generation
from app.context import prepare

def main():
    question='Napisz 50 ponumerowanych wskazówek nauki Pythona, każdą w dwóch zdaniach'
    history=[{'role':'user','content':question}]
    scope=tools.policy(question,True,True)
    with httpx.Client(timeout=120,headers=config.llm_headers(),trust_env=False) as client:
        planning,_,_=prepare(history,client,tool_definitions=tools.schemas(scope),budget=config.CONTEXT-512-128)
        with patch.object(tools,'read',side_effect=AssertionError('Unexpected network tool')):
            readings=tools.plan(client,planning,scope,lambda:None,lambda n,s:print(n,s,flush=True))
        print('Planner finished; network calls: 0',flush=True)
        messages,_,_=prepare(history,client,network=readings)
        text,reason=generation.generate(client,messages,lambda:None,lambda piece:None,lambda n:print('Segment',n,flush=True))
        numbers=[int(n) for n in re.findall(r'^\s*(\d+)\.',text,re.M)]
        print(json.dumps({'finish_reason':reason,'numbers':numbers,'characters':len(text),'text':text},ensure_ascii=True),flush=True)
        if reason=='length' or numbers!=list(range(1,51)):raise RuntimeError('Incomplete numbered answer')

if __name__=='__main__':main()

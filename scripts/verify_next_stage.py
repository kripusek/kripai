"""Rzeczywisty model i odczyt GitHuba. Ta próba nigdy nie publikuje PR."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
import json
import httpx
from app import config,tools,generation
from app.context import prepare

def main():
    with httpx.Client(timeout=120,headers=config.llm_headers(),trust_env=False) as client:
        client.get(config.LLM+'/health').raise_for_status()
        question='Wypisz po polsku ponumerowaną listę 30 wskazówek nauki Pythona. Każda wskazówka ma mieć jedno pełne zdanie. Nie skracaj listy.'
        messages,_,_=prepare([{'role':'user','content':question}],client)
        output=config.OUTPUT
        config.OUTPUT=128  # Wymuszenie granicy w krótkim teście rzeczywistego modelu.
        try:
            parts=[]
            text,reason=generation.generate(client,messages,lambda:None,lambda text:None,parts.append)
            print(json.dumps({'test':'continuation','segments':len(parts)+1,'reason':reason,'characters':len(text),'text':text},ensure_ascii=True),flush=True)
            if not parts:raise RuntimeError('continuation was not exercised')
        finally:config.OUTPUT=output
        with tempfile.TemporaryDirectory(dir=config.ROOT/'reports') as directory:
            config.DATA=Path(directory)
            question='Popraw czytelność i gramatykę README.md w kripusek/kripusek-autoexec. Zachowaj informacje i linki. Odczytaj plik i przygotuj konkretną lokalną propozycję PR narzędziem github_draft.'
            scope=dict(tools.policy(question,False,True),owner='qa-owner')
            messages,_,_=prepare([{'role':'user','content':question}],client,tool_definitions=tools.schemas(scope),budget=config.CONTEXT-512-128)
            results=tools.plan(client,messages,scope,lambda:None,lambda n,s:print(n,s,flush=True))
            print(json.dumps(results,ensure_ascii=True),flush=True)
            if not any(r.get('draft_id') for r in results):raise RuntimeError('model did not prepare a local proposal')
            print('No branch or PR published; isolated local draft removed.',flush=True)

if __name__=='__main__':main()

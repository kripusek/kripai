"""Próba na uruchomionym modelu: bez zapisu rozmów i prywatnych danych."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import tempfile
import httpx
from app import config, tools
from app.context import prepare

def main():
    # Klucz służy tylko do lokalnego transportu; nie zapisujemy go w raporcie.
    with httpx.Client(timeout=90,headers=config.llm_headers(),trust_env=False) as client:
        client.get(config.LLM+'/health').raise_for_status()
        with tempfile.TemporaryDirectory(dir=config.ROOT/'reports') as directory:
            config.DATA=Path(directory)
            for question,web,github in [
                ('Pokaż strukturę katalogu app w repozytorium kripusek/kripai.',False,True),
                ('Znajdź oficjalną dokumentację Pythona dotyczącą pathlib, odczytaj znalezioną stronę i wyjaśnij Path.exists().',True,False)]:
                history=[{'role':'user','content':question}]
                scope=tools.policy(question,web,github)
                planning,_,_=prepare(history,client,tool_definitions=tools.schemas(scope),budget=config.CONTEXT-512-128)
                readings=tools.plan(client,planning,scope,lambda:None,lambda n,s:print(n,s,flush=True))
                messages,_,tokens=prepare(history,client,network=readings)
                print(json.dumps({'question':question,'tokens':tokens,'sources':readings},ensure_ascii=True),flush=True)
                response=client.post(config.LLM+'/v1/chat/completions',json={'messages':messages,'max_tokens':512,'temperature':0,'chat_template_kwargs':{'enable_thinking':False}})
                response.raise_for_status()
                print(json.dumps(response.json()['choices'][0],ensure_ascii=True),flush=True)

if __name__=='__main__':main()

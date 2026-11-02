"""Kolejne porcje odpowiedzi mieszczą się w tym samym kontekście GPU."""
import json
import re
from . import config
from .tools import token_count

MAX_SEGMENTS = 8

class GenerationInterrupted(Exception):
    def __init__(self, text):
        self.text = text
        super().__init__('inference_interrupted')

def continuation(client, messages, answer):
    tail = answer[-6000:]
    while True:
        candidate = messages + [
            {'role':'assistant','content':tail},
            {'role':'user','content':'Kontynuuj dokładnie od miejsca przerwania. Nie powtarzaj wcześniejszego tekstu, nagłówków ani otwarcia bloku kodu. Dokończ pierwotną odpowiedź.'}]
        count = token_count(client, candidate)
        if count + 128 + 256 <= config.CONTEXT:
            return candidate, min(config.OUTPUT, config.CONTEXT-count-128)
        if len(tail) <= 100: raise GenerationInterrupted(answer)
        tail = tail[len(tail)//2:]

def safe_boundary(text):
    # Nowe żądanie nie potrafi niezawodnie dokończyć połowy słowa. Niepełną
    # ostatnią linię odtwarzamy, zaczynając od ostatniej kompletnej granicy.
    if text.endswith('\n'):return text
    if text.count('```')%2==0 and re.search(r'[.!?]["»”)]?$',text):return text+'\n'
    index=text.rfind('\n')
    if index>=0 and len(text)-index<1500:return text[:index+1]
    return text

def generate(client, messages, check, emit, activity=lambda segment:None, replace=lambda text:None):
    answer=''; current=messages; output=config.OUTPUT
    for segment in range(MAX_SEGMENTS):
        check()
        if segment: activity(segment+1)
        done=False; reason=None; piece_text=''
        try:
            with client.stream('POST',config.LLM+'/v1/chat/completions',json={
                'messages':current,'stream':True,'max_tokens':output,'temperature':0.6,
                'chat_template_kwargs':{'enable_thinking':False}}) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    check()
                    if line=='data: [DONE]':done=True;break
                    if not line.startswith('data: '):continue
                    choices=json.loads(line[6:]).get('choices',[])
                    if not choices:continue
                    reason=choices[0].get('finish_reason') or reason
                    piece=choices[0].get('delta',{}).get('content') or ''
                    answer+=piece;piece_text+=piece
                    if piece:emit(piece)
            if not done or not piece_text.strip():raise GenerationInterrupted(answer)
        except GenerationInterrupted:raise
        except Exception:
            # Cancel/Gaming sprawdzamy osobno: nie zamieniamy ich na błąd transportu.
            check()
            raise GenerationInterrupted(answer) from None
        if reason!='length':return answer,reason
        if segment+1 < MAX_SEGMENTS:
            stable=safe_boundary(answer)
            if stable!=answer:answer=stable;replace(answer)
            current,output=continuation(client,messages,answer)
    return answer,'length'

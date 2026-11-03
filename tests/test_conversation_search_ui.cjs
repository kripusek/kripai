const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {document,Node,walk}=require('../tests/dom.cjs');
const source=fs.readFileSync(path.join(__dirname,'../web/conversation-search.js'),'utf8');
const CID='12345678-1234-4234-8234-123456789abc';
const row=(seq=9)=>({conversation_id:CID,title:'Rozmowa',seq,role:'user',excerpt:'Znaleziony tekst',created_at:100});
const result=(items=[],next_cursor=null)=>({items,next_cursor,scanned_messages:20,partial:next_cursor!==null});
function harness(){
 const doc=document(),host=new Node('section'),calls=[],selected=[],queue=[];doc.getElementById('prompt').value='NIEWYSŁANY SZKIC';
 const ctx={document:doc,window:{}};vm.createContext(ctx);vm.runInContext(source,ctx);
 const api=ctx.window.KripConversationSearch;
 api.configure({host,api:async url=>{calls.push(url);const next=queue.shift();return typeof next==='function'?await next():next||result();},onSelect:async item=>selected.push(item)});
 const all=()=>walk(host),input=all().find(n=>n.tagName==='input'),form=all().find(n=>n.tagName==='form'),buttons=()=>all().filter(n=>n.tagName==='button');
 const submit=()=>form.onsubmit({preventDefault(){}}),find=text=>buttons().find(n=>n.textContent===text),status=()=>all().find(n=>n.attributes.role==='status').textContent;
 return {api,doc,host,calls,selected,queue,input,form,submit,find,status,all,results:()=>all().filter(n=>n.className==='conversation-search-result')};
}
test('wyszukiwanie dopiero po submit, literalny Unicode i kodowanie query; szkic pozostaje',async()=>{
 const h=harness();h.input.value='  Zażółć %_&🐈  ';h.input.listeners.input();assert.equal(h.calls.length,0);
 await h.submit();assert.equal(h.calls[0],'/conversations/search?q='+encodeURIComponent('Zażółć %_&🐈'));assert.equal(h.doc.getElementById('prompt').value,'NIEWYSŁANY SZKIC');
 assert.equal(h.all().find(n=>n.tagName==='label').textContent,'Fragment wiadomości');
 assert(!h.calls.some(url=>/messages|export|https?:/.test(url)));
});
test('jawna walidacja 2–120 znaków Unicode bez wywołania API dla złych danych',async()=>{
 const h=harness();for(const value of ['','a','x'.repeat(121),'a\u0000b']){h.input.value=value;await h.submit();assert.match(h.status(),/2 do 120/);}assert.equal(h.calls.length,0);
 h.input.value='🐈'.repeat(120);await h.submit();assert.equal(h.calls.length,1);
});
test('zero trafień może mieć następną stronę; częściowy wynik nie deklaruje całej historii',async()=>{
 const h=harness();h.input.value='tekst';h.queue.push(result([],'123'),result([row(90)]));await h.submit();
 assert.match(h.status(),/Brak dopasowań na tej stronie.*Nie sprawdzono jeszcze całej historii/);assert.equal(h.find('Przeszukaj starsze').hidden,false);
 await h.find('Przeszukaj starsze').onclick();assert.equal(h.calls[1],'/conversations/search?q=tekst&cursor=123');assert.equal(h.results().length,1);assert.equal(h.find('Przeszukaj starsze').hidden,true);assert.match(h.status(),/najstarszej wiadomości/);
});
test('kolejna strona zastępuje maksymalnie 20 wierszy, kliknięcie przekazuje dokładny seq i nie wysyła wiadomości',async()=>{
 const h=harness();h.input.value='tekst';h.queue.push(result(Array.from({length:20},(_,i)=>row(100-i)),'81'),result([row(3)]));await h.submit();assert.equal(h.results().length,20);
 const old=h.results()[0];await h.find('Przeszukaj starsze').onclick();assert.equal(h.results().length,1);await old.onclick();assert.equal(h.selected.length,0);
 await h.results()[0].onclick();assert.equal(h.selected[0].conversation_id,CID);assert.equal(h.selected[0].seq,3);assert.equal(h.calls.length,2);assert.equal(h.doc.getElementById('prompt').value,'NIEWYSŁANY SZKIC');
});
test('tytuł i fragment zawierające HTML są wyłącznie tekstem DOM',async()=>{
 const h=harness();h.input.value='tekst';h.queue.push(result([{...row(),title:'<script>bad()</script>',excerpt:'<img src=x onerror=bad()> & tekst'}]));await h.submit();
 const button=h.results()[0];assert(button.textContent.includes('<script>bad()</script>'));assert(button.textContent.includes('<img src=x onerror=bad()>'));assert.equal(walk(button).some(n=>['script','img'].includes(n.tagName)),false);
});
test('logout i edycja query unieważniają spóźniony wynik bez kolejnego żądania',async()=>{
 for(const logout of [true,false]){
  const h=harness();let resolve;h.queue.push(()=>new Promise(r=>resolve=r));h.input.value='tekst';const waiting=h.submit();
  if(logout)h.api.clear();else{h.input.value='nowy tekst';h.input.listeners.input();}
  resolve(result([row()],'100'));await waiting;assert.equal(h.results().length,0);assert.equal(h.find('Przeszukaj starsze').hidden,true);assert.equal(h.calls.length,1);if(logout)assert.equal(h.input.value,'');
 }
});
test('Wyczyść zeruje pola, a błąd API nie jest pustym wynikiem; starszą stronę można ponowić',async()=>{
 const h=harness();h.input.value='tekst';h.queue.push(result([row()],'80'),()=>{throw Error('Sesja wygasła.');});await h.submit();await h.find('Przeszukaj starsze').onclick();
 assert.match(h.status(),/Nie udało się.*Sesja wygasła/);assert(!h.status().includes('Brak dopasowań'));assert.equal(h.find('Przeszukaj starsze').hidden,false);
 h.queue.push(result([row(2)]));await h.find('Przeszukaj starsze').onclick();assert.equal(h.calls[1],h.calls[2]);
 h.find('Wyczyść').onclick();assert.equal(h.input.value,'');assert.equal(h.results().length,0);assert.equal(h.find('Przeszukaj starsze').hidden,true);
});
test('niepoprawne metadane i zbyt duża strona są błędem bez renderowania',async()=>{
 for(const data of [{...result(),items:Array.from({length:21},()=>row())},{...result(),next_cursor:'../unsafe'},{...result(),items:[{...row(),seq:-1}]},{...result(),scanned_messages:2001}]){
  const h=harness();h.input.value='tekst';h.queue.push(data);await h.submit();assert.match(h.status(),/Nie udało się.*Nieprawidłowa/);assert.equal(h.results().length,0);
 }
});
test('powtórzone submit podczas żądania nie dubluje API',async()=>{
 const h=harness();let resolve;h.input.value='tekst';h.queue.push(()=>new Promise(r=>resolve=r));const waiting=h.submit();await h.submit();assert.equal(h.calls.length,1);resolve(result());await waiting;
});
test('błąd otwarcia trafienia ma komunikat, a kursor musi prowadzić do starszych wiadomości',async()=>{
 const h=harness();h.input.value='tekst';h.queue.push(result([row()],'80'),result([],'80'));await h.submit();
 h.api.configure({host:h.host,api:async()=>result([],'80'),onSelect:async()=>{throw Error('failure');}});
 await h.results()[0].onclick();assert.match(h.status(),/Nie udało się otworzyć/);await h.find('Przeszukaj starsze').onclick();assert.match(h.status(),/nie przesunął wyszukiwania/);assert.equal(h.results().length,0);
});

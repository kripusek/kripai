const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {webcrypto}=require('node:crypto'),{document,Node}=require('../tests/dom.cjs');
const source=fs.readFileSync(path.join(__dirname,'../web/conversation-branch.js'),'utf8');
const CID='12345678-1234-4234-8234-123456789abc',MID='22345678-1234-4234-8234-123456789abc',NEW='32345678-1234-4234-8234-123456789abc';
const response=()=>({id:NEW,title:'Nowa rozmowa',created_at:100,copied_messages:2});

test('ponowne renderowanie tego samego kontekstu unieważnia stare przyciski',async()=>{
 const h=harness();h.api.setContext(CID);const container=new Node('article'),button=h.api.attach(container,{conversationId:CID,messageId:MID,role:'assistant'});h.api.setContext(CID,true);await button.onclick();assert.equal(h.calls.length,0);assert.equal(button.disabled,true);
});
function harness(){
 const doc=document(),calls=[],opened=[],notices=[],queue=[],ctx={document:doc,window:{},crypto:webcrypto};doc.getElementById('prompt').value='NIEWYSŁANY SZKIC';
 vm.createContext(ctx);vm.runInContext(source,ctx);const api=ctx.window.KripConversationBranch;
 api.configure({api:async(...args)=>{calls.push(args);const next=queue.shift();return typeof next==='function'?await next():next||response();},onBranch:async value=>opened.push(value),notice:text=>notices.push(text)});api.setContext(CID);
 const attach=(extra={},container=new Node('div'))=>({container,button:api.attach(container,{conversationId:CID,messageId:MID,role:'assistant',...extra})});
 return {api,doc,ctx,calls,opened,notices,queue,attach};
}
test('tylko jawny klik tworzy nową rozmowę i przekazuje wynik bez zmiany szkicu lub wysyłania wiadomości',async()=>{
 const h=harness(),{button}=h.attach();assert.equal(h.calls.length,0);assert.equal(button.textContent,'Nowa rozmowa od tej odpowiedzi');await button.onclick();
 assert.equal(h.calls[0][0],'/conversations/'+CID+'/branch');assert.equal(h.calls[0][1],'POST');assert.deepEqual(JSON.parse(JSON.stringify(h.calls[0][2])),{message_id:MID});assert.match(h.calls[0][3],/^[a-f0-9-]{36}$/);assert.equal(h.opened[0].id,NEW);assert.equal(h.doc.getElementById('prompt').value,'NIEWYSŁANY SZKIC');assert(!h.calls.some(args=>args[0].includes('/messages')));
});
test('tylko odpowiedź asystenta z UUID i bieżącej rozmowy ma działanie',()=>{
 const h=harness();for(const input of [{role:'user'},{role:'tool'},{messageId:'../../x'},{conversationId:'../../x'},{conversationId:NEW}])assert.equal(h.attach(input).button,null);
 h.api.clear();assert.equal(h.attach().button,null);assert.equal(h.calls.length,0);
});
test('utracona odpowiedź zachowuje ten sam klucz dla tego samego przycisku, inny przycisk ma własny klucz',async()=>{
 const h=harness(),first=h.attach().button,second=h.attach({messageId:NEW}).button;h.queue.push(()=>{throw Error('network lost');});await first.onclick();assert.match(h.notices[0],/bezpiecznie ponowić/);await first.onclick();await second.onclick();
 assert.equal(h.calls[0][3],h.calls[1][3]);assert.notEqual(h.calls[0][3],h.calls[2][3]);assert.equal(h.opened.length,2);
});
test('generowanie i trwająca operacja blokują wszystkie przyciski i podwójny klik',async()=>{
 const h=harness(),first=h.attach().button,second=h.attach().button;h.api.setBusy(true);assert(first.disabled);await first.onclick();assert.equal(h.calls.length,0);h.api.setBusy(false);
 let resolve;h.queue.push(()=>new Promise(r=>resolve=r));const wait=first.onclick();assert(first.disabled&&second.disabled);await first.onclick();await second.onclick();assert.equal(h.calls.length,1);resolve(response());await wait;assert(!first.disabled&&!second.disabled);
});
test('zmiana rozmowy i logout odrzucają późny wynik oraz stare przyciski',async()=>{
 for(const logout of [true,false]){
  const h=harness(),{button}=h.attach();let resolve;h.queue.push(()=>new Promise(r=>resolve=r));const wait=button.onclick();if(logout)h.api.clear();else h.api.setContext(NEW);resolve(response());await wait;
  assert.equal(h.opened.length,0);assert(button.disabled);await button.onclick();assert.equal(h.calls.length,1);assert.equal(h.notices.length,0);
 }
});
test('wadliwy protokół nie otwiera rozmowy; tytuł serwera pozostaje zwykłymi danymi',async()=>{
 for(const bad of [{id:'../../x'},{id:CID},{copied_messages:0},{copied_messages:1001},{created_at:Infinity},{title:5}]){
  const h=harness(),{button}=h.attach();h.queue.push({...response(),...bad});await button.onclick();assert.equal(h.opened.length,0);assert.match(h.notices[0],/nieprawidłowe dane/);
 }
 const h=harness(),{button,container}=h.attach();h.queue.push({...response(),title:'<img src=x onerror=bad()>'});await button.onclick();assert.equal(h.opened[0].title,'<img src=x onerror=bad()>');assert.equal(container.children.length,1);assert(!container.textContent.includes('<img'));
});
test('powtórne attach do tego samego kontenera nie dubluje przycisku ani nie gubi klucza',async()=>{
 const h=harness(),{button,container}=h.attach();h.queue.push(()=>{throw Error('offline');});await button.onclick();assert.equal(h.attach({},container).button,button);assert.equal(container.children.length,1);h.api.setContext(CID);await button.onclick();assert.equal(h.calls[0][3],h.calls[1][3]);
});
test('brak randomUUID ma jawny komunikat i nie wysyła żądania',async()=>{
 const h=harness(),{button}=h.attach();h.ctx.crypto={};await button.onclick();assert.equal(h.calls.length,0);assert.match(h.notices[0],/Przeglądarka/);assert.equal(button.disabled,false);
});
test('znane błędy backendu mają wskazówki, a prywatny opis serwera nie jest wyświetlany',async()=>{
 for(const [code,message] of [['not_found',/Odśwież historię/],['branch_point',/odpowiedzi asystenta/],['branch_too_large',/1000 wiadomości lub 8 MiB/],['generation_busy',/Poczekaj na zakończenie/],['login_required',/Zaloguj się ponownie/]]){
  const h=harness(),{button}=h.attach();h.queue.push(()=>{throw Object.assign(Error('PRIVATE_SERVER_DETAIL'),{code});});await button.onclick();assert.match(h.notices[0],message);assert(!h.notices[0].includes('PRIVATE'));assert.equal(button.disabled,false);
 }
});

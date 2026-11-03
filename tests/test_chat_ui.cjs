const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs'),marked=require('../web/vendor/marked/marked.umd.js');
const tick=()=>new Promise(r=>setImmediate(r));

test('odgałęzienie otwiera nowy kontekst bez wysłania wiadomości i zachowuje szkic',async()=>{
 let configured;const contexts=[],h=await harness({KripConversationBranch:{configure(value){configured=value;},setContext:(...args)=>contexts.push(args),setBusy(){},clear(){},attach(){}}});h.doc.getElementById('prompt').value='Szkic nowej wersji';await configured.onBranch({id:'fork-cid',title:'Gałąź'});
 assert(contexts.some(([id,reset])=>id==='fork-cid'&&reset===true));assert(h.calls.some(([url])=>url==='/api/v1/conversations/fork-cid/messages?limit=50'));assert.equal(h.doc.getElementById('prompt').value,'Szkic nowej wersji');assert(!h.calls.some(([url,options])=>url.includes('/messages')&&options.method==='POST'));
});
test('logout podczas otwierania gałęzi blokuje późny komunikat i zawartość',async()=>{
 let configured,resolve;const h=await harness({KripConversationBranch:{configure(value){configured=value;},setContext(){},setBusy(){},clear(){},attach(){}}}),original=h.ctx.fetch;
 h.ctx.fetch=(url,options)=>url.includes('/fork-cid/messages')?new Promise(r=>resolve=r):original(url,options);const pending=configured.onBranch({id:'fork-cid',title:'Prywatna'});await h.doc.getElementById('logout').onclick();resolve({ok:true,status:200,json:async()=>({items:[],next_cursor:null})});await pending;assert.equal(h.doc.getElementById('messages').children.length,0);assert.equal(h.doc.getElementById('notice').textContent,'');assert.equal(h.doc.getElementById('workspace').hidden,true);
});

test('wybór wyniku szuka dokładnego at, Najnowsze wraca do końca i szkic pozostaje',async()=>{
 let configured,cleared=0;const h=await harness({KripConversationSearch:{configure(value){configured=value;},clear(){cleared++;}}});h.doc.getElementById('prompt').value='Niewysłany szkic';await configured.onSelect({conversation_id:'cid',title:'Historia',seq:7});
 assert(h.calls.some(([url])=>url==='/api/v1/conversations/cid/messages?limit=50&at=7'));assert.equal(h.doc.getElementById('latest').hidden,false);assert.equal(h.doc.getElementById('prompt').value,'Niewysłany szkic');
 h.doc.getElementById('latest').onclick();await tick();await tick();assert.equal(h.doc.getElementById('latest').hidden,true);assert(!h.calls.some(([url,options])=>url.includes('/messages')&&options.method==='POST'));
 await h.doc.getElementById('logout').onclick();assert.equal(cleared,1);
});
test('wynik wyszukiwania nie przerywa bieżącego streamu odpowiedzi',async()=>{
 let configured;const h=await harness({KripConversationSearch:{configure(value){configured=value;},clear(){}}});h.doc.getElementById('prompt').value='Pytanie';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});await configured.onSelect({conversation_id:'other',title:'Inna',seq:8});
 assert(!h.calls.some(([url])=>url.includes('&at=')));assert.equal(h.doc.getElementById('latest').disabled,true);assert.match(h.doc.getElementById('notice').textContent,/Poczekaj/);
});

test('nowa rozmowa ustawia działania dla właściwego ID, a logout je czyści',async()=>{
 const h=await harness(),selected=[];let clears=0;h.ctx.window.KripConversations={setCurrent:(...args)=>selected.push(args),clear:()=>clears++};
 h.doc.getElementById('prompt').value='Niewysłany szkic';await h.doc.getElementById('newChat').onclick();assert(selected.some(([id])=>id==='cid'));assert.equal(h.doc.getElementById('prompt').value,'Niewysłany szkic');await h.doc.getElementById('logout').onclick();assert.equal(clears,1);
});
test('spóźnione utworzenie rozmowy nie odtwarza działań po logout',async()=>{
 const h=await harness(),selected=[],original=h.ctx.fetch;let resolve;h.ctx.window.KripConversations={setCurrent:(...args)=>selected.push(args),clear(){}};
 h.ctx.fetch=(url,options)=>url==='/api/v1/conversations'&&options.method==='POST'?new Promise(r=>resolve=r):original(url,options);
 const pending=h.doc.getElementById('newChat').onclick();await h.doc.getElementById('logout').onclick();resolve({ok:true,status:201,json:async()=>({id:'old-private-cid'})});await pending;assert.equal(selected.length,0);assert.equal(h.doc.getElementById('workspace').hidden,true);
});

test('MCP jest jawną flagą wiadomości, bez konieczności włączania internetu',async()=>{
 const h=await harness();h.ctx.window.KripTools={permissions:()=>({allow_mcp:true}),renderSources(){},clear(){}};
 h.doc.getElementById('prompt').value='Przeczytaj README.md przez MCP';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 const body=JSON.parse(h.calls.find(([u,o])=>u.includes('/messages')&&o.method==='POST')[1].body);
 assert.equal(body.allow_mcp,true);assert(!body.allow_web);assert(!body.allow_github);
});

test('kontynuacja zastępuje niepełną linię i ignoruje powtórzony snapshot SSE',async()=>{
 const h=await harness();h.doc.getElementById('prompt').value='Długa odpowiedź';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 const events=h.streams[0].events;
 events['assistant.text.delta']({lastEventId:'1',data:JSON.stringify({text:'1. Gotowe.\n2. Poło'})});
 events['assistant.text.snapshot']({lastEventId:'2',data:JSON.stringify({text:'1. Gotowe.\n'})});
 events['assistant.text.snapshot']({lastEventId:'2',data:JSON.stringify({text:'Powtórzony błędny tekst'})});
 events['assistant.text.delta']({lastEventId:'3',data:JSON.stringify({text:'2. Gotowe.'})});
 await new Promise(r=>setTimeout(r,100));
 const text=walk(h.doc.getElementById('messages')).find(n=>n._raw==='1. Gotowe.\n2. Gotowe.');assert(text);
});
test('spóźniona lista rozmów nie wraca do DOM po wylogowaniu',async()=>{
 const h=await harness(),original=h.ctx.fetch;let resolve;
 h.ctx.fetch=(url,options)=>url.startsWith('/api/v1/conversations?')?new Promise(r=>resolve=r):original(url,options);
 const pending=vm.runInContext('list()',h.ctx);await h.doc.getElementById('logout').onclick();
 resolve({ok:true,status:200,json:async()=>({items:[{id:'old',title:'Prywatny tytuł fixture'}],next_cursor:null})});await pending;
 assert.equal(h.doc.getElementById('conversations').children.length,0);assert.equal(h.doc.getElementById('workspace').hidden,true);
});
test('spóźnione me nie otwiera wylogowanej aplikacji',async()=>{
 const h=await harness(),original=h.ctx.fetch;let resolve;
 h.ctx.fetch=(url,options)=>url==='/api/v1/me'?new Promise(r=>resolve=r):original(url,options);
 const pending=vm.runInContext('enter()',h.ctx);await h.doc.getElementById('logout').onclick();
 resolve({ok:true,status:200,json:async()=>({id:'owner'})});await pending;
 assert.equal(h.doc.getElementById('workspace').hidden,true);assert.equal(h.doc.getElementById('login').hidden,false);
 assert.equal(h.doc.getElementById('send').disabled,true);assert.equal(h.doc.getElementById('older').hidden,true);
});
test('stare 401 nie wylogowuje ponownie zalogowanej sesji',async()=>{
 const h=await harness(),original=h.ctx.fetch;let resolve,first=true;
 h.ctx.fetch=(url,options)=>{if(url==='/api/v1/me'&&first){first=false;return new Promise(r=>resolve=r);}return original(url,options);};
 const oldEntry=vm.runInContext('enter()',h.ctx);await h.doc.getElementById('logout').onclick();await vm.runInContext('enter()',h.ctx);
 assert.equal(h.doc.getElementById('workspace').hidden,false);
 resolve({ok:false,status:401,json:async()=>({error:{code:'login_required'}})});await oldEntry;
 assert.equal(h.doc.getElementById('workspace').hidden,false);assert.equal(h.doc.getElementById('login').hidden,true);
});
async function harness(features={}){
 const doc=document(),calls=[],streams=[],saved=new Map(),revoked=[];doc.cookie='assistant_csrf=token';doc.querySelectorAll=()=>[];
 const ctx={document:doc,window:{addEventListener(){},...features},marked,URL:{createObjectURL:()=> 'blob:preview',revokeObjectURL:u=>revoked.push(u)},crypto:{randomUUID:()=>Math.random().toString(36)},AbortController,setTimeout,clearTimeout,setInterval(){},navigator:{clipboard:{writeText:async()=>{}}},sessionStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},KripVoice:{stop(){},configure(){},setBlocked(){},speak(){}},KripMedia:{hide(){},stop(){},configure(){},setBlocked(){}},EventSource:function(){this.events={};this.addEventListener=(k,fn)=>this.events[k]=fn;this.close=()=>{};streams.push(this);},fetch:async(url,options={})=>{
  calls.push([url,options]);let data={};if(url==='/api/v1/me')data={id:'owner'};
  else if(url.includes('/system/status'))data={controller:'ready',profile:'text',mode:'normal',backup:'ready'};
  else if(url.startsWith('/api/v1/media/jobs/'))data={id:'image-id'};
  else if(url==='/api/v1/conversations'&&options.method==='POST')data={id:'cid'};
  else if(url.includes('/messages')&&options.method==='POST')data={run_id:'rid'};
  else if(url.includes('/conversations'))data={items:[],next_cursor:null};
  return {ok:true,status:url==='/api/v1/auth/logout'?204:200,json:async()=>data};
 }};
 vm.createContext(ctx);for(const name of ['format.js','attachments.js']){vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/'+name),'utf8'),ctx);Object.assign(ctx,ctx.window);}
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),ctx);await tick();
 function paste(files=[{type:'image/png',size:20,name:'x.png'}]){doc.getElementById('prompt').listeners.paste({clipboardData:{items:files.map(f=>({kind:'file',getAsFile:()=>f}))},preventDefault(){}});}
 return {doc,ctx,calls,streams,paste,revoked};
}
test('Ctrl+V lokalnie, następnie jedno zdjęcie i pytanie w wiadomości oraz Markdown w streamie',async()=>{
 const h=await harness();h.paste();assert(!h.calls.some(([u])=>u.includes('/media/')));assert.equal(h.doc.getElementById('attachedImage').src,'blob:preview');h.doc.getElementById('prompt').value='Rozwiąż zadanie';
 await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 const sends=h.calls.filter(([u,o])=>u.includes('/messages')&&o.method==='POST');assert.equal(sends.length,1);assert.equal(JSON.parse(sends[0][1].body).attachment_id,'image-id');
 assert(walk(h.doc.getElementById('messages')).some(n=>n.tagName==='img'));
 h.streams[0].events['assistant.text.delta']({lastEventId:'1',data:JSON.stringify({text:'### Wynik\n\n**Tak**'})});await new Promise(r=>setTimeout(r,100));assert(walk(h.doc.getElementById('messages')).some(n=>n.tagName==='h3'));
});
test('samo zdjęcie ma pytanie domyślne, logout usuwa historię i ignoruje późny stream',async()=>{
 const h=await harness();h.paste();await h.doc.getElementById('composer').onsubmit({preventDefault(){}});const body=JSON.parse(h.calls.find(([u,o])=>u.includes('/messages')&&o.method==='POST')[1].body);assert.equal(body.text,'Opisz to zdjęcie.');
 await h.doc.getElementById('logout').onclick();h.streams[0].events['assistant.text.delta']({lastEventId:'1',data:JSON.stringify({text:'Prywatny tekst'})});await new Promise(r=>setTimeout(r,100));assert.equal(h.doc.getElementById('messages').children.length,0);
});
test('anulowany upload nie wysyła wiadomości po spóźnionej odpowiedzi',async()=>{
 const h=await harness();let resolve;const original=h.ctx.fetch;h.ctx.fetch=(u,o)=>u.includes('/media/')&&!u.endsWith('/cancel')?new Promise(r=>resolve=r):original(u,o);
 h.paste();const pending=h.doc.getElementById('composer').onsubmit({preventDefault(){}});await h.doc.getElementById('cancel').onclick();resolve({ok:true,json:async()=>({id:'late'})});await pending;
 assert(!h.calls.some(([u,o])=>u.includes('/messages')&&o.method==='POST'));assert(!h.ctx.KripAttachments.has());
});
test('anulowanie zaakceptowanej wiadomości zatrzymuje run po otrzymaniu ID',async()=>{
 const h=await harness();let resolve;const original=h.ctx.fetch;h.ctx.fetch=(u,o)=>u.includes('/messages')&&o.method==='POST'?new Promise(r=>resolve=r):original(u,o);
 h.doc.getElementById('prompt').value='Pytanie';const pending=h.doc.getElementById('composer').onsubmit({preventDefault(){}});await tick();await h.doc.getElementById('cancel').onclick();resolve({ok:true,status:202,json:async()=>({run_id:'late'})});await pending;assert(h.calls.some(([u])=>u==='/api/v1/runs/late/cancel'));assert.equal(h.streams.length,0);
});
test('błąd uploadu zachowuje miniaturę do ponowienia',async()=>{
 const h=await harness();const original=h.ctx.fetch;h.ctx.fetch=(u,o)=>u.includes('/media/')?Promise.resolve({ok:false}):original(u,o);h.paste();await h.doc.getElementById('composer').onsubmit({preventDefault(){}});assert(h.ctx.KripAttachments.has());assert.equal(h.doc.getElementById('send').disabled,false);assert(!h.calls.some(([u,o])=>u.includes('/messages')&&o.method==='POST'));
});
test('zły format, zbyt duży plik i wiele zdjęć nie zastępują istniejącego',async()=>{
 const h=await harness();h.paste();h.paste([{type:'text/html',size:2}]);h.paste([{type:'image/png',size:9*1024*1024}]);h.paste([{type:'image/png',size:2},{type:'image/png',size:3}]);assert.equal(h.revoked.length,0);assert(h.ctx.KripAttachments.has());
});
test('przeciąganie i usunięcie miniatury; ponowny upload używa tego samego ID',async()=>{
 const h=await harness();h.doc.getElementById('composer').listeners.drop({dataTransfer:{files:[{type:'image/jpeg',size:20,name:'x.jpg'}]},preventDefault(){}});
 assert.equal(await h.ctx.KripAttachments.upload(),'image-id');assert.equal(await h.ctx.KripAttachments.upload(),'image-id');assert.equal(h.calls.filter(([u])=>u.includes('/media/')).length,1);h.ctx.KripAttachments.clear();assert(!h.ctx.KripAttachments.has());assert.equal(h.revoked.length,1);
});
test('Kontynuuj przenosi końcówkę do edycji, bez automatycznego wysyłania',async()=>{
 const h=await harness();h.ctx.bubble('assistant','x'.repeat(3000)+'KONIEC');
 const button=walk(h.doc.getElementById('messages')).find(n=>n.tagName==='button'&&n.textContent==='Kontynuuj');assert(button);button.onclick();
 const prompt=h.doc.getElementById('prompt').value;assert(prompt.endsWith('KONIEC'));assert(prompt.length<4000);assert(prompt.startsWith('Kontynuuj'));assert(!h.calls.some(([u,o])=>u.includes('/messages')&&o.method==='POST'));
});
test('zakończenie przez limit wyświetla ostrzeżenie o niepełnej odpowiedzi',async()=>{
 const h=await harness();h.doc.getElementById('prompt').value='Pytanie';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 await h.streams[0].events['run.status']({lastEventId:'1',data:JSON.stringify({state:'completed',error_code:'output_limit'})});
 assert.match(h.doc.getElementById('notice').textContent,/niepełna/);assert.match(h.doc.getElementById('notice').textContent,/Kontynuuj/);
});
test('wybrane dokumenty trafiają do wiadomości; zdjęcie i dokumenty nie są wysyłane razem',async()=>{
 const h=await harness();h.ctx.window.KripRag={selection:()=>['pdf-id']};h.doc.getElementById('prompt').value='Pytanie do PDF';
 await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 const sends=h.calls.filter(([u,o])=>u.includes('/messages')&&o.method==='POST');assert.deepEqual(JSON.parse(sends[0][1].body).document_ids,['pdf-id']);
 const other=await harness();other.ctx.window.KripRag={selection:()=>['pdf-id']};other.paste();await other.doc.getElementById('composer').onsubmit({preventDefault(){}});
 assert(!other.calls.some(([u,o])=>u.includes('/messages')&&o.method==='POST'));assert.match(other.doc.getElementById('notice').textContent,/osobno/);
});
test('jawne uprawnienia narzędzi trafiają do żądania, a logout je czyści',async()=>{
 const h=await harness();let cleared=false;h.ctx.window.KripTools={permissions:()=>({allow_web:true,allow_github:false}),renderSources(){},clear(){cleared=true;}};
 h.doc.getElementById('prompt').value='Przeczytaj https://example.org';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 const body=JSON.parse(h.calls.find(([u,o])=>u.includes('/messages')&&o.method==='POST')[1].body);assert.equal(body.allow_web,true);assert(!body.allow_github);
 h.streams[0].events['tool.sources']({data:JSON.stringify({items:[]})});assert.match(h.doc.getElementById('notice').textContent,/nie jest potwierdzona/);
 await h.doc.getElementById('logout').onclick();assert(cleared);
});


test('kompozytor deleguje transport, pokazuje postęp i wysyła gotowe ID dopiero po kliknięciu',async()=>{
 const h=await harness();let sent=0,cleared=0;
 h.ctx.window.KripUploads={clear(){cleared++;},async send(file,options){sent++;assert.equal(file.name,'x.png');assert.equal(options.csrf(),'token');assert(options.signal);assert(options.job);options.onProgress(10,20);assert.match(h.doc.getElementById('notice').textContent,/50%/);return {id:'resumed-id'};}};
 h.paste();h.doc.getElementById('prompt').value='Pytanie';assert.equal(sent,0);
 await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 assert.equal(sent,1);assert.equal(cleared,0);const call=h.calls.find(([u,o])=>u.includes('/messages')&&o.method==='POST');assert.equal(JSON.parse(call[1].body).attachment_id,'resumed-id');
 assert(!h.calls.some(([u])=>u.includes('/files?name=')));await h.doc.getElementById('logout').onclick();assert.equal(cleared,1);
});

test('anulowanie delegowanego transportu zachowuje zakładkę wznowienia i ignoruje wynik',async()=>{
 const h=await harness();let finish,signal,cleared=0;
 h.ctx.window.KripUploads={clear(){cleared++;},send(file,options){signal=options.signal;return new Promise(r=>finish=r);}};
 h.paste();h.doc.getElementById('prompt').value='Szkic';const pending=h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 await h.doc.getElementById('cancel').onclick();assert(signal.aborted);assert.equal(cleared,0);finish({id:'late'});await pending;
 assert.equal(h.doc.getElementById('prompt').value,'Szkic');assert(!h.calls.some(([u,o])=>u.includes('/messages')&&o.method==='POST'));
});

test('błąd transportu zachowuje szkic i miniaturę do ponowienia',async()=>{
 const h=await harness();h.ctx.window.KripUploads={async send(){throw Error('Utracono połączenie. Wybierz ponownie plik.');}};
 h.paste();h.doc.getElementById('prompt').value='Szkic pytania';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});
 assert(h.ctx.KripAttachments.has());assert.equal(h.doc.getElementById('prompt').value,'Szkic pytania');assert.match(h.doc.getElementById('notice').textContent,/Utracono/);assert.equal(h.doc.getElementById('send').disabled,false);
});

test('utworzona gałąź z błędem odczytu pokazuje prawdziwy wynik zamiast sukcesu otwarcia',async()=>{
 let configured;const h=await harness({KripConversationBranch:{configure(value){configured=value;},setContext(){},setBusy(){},clear(){},attach(){}}}),original=h.ctx.fetch;
 h.ctx.fetch=(url,options)=>url.includes('/fork-cid/messages')?Promise.reject(Error('fixture offline')):original(url,options);
 h.doc.getElementById('messages').append(h.doc.createElement('article'));await configured.onBranch({id:'fork-cid',title:'Gałąź'});assert.match(h.doc.getElementById('notice').textContent,/utworzona, ale nie udało/);assert.match(h.doc.getElementById('notice').textContent,/Najnowsze/);assert.equal(h.doc.getElementById('messages').children.length,0);assert.equal(h.doc.getElementById('latest').hidden,false);assert(h.calls.some(([url])=>url.startsWith('/api/v1/conversations?')));assert(!h.calls.some(([url,options])=>url.includes('/messages')&&options.method==='POST'));
});
test('późny błąd otwarcia gałęzi nie wraca po logout',async()=>{
 let configured,reject;const h=await harness({KripConversationBranch:{configure(value){configured=value;},setContext(){},setBusy(){},clear(){},attach(){}}}),original=h.ctx.fetch;
 h.ctx.fetch=(url,options)=>url.includes('/fork-cid/messages')?new Promise((_,r)=>reject=r):original(url,options);
 const pending=configured.onBranch({id:'fork-cid',title:'Gałąź'});await h.doc.getElementById('logout').onclick();reject(Error('fixture offline'));await pending;assert.equal(h.doc.getElementById('notice').textContent,'');
});

test('kopiowanie całej wiadomości integruje user i żywy streaming; logout czyści przyciski',async()=>{
 const attached=[];let cleared=0;const h=await harness({KripMessageCopy:{configure(){},clear(){cleared++;},attach(container,options){attached.push(options.getText);}}});
 h.doc.getElementById('prompt').value='Pełna wiadomość użytkownika';await h.doc.getElementById('composer').onsubmit({preventDefault(){}});assert(attached.some(get=>get()==='Pełna wiadomość użytkownika'));const live=attached.at(-1);assert.equal(live(),'');h.streams[0].events['assistant.text.delta']({lastEventId:'1',data:JSON.stringify({text:'**Żółw** ze źródłem [W1]'})});assert.equal(live(),'**Żółw** ze źródłem [W1]');const before=cleared;await h.doc.getElementById('logout').onclick();assert.equal(cleared,before+1);
});

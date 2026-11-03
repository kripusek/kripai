const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs'),marked=require('../web/vendor/marked/marked.umd.js');
const tick=()=>new Promise(r=>setImmediate(r));

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
async function harness(){
 const doc=document(),calls=[],streams=[],saved=new Map(),revoked=[];doc.cookie='assistant_csrf=token';doc.querySelectorAll=()=>[];
 const ctx={document:doc,window:{addEventListener(){}},marked,URL:{createObjectURL:()=> 'blob:preview',revokeObjectURL:u=>revoked.push(u)},crypto:{randomUUID:()=>Math.random().toString(36)},AbortController,setTimeout,clearTimeout,setInterval(){},navigator:{clipboard:{writeText:async()=>{}}},sessionStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},KripVoice:{stop(){},configure(){},setBlocked(){},speak(){}},KripMedia:{hide(){},stop(){},configure(){},setBlocked(){}},EventSource:function(){this.events={};this.addEventListener=(k,fn)=>this.events[k]=fn;this.close=()=>{};streams.push(this);},fetch:async(url,options={})=>{
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

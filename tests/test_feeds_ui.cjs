const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function harness(api){
 const doc=document(),events={},calls=[],notices=[],ctx={document:doc,window:{KripAttachments:{has:()=>false}},URL};doc.addEventListener=(name,fn)=>events[name]=fn;
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/feeds.js'),'utf8'),ctx);
 ctx.window.KripFeeds.configure({api:async(...args)=>{calls.push(args);return api(...args);},notice:value=>notices.push(value)});events.DOMContentLoaded();
 const nodes=walk(doc.getElementById('integrationsPanel')),form=nodes.find(n=>n.tagName==='form'),input=nodes.find(n=>n.type==='url'),button=nodes.find(n=>n.type==='submit'),status=nodes.find(n=>n.attributes.role==='status');
 return {doc,ctx,api:ctx.window.KripFeeds,calls,notices,form,input,button,status,all:()=>walk(doc.getElementById('integrationsPanel')),submit:()=>form.onsubmit({preventDefault(){}})};
}
const success=()=>({available:true,url:'https://example.org/feed',title:'Kanał <script>bad</script>',count:1,truncated:true,items:[{title:'Wpis <img onerror=bad>',url:'https://example.org/a',date:'2026',excerpt:'Tylko zajawka'}]});

test('kanał czytamy dopiero po kliknięciu i pokazujemy tekstowe zajawki, nie HTML',async()=>{
 const h=harness(async()=>success());assert.equal(h.calls.length,0);h.input.value='https://example.org/feed';await h.submit();assert.equal(h.calls[0][0],'/integrations/feeds/test');assert.equal(h.calls[0][1],'POST');assert.equal(h.calls[0][2].url,h.input.value);assert.match(h.status.textContent,/zakres częściowy/);assert.match(h.status.textContent,/nie przeczytane artykuły/);assert(!h.all().some(n=>['script','img'].includes(n.tagName)));const link=h.all().find(n=>n.tagName==='a');assert.equal(link.rel,'noopener noreferrer');
});
test('dodanie pytania zachowuje szkic i tylko włącza Internet, bez wysyłania',async()=>{
 const h=harness(async()=>success());h.input.value='https://example.org/feed';h.doc.getElementById('prompt').value='Mój szkic';await h.submit();h.all().find(n=>n.textContent==='Zapytaj o artykuł').onclick();assert.equal(h.doc.getElementById('prompt').value,'Mój szkic\n\nPrzeczytaj i podsumuj https://example.org/a');assert.equal(h.doc.getElementById('allowWeb').checked,true);assert.equal(h.calls.length,1);
});
test('zdjęcie i limit szkicu nie są usuwane przy przygotowaniu pytania',async()=>{
 const h=harness(async()=>success());h.input.value='https://example.org/feed';await h.submit();const ask=h.all().find(n=>n.textContent==='Dodaj pytanie o kanał');h.ctx.window.KripAttachments.has=()=>true;h.doc.getElementById('prompt').value='Szkic';ask.onclick();assert.equal(h.doc.getElementById('prompt').value,'Szkic');assert.match(h.notices.at(-1),/Odłącz zdjęcie/);h.ctx.window.KripAttachments.has=()=>false;h.doc.getElementById('prompt').value='x'.repeat(4000);ask.onclick();assert.equal(h.doc.getElementById('prompt').value.length,4000);assert.match(h.notices.at(-1),/za długi/);
});
test('zmiana adresu i logout blokują spóźnione wyniki i stare przyciski',async()=>{
 let finish;const h=harness(()=>new Promise(r=>finish=r));h.input.value='https://example.org/feed';const pending=h.submit();h.input.value='https://example.org/new';h.input.oninput();finish(success());await pending;assert(!h.all().some(n=>n.textContent==='Dodaj pytanie o kanał'));assert.equal(h.button.disabled,false);
 h.api.configure({api:async()=>success(),notice:value=>h.notices.push(value)});await h.submit();const old=h.all().find(n=>n.textContent==='Dodaj pytanie o kanał');h.api.clear();old.onclick();assert.equal(h.doc.getElementById('prompt').value,'');assert.equal(h.input.value,'');
});
test('logout ignoruje późną odmowę, a stare finally nie odblokowuje nowego testu',async()=>{
 let finishOld,finishNew;const h=harness(()=>new Promise((r,j)=>finishOld=j));h.input.value='https://example.org/feed';const first=h.submit();h.api.clear();h.api.configure({api:()=>new Promise(r=>finishNew=r)});h.input.value='https://example.org/new';const second=h.submit();finishOld(Error('PRIVATE_SERVER_DETAIL'));await first;assert.equal(h.button.disabled,true);assert(!h.status.textContent.includes('PRIVATE'));finishNew(success());await second;assert.equal(h.button.disabled,false);
});
test('błędny adres, błąd XML, zły protokół odpowiedzi i brak sieci nie udają sukcesu',async()=>{
 const h=harness(async()=>({available:false,error:'feed_xml_denied'}));h.input.value='file:///secret';await h.submit();assert.equal(h.calls.length,0);assert.match(h.status.textContent,/HTTPS/);h.input.value='https://example.org/feed';await h.submit();assert.match(h.status.textContent,/niedozwoloną deklarację/);h.api.configure({api:async()=>({...success(),items:[{title:'T',url:'javascript:alert(1)',date:'',excerpt:''}]})});await h.submit();assert(!h.all().some(n=>n.tagName==='a'));h.api.configure({api:async()=>{throw Error('SECRET_SERVER_DETAIL');}});await h.submit();assert(!h.status.textContent.includes('SECRET'));assert.equal(h.button.disabled,false);
});
test('podwójny klik nie powiela odczytu kanału',async()=>{
 let done;const h=harness(()=>new Promise(r=>done=r));h.input.value='https://example.org/feed';const pending=h.submit();await h.submit();assert.equal(h.calls.length,1);done(success());await pending;
});

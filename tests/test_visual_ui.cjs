const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('rzeczywisty HTML zawiera wszystkie kontrolki modułu i obie drogi otwarcia',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),source=fs.readFileSync(path.join(__dirname,'../web/visual.js'),'utf8');
 const ids=Array.from(html.matchAll(/\bid="([^"]+)"/g),match=>match[1]);
 assert.equal(new Set(ids).size,ids.length,'ID w dokumencie muszą być unikalne');
 for(const match of source.matchAll(/\$\('([^']+)'\)/g))assert.ok(ids.includes(match[1]),'Brak kontrolki '+match[1]);
 assert.ok(ids.includes('menuVisual'));assert.ok(html.includes('Pamięć obrazów'));
 assert.ok(!html.slice(html.indexOf('<dialog id="visualDialog">')).includes('??'));
});
const row=(id='image',status='ready')=>({id,filename:id+'.png',pages:1,status,next_page:status==='ready'?2:1,images:status==='ready'?1:0});
function harness(items=[row()]){
 const doc=document(),calls=[],opened=[],timers=[],ctx={document:doc,window:{addEventListener(){}},confirm:()=>true,AbortController,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},encodeURIComponent};
 ctx.fetch=async(url,options)=>{calls.push([url,options]);return response(url.endsWith('/status')?{installed:true}:url.endsWith('/search')?{items:[{attachment_id:'image',filename:'image.png',page:1,distance:.2}]}:{items});};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/visual.js'),'utf8'),ctx);
 const api=ctx.window.KripVisual;api.configure({csrf:()=> 'csrf',openPage:(...args)=>opened.push(args)});
 return {ctx,doc,calls,opened,timers,api,get:id=>doc.getElementById(id)};
}
function response(data,status=200){return {ok:status<400,status,json:async()=>data};}
function boxes(h){return walk(h.get('visualList')).filter(n=>n.tagName==='input');}
function button(h,text){return walk(h.get('visualList')).find(n=>n.tagName==='button'&&n.textContent===text);}
async function select(h){h.get('visualButton').onclick();await tick();const box=boxes(h)[0];box.checked=true;box.onchange();h.get('visualQuery').value='czerwony kwadrat';h.get('visualQuery').oninput();}
const submit=h=>h.get('visualForm').onsubmit({preventDefault(){}});

test('otwarcie pamięci obrazów tylko odczytuje stan i listę, nic nie pobiera ani nie wybiera',async()=>{
 const h=harness();h.get('visualButton').onclick();await tick();
 assert.equal(h.calls.length,2);assert(h.calls.every(([,o])=>o.method==='GET'));assert.equal(boxes(h)[0].checked,false);
 assert.equal(h.get('visualSearch').disabled,true);assert.match(h.get('visualState').textContent,/CPU/);assert.equal(h.timers.length,0);
});
test('jawny wybór ograniczony do pięciu gotowych plików; niegotowy jest niedostępny',async()=>{
 const h=harness([...Array.from({length:6},(_,i)=>row('i'+i)),row('pending','paused')]);h.get('visualButton').onclick();await tick();
 for(const box of boxes(h).slice(0,6)){box.checked=true;box.onchange();}
 assert.equal(boxes(h)[5].checked,false);assert.equal(boxes(h)[6].disabled,true);assert.match(h.get('visualSelected').textContent,/5 \/ 5/);assert.match(h.get('visualNotice').textContent,/najwyżej 5/);
});
test('wyszukiwanie ma CSRF i ograniczenie do wybranych plików, wynik otwiera stronę bez rozmowy/VLM',async()=>{
 const h=harness();await select(h);assert.equal(h.get('visualSearch').disabled,false);await submit(h);
 const [url,options]=h.calls.find(([u])=>u.endsWith('/search'));assert.equal(url,'/api/v1/visual/search');assert.equal(options.method,'POST');assert.equal(options.headers['X-CSRF-Token'],'csrf');
 assert.deepEqual(JSON.parse(options.body),{query:'czerwony kwadrat',attachment_ids:['image']});
 const open=walk(h.get('visualResults')).find(n=>n.tagName==='button');open.onclick();assert.deepEqual(h.opened,[['image',1]]);assert.equal(h.get('visualDialog').open,false);
 assert(!h.calls.some(([u])=>/messages|analyze|prepare/.test(u)));
});
test('indeksowanie to jawny POST i po odpowiedzi odblokowuje listę; nie zaznacza pliku',async()=>{
 const h=harness([row('image',null)]);h.get('visualButton').onclick();await tick();await button(h,'Indeksuj').onclick();
 const [,options]=h.calls.find(([u])=>u.endsWith('/index'));assert.equal(options.method,'POST');assert.equal(options.headers['X-CSRF-Token'],'csrf');assert.deepEqual(JSON.parse(options.body),{});
 assert.equal(button(h,'Indeksuj').disabled,false);assert.equal(boxes(h)[0].checked,false);assert.equal(h.get('visualRefresh').disabled,false);
});
test('pobieranie kodera jest opcjonalne i wymaga przycisku; błąd pozwala ponowić',async()=>{
 const h=harness();h.ctx.fetch=async(url,options)=>{h.calls.push([url,options]);if(url.endsWith('/prepare'))return response({error:{code:'visual_download_denied'}},503);return response(url.endsWith('/status')?{installed:false}:{items:[row('image',null)]});};
 h.get('visualButton').onclick();await tick();assert.equal(h.get('visualPrepare').disabled,false);assert.equal(button(h,'Indeksuj').disabled,true);
 await h.get('visualPrepare').onclick();assert.match(h.get('visualNotice').textContent,/zweryfikować/);assert.equal(h.get('visualPrepare').disabled,false);assert.equal(h.calls.filter(([u])=>u.endsWith('/prepare')).length,1);
});
test('wylogowanie ignoruje opóźnioną listę i wynik oraz usuwa prywatny opis',async()=>{
 const h=harness();await select(h);let release;h.ctx.fetch=()=>new Promise(resolve=>release=resolve);const pending=submit(h);h.api.hide();
 release(response({items:[{attachment_id:'image',filename:'private.png',page:1}]}));await pending;
 assert.equal(h.get('visualResults').children.length,0);assert.equal(h.get('visualQuery').value,'');assert.equal(h.get('visualList').children.length,0);assert.equal(h.get('visualDialog').open,false);
 let listRelease,statusRelease;h.ctx.fetch=url=>new Promise(resolve=>{if(url.endsWith('/status'))statusRelease=resolve;else listRelease=resolve;});h.get('visualButton').onclick();h.api.hide();
 statusRelease(response({installed:true}));listRelease(response({items:[row('private')]}));await tick();assert.equal(h.get('visualList').children.length,0);assert.equal(h.get('visualState').textContent,'');
});
test('stare wyszukiwanie nie nadpisuje nowej sesji ani blokady jej kontrolek',async()=>{
 const h=harness();await select(h);let release;const original=h.ctx.fetch;h.ctx.fetch=()=>new Promise(resolve=>release=resolve);const pending=submit(h);h.api.hide();h.ctx.fetch=original;await select(h);
 release(response({items:[{attachment_id:'image',filename:'old.png',page:1}]}));await pending;
 assert.equal(h.get('visualResults').children.length,0);assert.equal(h.get('visualSearch').disabled,false);assert.equal(h.get('visualQuery').value,'czerwony kwadrat');
});
test('Gaming blokuje wyszukiwanie i indeksowanie, zachowuje przycisk wstrzymania',async()=>{
 const h=harness([row('image','indexing')]);h.get('visualButton').onclick();await tick();h.api.setBlocked(true);await tick();
 assert.equal(h.get('visualSearch').disabled,true);assert.equal(h.get('visualPrepare').disabled,true);assert.equal(button(h,'Wstrzymaj').disabled,false);await button(h,'Wstrzymaj').onclick();
 assert(h.calls.some(([u,o])=>u.endsWith('/pause')&&o.method==='POST'));assert(h.timers.length>0);
});
test('odpytywanie postępu nie sprawdza plików kodera ponownie; ręczne odświeżenie sprawdza',async()=>{
 const h=harness([row('image','indexing')]);h.get('visualButton').onclick();await tick();
 assert.equal(h.calls.filter(([u])=>u.endsWith('/status')).length,1);h.timers.at(-1)();await tick();
 assert.equal(h.calls.filter(([u])=>u.endsWith('/status')).length,1);assert.equal(h.calls.filter(([u])=>u.endsWith('/documents')).length,2);
 await h.get('visualRefresh').onclick();assert.equal(h.calls.filter(([u])=>u.endsWith('/status')).length,2);
});
test('nazwy wyników są tekstem; obcy plik i nieprawidłowa strona nie mają przycisku',async()=>{
 const h=harness();await select(h);h.ctx.fetch=async()=>response({items:[{attachment_id:'image',filename:'<script>bad()</script>',page:1},{attachment_id:'other',filename:'other',page:1},{attachment_id:'image',filename:'bad',page:51}]});await submit(h);
 const nodes=walk(h.get('visualResults'));assert.equal(nodes.filter(n=>n.tagName==='button').length,1);assert(!nodes.some(n=>n.tagName==='script'));assert.match(h.get('visualResults').textContent,/<script>/);
 const open=nodes.find(n=>n.tagName==='button');h.api.hide();open.onclick();assert.equal(h.opened.length,0);
});
test('błąd szukania odblokowuje panel, zmiana opisu i wyczyszczenie wyboru usuwają wyniki',async()=>{
 const h=harness();await select(h);await submit(h);assert.equal(h.get('visualResults').children.length,1);h.get('visualQuery').oninput();assert.equal(h.get('visualResults').children.length,0);
 const original=h.ctx.fetch;h.ctx.fetch=async()=>response({error:{code:'visual_query_too_large'}},422);await submit(h);assert.match(h.get('visualNotice').textContent,/Skróć/);assert.equal(h.get('visualSearch').disabled,false);
 h.ctx.fetch=original;h.get('visualClear').onclick();await tick();assert.equal(boxes(h)[0].checked,false);assert.equal(h.get('visualSearch').disabled,true);
});

const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,Node,walk}=require('./dom.cjs');
test('propozycja jest tekstowym diffem; publikacja następuje tylko po kliknięciu',async()=>{
 const doc=document(),bar=new Node('div'),events={},calls=[];let published=false;
 doc.addEventListener=(name,fn)=>events[name]=fn;doc.querySelector=()=>bar;
 const ctx={document:doc,window:{},URLSearchParams,api:async(url,method)=>{
  calls.push([url,method]);
  if(method==='POST'){published=true;return {url:'https://github.com/owner/repo/pull/1'};}
  return {items:[{id:'draft-id',state:published?'published':'prepared',proposal:{title:'<img onerror=bad>',repository:'owner/repo',files:[{path:'README.md',diff:'-old\n+<script>bad</script>'}]}}]};
 }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/integrations.js'),'utf8'),ctx);events.DOMContentLoaded();
 const panel=doc.getElementById('integrationsPanel');
 const refresh=walk(panel).find(n=>n.textContent==='Pokaż propozycje zmian');await refresh.onclick();
 assert.equal(calls.filter(([,m])=>m==='POST').length,0);
 assert(!walk(panel).some(n=>['img','script'].includes(n.tagName)));
 const publish=walk(panel).find(n=>n.textContent==='Utwórz gałąź i PR');await publish.onclick();
 assert.equal(calls.filter(([,m])=>m==='POST').length,1);
 assert.equal(calls.find(([,m])=>m==='POST')[0],'/integrations/github/drafts/draft-id/publish');
 assert(walk(panel).find(n=>n.textContent==='Utwórz gałąź i PR').disabled);
});

test('token kreatora tylko w lokalnym POST, czyszczony po błędzie i zamknięciu',async()=>{
 const doc=document(),events={},calls=[];
 doc.addEventListener=(name,fn)=>events[name]=fn;
 const ctx={document:doc,window:{},URLSearchParams,csrf:()=> 'csrf-fixture',fetch:async(url,options)=>{calls.push([url,options]);return {ok:false,status:409,json:async()=>({error:{code:'tool_remote_denied'}})};}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/integrations.js'),'utf8'),ctx);events.DOMContentLoaded();
 const panel=doc.getElementById('integrationsPanel'),token=walk(panel).find(n=>n.type==='password'),repo=walk(panel).find(n=>n.placeholder?.startsWith('owner/repo'));
 token.value='fixture-only';repo.value='owner/repo';await walk(panel).find(n=>n.tagName==='form').onsubmit({preventDefault(){}});
 assert.equal(token.value,'');assert(!calls[0][0].includes('fixture-only'));assert.equal(JSON.parse(calls[0][1].body).token,'fixture-only');assert.equal(calls[0][1].headers['X-CSRF-Token'],'csrf-fixture');
 token.value='again';doc.getElementById('integrationsDialog').listeners.close();assert.equal(token.value,'');
});

test('niepewna publikacja daje tylko sprawdzenie wyniku zamiast ponowienia zapisu',async()=>{
 const doc=document(),events={},calls=[];doc.addEventListener=(name,fn)=>events[name]=fn;
 const ctx={document:doc,window:{},URLSearchParams,api:async(url,method)=>{
  calls.push([url,method]);if(method==='POST')return {state:'branch_only',url:'https://github.com/owner/repo/tree/kripai/id'};
  return {items:[{id:'id',state:'outcome_unknown',proposal:{title:'Propozycja',repository:'owner/repo',files:[]}}]};
 }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/integrations.js'),'utf8'),ctx);events.DOMContentLoaded();
 const panel=doc.getElementById('integrationsPanel');await walk(panel).find(n=>n.textContent==='Pokaż propozycje zmian').onclick();
 assert(walk(panel).find(n=>n.textContent==='Utwórz gałąź i PR').disabled);
 await walk(panel).find(n=>n.textContent==='Sprawdź wynik w GitHub').onclick();
 assert.deepEqual(calls.filter(([,m])=>m==='POST').map(([u])=>u),['/integrations/github/drafts/id/reconcile']);
});

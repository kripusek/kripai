const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,Node,walk}=require('./dom.cjs');
const tick=()=>new Promise(r=>setImmediate(r));
function harness(){
 const doc=document(),calls=[],ctx={document:doc,window:{addEventListener(){}},confirm:()=>true,setTimeout:()=>1,clearTimeout(){},encodeURIComponent,fetch:async(url,options)=>{calls.push([url,options]);return {ok:true,status:200,json:async()=>({items:[{id:'pdf',filename:'dokument.pdf',pages:2,status:'ready',next_page:3,chunks:2}]})};}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/rag.js'),'utf8'),ctx);const api=ctx.window.KripRag;api.configure({csrf:()=> 'csrf'});
 return {ctx,doc,calls,api,get:id=>doc.getElementById(id)};
}
test('wybór dokumentu jest jawny; otwarcie nie wysyła wiadomości ani nie indeksuje',async()=>{
 const h=harness();h.get('ragButton').onclick();await tick();
 const check=walk(h.get('ragList')).find(n=>n.tagName==='input');check.checked=true;check.onchange();
 assert.deepEqual(Array.from(h.api.selection()),['pdf']);assert.match(h.get('ragSelected').textContent,/1/);
 assert.equal(h.calls.length,1);assert.equal(h.calls[0][1].method,'GET');
 h.get('ragClear').onclick();assert.deepEqual(Array.from(h.api.selection()),[]);
});
test('wylogowanie usuwa wybór i ignoruje opóźnioną listę',async()=>{
 const h=harness();let resolve;h.ctx.fetch=()=>new Promise(r=>resolve=r);h.get('ragButton').onclick();h.api.hide();
 resolve({ok:true,status:200,json:async()=>({items:[{id:'old',filename:'prywatny.pdf',status:'ready'}]})});await tick();
 assert.equal(h.get('ragList').children.length,0);assert.deepEqual(Array.from(h.api.selection()),[]);
});
test('kolejka ma POST z CSRF; gotowy indeks nie jest wybierany automatycznie',async()=>{
 const h=harness();h.ctx.fetch=async(url,options)=>{h.calls.push([url,options]);return {ok:true,status:200,json:async()=>({items:[{id:'pdf',filename:'scan.pdf',pages:2,status:null}]})};};
 h.get('ragButton').onclick();await tick();const section=h.get('ragList').children[0];
 assert.equal(walk(section).find(n=>n.tagName==='input').disabled,true);
 await walk(section).find(n=>n.tagName==='button'&&n.textContent==='Indeksuj').onclick();
 const [,opts]=h.calls.find(([u,o])=>o.method==='POST');assert.equal(opts.headers['X-CSRF-Token'],'csrf');assert.equal(opts.body,'{}');assert.equal(h.api.selection().length,0);
});
test('źródła i złośliwe nazwy/wycinki są tekstem, link prowadzi do lokalnego pliku',()=>{
 const h=harness(),box=new Node('article'),text=new Node('div');box.append(text);
 h.api.renderSources(text,[{ordinal:1,filename:'<img onerror=bad()>',page:2,excerpt:'<script>bad()</script>',attachment_id:'id'}]);
 const nodes=walk(box);assert(!nodes.some(n=>['img','script'].includes(n.tagName)));assert.equal(nodes.find(n=>n.tagName==='a').href,'/api/v1/files/id/download');assert.match(box.textContent,/<script>/);
 h.api.renderSources(text,[]);assert.equal(walk(box).filter(n=>n.tagName==='details').length,0);
});
test('błąd pobierania indeksu pokazuje opis i umożliwia ponowienie',async()=>{
 const h=harness();h.ctx.fetch=async()=>({ok:false,status:503,json:async()=>({error:{code:'rag_not_installed'}})});
 h.get('ragButton').onclick();await tick();assert.match(h.get('ragNotice').textContent,/START.cmd/);
});

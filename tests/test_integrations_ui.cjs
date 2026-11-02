const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,Node,walk}=require('./dom.cjs');
test('propozycja jest tekstowym diffem; publikacja następuje tylko po kliknięciu',async()=>{
 const doc=document(),bar=new Node('div'),events={},calls=[];let published=false;
 doc.addEventListener=(name,fn)=>events[name]=fn;doc.querySelector=()=>bar;
 const ctx={document:doc,api:async(url,method)=>{
  calls.push([url,method]);
  if(method==='POST'){published=true;return {url:'https://github.com/owner/repo/pull/1'};}
  return {items:[{id:'draft-id',state:published?'published':'prepared',proposal:{title:'<img onerror=bad>',repository:'owner/repo',files:[{path:'README.md',diff:'-old\n+<script>bad</script>'}]}}]};
 }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/integrations.js'),'utf8'),ctx);events.DOMContentLoaded();
 const refresh=walk(bar).find(n=>n.textContent==='Pokaż propozycje zmian');await refresh.onclick();
 assert.equal(calls.filter(([,m])=>m==='POST').length,0);
 assert(!walk(bar).some(n=>['img','script'].includes(n.tagName)));
 const publish=walk(bar).find(n=>n.textContent==='Utwórz gałąź i PR');await publish.onclick();
 assert.equal(calls.filter(([,m])=>m==='POST').length,1);
 assert.equal(calls.find(([,m])=>m==='POST')[0],'/integrations/github/drafts/draft-id/publish');
 assert(walk(bar).find(n=>n.textContent==='Utwórz gałąź i PR').disabled);
});

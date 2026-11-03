const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function harness(api){const doc=document(),events={};doc.addEventListener=(name,fn)=>events[name]=fn;const ctx={document:doc,window:{},api};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/mcp-files.js'),'utf8'),ctx);events.DOMContentLoaded();const panel=doc.getElementById('integrationsPanel');return {doc,api:ctx.window.KripMcpFiles,panel,nodes:walk(panel)};}
test('odświeżenie nie instaluje serwera i bezpiecznie wyświetla prywatną konfigurację',async()=>{
 const calls=[],h=harness(async(...args)=>{calls.push(args);return {configured:true,available:true,root:'C:/Notes',label:'<img onerror=x>'};});await h.api.refresh();
 assert.equal(calls.length,1);assert.equal(calls[0][0],'/integrations/mcp-files/config');assert.equal(calls[0][1],'GET');assert.match(h.panel.textContent,/<img onerror=x>/);assert(!h.nodes.some(n=>n.tagName==='img'));
});
test('wybór folderu i test używają wyłącznie stałych lokalnych tras',async()=>{
 const calls=[],h=harness(async(p,m,b)=>{calls.push([p,m,b]);return p.endsWith('/test')?{available:true,documents:2,omitted_entries:1}:{available:true,root:'C:/Notes',label:'Notes'};});
 const inputs=h.nodes.filter(n=>n.tagName==='input');inputs[0].value='C:/Notes';inputs[1].value='Notes';await h.nodes.find(n=>n.tagName==='form').onsubmit({preventDefault(){}});
 assert.equal(calls[0][0],'/integrations/mcp-files/config');assert.equal(calls[0][1],'POST');assert.equal(calls[0][2].root,'C:/Notes');
 await h.nodes.find(n=>n.textContent==='Test odczytu').onclick();assert.match(h.panel.textContent,/dokumenty w katalogu: 2/);
});
test('logout usuwa ścieżkę i odrzuca spóźnioną konfigurację',async()=>{
 let resolve;const pending=new Promise(r=>resolve=r),h=harness(()=>pending);const done=h.api.refresh();h.api.clear();resolve({root:'C:/Private',label:'Private',available:true});await done;
 assert(h.nodes.filter(n=>n.tagName==='input').every(n=>n.value===''));assert(!h.panel.textContent.includes('Wybrano: Private'));
});
test('przygotowanie wymaga kliknięcia, awaria ma czytelny komunikat',async()=>{
 const calls=[],h=harness(async(p,m)=>{calls.push([p,m]);const e=Error();e.code='mcp_files_install_failed';throw e;});
 assert.equal(calls.length,0);await h.nodes.find(n=>n.textContent==='Przygotuj serwer MCP').onclick();assert.equal(calls[0][1],'POST');assert.match(h.panel.textContent,/Node.js 24/);
});

const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function harness(api){const doc=document(),events={};doc.addEventListener=(name,fn)=>events[name]=fn;const ctx={document:doc,window:{},api,URLSearchParams};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/mcp-files.js'),'utf8'),ctx);events.DOMContentLoaded();const panel=doc.getElementById('integrationsPanel');return {doc,window:ctx.window,api:ctx.window.KripMcpFiles,panel,nodes:walk(panel)};}
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

const root='12345678-1234-1234-1234-123456789abc';
function configuration(id=root){return {configured:true,available:true,root_id:id,root:'C:/Notes',label:'Notes'};}
const button=(h,text)=>walk(h.panel).find(n=>n.tagName==='button'&&n.textContent===text);
test('przeglądanie katalogów i wybór polskiej nazwy zachowuje szkic i nie wysyła wiadomości',async()=>{
 const calls=[],h=harness(async(p,m)=>{calls.push([p,m]);return p.endsWith('/config')?configuration():p.includes('path=docs')?{paths:['docs/zażółć gęślą.txt'],text:'[FILE] docs/zażółć gęślą.txt',omitted_entries:1}:{paths:[],text:'[DIR] docs',omitted_entries:0};});
 await h.api.refresh();await button(h,'Przeglądaj dokumenty').onclick();await button(h,'Otwórz katalog: docs').onclick();
 h.doc.getElementById('prompt').value='Moje pytanie';h.doc.getElementById('integrationsDialog').open=true;button(h,'Zapytaj o dokument').onclick();
 assert.match(h.doc.getElementById('prompt').value,/^Moje pytanie\n\nDokument MCP/);assert.match(h.doc.getElementById('prompt').value,/docs\/zażółć gęślą.txt/);assert.equal(h.doc.getElementById('allowMcp').checked,true);assert.equal(h.doc.getElementById('integrationsDialog').open,false);
 assert(calls.every(([p,m])=>m==='GET'&&!p.includes('messages')));assert(calls.some(([p])=>p.includes('root='+root+'&path=docs')));
 const source=walk(h.panel).find(n=>n.tagName==='a');assert.match(source.href,/document\?root=/);assert.match(source.href,/path=docs%2Fza/);assert.equal(source.rel,'noopener noreferrer');
});
test('brak serwera i błąd odczytu nie udają pustego katalogu',async()=>{
 const h=harness(async p=>{if(p.endsWith('/config'))return configuration();throw Error('Serwer niedostępny');});await h.api.refresh();await button(h,'Przeglądaj dokumenty').onclick();assert.match(h.panel.textContent,/Serwer niedostępny/);assert(!h.panel.textContent.includes('Dokumenty w tym katalogu: 0'));
});
test('stara odpowiedź katalogu i stary przycisk nie przywracają danych po logout lub zmianie root',async()=>{
 let resolve,selected=root,pending=false;const h=harness(async p=>p.endsWith('/config')?configuration(selected):pending?new Promise(r=>resolve=r):{paths:['memo.md'],text:'[FILE] memo.md'});
 await h.api.refresh();await button(h,'Przeglądaj dokumenty').onclick();const old=button(h,'Zapytaj o dokument');selected='87654321-1234-1234-1234-123456789abc';await h.api.refresh();old.onclick();assert.equal(h.doc.getElementById('prompt').value,'');assert(!h.panel.textContent.includes('memo.md'));
 pending=true;const done=button(h,'Przeglądaj dokumenty').onclick();h.api.clear();resolve({paths:['private.md'],text:'[FILE] private.md'});await done;assert(!h.panel.textContent.includes('private.md'));assert.equal(button(h,'Przeglądaj dokumenty').disabled,true);
});
test('nazwy są tekstem, niedozwolone ścieżki pomijane, a zdjęcie nie jest usuwane',async()=>{
 const h=harness(async p=>p.endsWith('/config')?configuration():{paths:['<img>.md','../secret.md','C:/secret.md','.hidden.md'],text:'[FILE] <img>.md\n[DIR] ../secret'});await h.api.refresh();await button(h,'Przeglądaj dokumenty').onclick();assert(!walk(h.panel).some(n=>n.tagName==='img'));assert.equal(walk(h.panel).filter(n=>n.tagName==='a').length,1);
 h.window.KripAttachments={has:()=>true};button(h,'Zapytaj o dokument').onclick();assert.equal(h.doc.getElementById('prompt').value,'');assert.equal(h.doc.getElementById('allowMcp').checked,undefined);assert.match(h.panel.textContent,/Usuń zdjęcie/);
});
test('wyszukiwanie nazwy jest lokalnym GET, pokazuje limit i pozwala wybrać wynik',async()=>{
 const calls=[],h=harness(async(p,m)=>{calls.push([p,m]);return p.endsWith('/config')?configuration():{paths:['docs/Raport 2026.txt'],text:'docs/Raport 2026.txt',matched_documents:27,truncated:true,omitted_entries:2};});
 await h.api.refresh();h.nodes.filter(n=>n.tagName==='input')[2].value='raport 2026';await h.nodes.filter(n=>n.tagName==='form')[1].onsubmit({preventDefault(){}});
 assert(calls[1][0].includes('/search?root='+root+'&query=raport+2026'));assert(calls.every(([,method])=>method==='GET'));assert.match(h.panel.textContent,/Pasujące dokumenty: 27/);assert.match(h.panel.textContent,/pierwsze 20/);
 button(h,'Zapytaj o dokument').onclick();assert.match(h.doc.getElementById('prompt').value,/Raport 2026.txt/);h.api.clear();assert.equal(h.nodes.filter(n=>n.tagName==='input')[2].value,'');
});
test('spóźnione wyszukiwanie nie zastępuje nowszego katalogu',async()=>{
 let resolve;const h=harness(async p=>p.endsWith('/config')?configuration():p.includes('/search?')?new Promise(r=>resolve=r):{paths:[],text:'Brak dokumentów'});
 await h.api.refresh();h.nodes.filter(n=>n.tagName==='input')[2].value='raport';const pending=h.nodes.filter(n=>n.tagName==='form')[1].onsubmit({preventDefault(){}});await button(h,'Przeglądaj dokumenty').onclick();resolve({paths:['stary.md'],text:'stary.md',matched_documents:1});await pending;assert(!h.panel.textContent.includes('stary.md'));assert(h.panel.textContent.includes('Katalog: /'));
});

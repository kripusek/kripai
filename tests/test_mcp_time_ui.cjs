const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function success(zone='Europe/Warsaw'){const snapshot={action:'now',captured_at:'2026-11-03T14:02:29+00:00',result:{timezone:zone,datetime:'2026-11-03T15:02:28'+(zone==='UTC'?'+00:00':'+01:00'),day_of_week:'Tuesday',is_dst:false}};return {available:true,content_kind:'time_snapshot',url:'/api/v1/integrations/mcp-time/result?data='+Buffer.from(JSON.stringify(snapshot)).toString('base64url'),text:JSON.stringify(snapshot)};}
function harness(handler){
 const doc=document(),events=[],calls=[],notices=[],ctx={document:doc,window:{KripAttachments:{has:()=>false}}};doc.addEventListener=(name,fn)=>{if(name==='DOMContentLoaded')events.push(fn);};vm.createContext(ctx);
 for(const name of ['integration-groups.js','mcp-time.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/'+name),'utf8'),ctx);
 const api=ctx.window.KripMcpTime;api.configure({api:async(...args)=>{calls.push(args);return handler?handler(...args):success(args[2]?.timezone);},notice:text=>notices.push(text)});for(const fn of events)fn();
 const all=()=>walk(doc.getElementById('integrationsPanel')),zone=all().find(n=>n.tagName==='input'),form=all().find(n=>n.tagName==='form'),prepare=all().find(n=>n.textContent==='Przygotuj serwer czasu'),test=all().find(n=>n.textContent==='Test odczytu czasu'),ask=all().find(n=>n.textContent==='Dodaj pytanie o czas'),status=all().find(n=>n.attributes.role==='status'),output=all().find(n=>n.className==='mcp-time-output'),link=all().find(n=>n.tagName==='a');
 return {doc,ctx,api,calls,notices,zone,form,prepare,test,ask,status,output,link,ready:()=>api.update({available:true},api.getEpoch()),read:()=>form.onsubmit({preventDefault(){}})};
}
test('panel nie uruchamia serwera sam; po jawnej próbie pokazuje zapisany wynik',async()=>{
 const h=harness();assert.equal(h.calls.length,0);assert(h.test.disabled);h.ready();assert(h.prepare.disabled);h.zone.value='UTC';await h.read();assert.equal(h.calls[0][0],'/integrations/mcp-time/test');assert.equal(h.calls[0][2].timezone,'UTC');assert.match(h.output.textContent,/UTC · 03.11.2026\n15:02:28 \(UTC\+00:00\)/);assert(!h.output.textContent.includes('captured_at'));assert.equal(h.link.href,success('UTC').url);assert.equal(h.link.rel,'noopener noreferrer');assert.equal(h.link.hidden,false);assert.match(h.status.textContent,/zapis chwili/);
});
test('przygotowanie ma osobny przycisk i nie udaje zaliczonego odczytu',async()=>{
 const h=harness(async()=>({prepared:true}));await h.prepare.onclick();assert.equal(h.calls[0][0],'/integrations/mcp-time/prepare');assert.equal(h.calls[0][2],undefined);assert.equal(h.test.disabled,false);assert.equal(h.link.hidden,true);assert.match(h.status.textContent,/Wykonaj test/);assert(!h.status.textContent.includes('zakończony'));
});
test('pytanie zachowuje dokładny szkic i włącza MCP bez wysyłania',()=>{
 const h=harness();h.ready();h.doc.getElementById('prompt').value='  Kod\n    wcięcie\n';h.ask.onclick();assert(h.doc.getElementById('prompt').value.startsWith('  Kod\n    wcięcie\n\n\nOdczytaj'));assert.equal(h.doc.getElementById('allowMcp').checked,true);assert.equal(h.calls.length,0);
});
test('zdjęcie i limit szkicu są chronione',()=>{
 const h=harness();h.ready();h.doc.getElementById('prompt').value='Szkic';h.ctx.window.KripAttachments.has=()=>true;h.ask.onclick();assert.equal(h.doc.getElementById('prompt').value,'Szkic');assert.match(h.notices.at(-1),/Odłącz zdjęcie/);h.ctx.window.KripAttachments.has=()=>false;h.doc.getElementById('prompt').value='x'.repeat(4000);h.ask.onclick();assert.equal(h.doc.getElementById('prompt').value.length,4000);assert.match(h.notices.at(-1),/za długi/);
});
test('zła strefa nie wysyła żądania, błąd dostawcy jest czytelny bez surowych danych',async()=>{
 const h=harness(async()=>({available:false,error:'mcp_time_arguments_invalid'}));h.ready();h.zone.value='../secret';await h.read();assert.equal(h.calls.length,0);assert.match(h.status.textContent,/IANA/);h.zone.value='Unknown/Zone';await h.read();assert.match(h.status.textContent,/Nieprawidłowa strefa/);assert.equal(h.output.textContent,'');assert.equal(h.link.hidden,true);assert.equal(h.test.disabled,false);
});
test('błędny link i HTML odpowiedzi nie tworzą aktywnego skryptu ani obcego źródła',async()=>{
 const h=harness(async()=>({...success(),text:'<script>BAD</script>'}));h.ready();await h.read();assert.equal(h.output.textContent,'');assert(!walk(h.output).some(n=>n.tagName==='script'));h.api.configure({api:async()=>({...success(),url:'javascript:alert(1)'})});await h.read();assert.equal(h.link.hidden,true);assert.equal(h.output.textContent,'');assert.match(h.status.textContent,/nieprawidłowe dane/);
});
test('wynik odświeżenia rozpoczętego przed testem nie cofa gotowego serwera',async()=>{
 let done;const h=harness(()=>new Promise(r=>done=r));h.ready();const old=h.api.getEpoch(),pending=h.read();assert(h.zone.disabled);done(success());await pending;h.api.update({available:false},old);assert.equal(h.test.disabled,false);assert.equal(h.prepare.disabled,true);assert.equal(h.zone.disabled,false);
});
test('logout ignoruje późny wynik i stary finally nie zmienia nowej operacji',async()=>{
 let reject,finish;const h=harness(()=>new Promise((_,r)=>reject=r));h.ready();const old=h.read();h.api.clear();h.api.configure({api:()=>new Promise(r=>finish=r)});const current=h.prepare.onclick();reject(Error('PRIVATE_SDK_DETAIL'));await old;assert(h.prepare.disabled);assert(!h.status.textContent.includes('PRIVATE'));finish({prepared:true});await current;assert.equal(h.test.disabled,false);assert.equal(h.output.textContent,'');
});

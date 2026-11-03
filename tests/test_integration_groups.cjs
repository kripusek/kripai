const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
const tick=()=>new Promise(r=>setImmediate(r));
function load(ctx,name){vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/'+name),'utf8'),ctx);}
function harness(){const doc=document(),ctx={document:doc,window:{},fetch(){throw Error('No automatic network');}};vm.createContext(ctx);load(ctx,'integration-groups.js');return {doc,ctx,api:ctx.window.KripIntegrationGroups};}
test('cztery zamknięte grupy mają stałą kolejność niezależną od montowania',()=>{
 const h=harness(),parent=h.doc.getElementById('integrationsPanel');for(const id of ['feeds','mcp_files','github','mcp'])h.api.mount({id,title:id,parent});assert.deepEqual(parent.children.map(n=>n.attributes['data-integration']),['github','mcp','mcp_files','feeds']);assert(parent.children.every(n=>n.tagName==='details'&&n.open===false));const group=h.api.mount({id:'github',title:'Duplicate',parent});assert.equal(parent.children.length,4);assert.equal(group.body.tagName,'div');
});
test('status jest zwykłym tekstem, a błędny kolor nie tworzy CSS lub HTML',()=>{
 const h=harness(),group=h.api.mount({id:'github',title:'<img>',parent:h.doc.getElementById('integrationsPanel')});group.setStatus('script','<script>BAD</script>');const status=walk(group.element).find(n=>n.className==='integration-status');assert.equal(status.attributes['data-state'],'neutral');assert.equal(status.textContent,'<script>BAD</script>');assert(!walk(group.element).some(n=>['script','img'].includes(n.tagName)));group.setStatus('ok','x'.repeat(300));assert.equal(status.textContent.length,80);
});
test('clear zamyka sekcje i unieważnia widoczny stan bez przebudowania formularzy',()=>{
 const h=harness(),group=h.api.mount({id:'feeds',title:'RSS',parent:h.doc.getElementById('integrationsPanel')}),input=h.doc.createElement('input');group.body.append(input);group.element.open=true;group.setStatus('ok','5 wpisów');h.api.clear();assert.equal(group.element.open,false);assert.equal(walk(group.element).find(n=>n.className==='integration-status').textContent,'Nie sprawdzono');assert.equal(group.body.children[0],input);
});
async function providers(options={}){
 const h=harness(),events=[],calls=[];
 h.doc.addEventListener=(name,fn)=>{if(name==='DOMContentLoaded')events.push(fn);};
 h.ctx.URL=URL;h.ctx.URLSearchParams=URLSearchParams;h.ctx.csrf=()=> 'fixture';
 h.ctx.api=async(url,method)=>{
  calls.push([url,method]);if(options.api)return options.api(url,method);
  if(url==='/integrations')return {items:[{name:'github',configured:false},{name:'mcp',available:true}]};
  if(url.endsWith('/config'))return {configured:false,available:true};
  return {available:false,error:'mcp_timeout'};
 };
 load(h.ctx,'feeds.js');h.ctx.window.KripFeeds.configure({api:h.ctx.api,notice(){}});load(h.ctx,'integrations.js');load(h.ctx,'mcp-files.js');for(const fn of events)fn();
 await h.ctx.window.KripIntegrations.refresh();await tick();
 const group=id=>h.doc.getElementById('integrationsPanel').children.find(n=>n.attributes['data-integration']===id),badge=id=>walk(group(id)).find(n=>n.className==='integration-status');
 return {...h,calls,group,badge};
}
test('dostawcy montują prawdziwe formularze w grupach, odświeżenie nie wykonuje testów',async()=>{
 const h=await providers();assert.equal(h.doc.getElementById('integrationsPanel').children.length,4);assert.match(h.badge('github').textContent,/bez konta/);assert.equal(h.badge('mcp').textContent,'Gotowy do testu');assert.equal(h.badge('mcp_files').textContent,'Wybierz folder');assert.equal(h.badge('feeds').textContent,'Bez konta');assert(!h.calls.some(([u,m])=>m==='POST'||u.endsWith('/test')));assert(walk(h.group('github')).some(n=>n.type==='password'));assert(walk(h.group('feeds')).some(n=>n.type==='url'));
});
test('błąd konfiguracji GitHuba jest widoczny zamiast rzekomego publicznego połączenia',async()=>{
 const h=await providers({api:async url=>url==='/integrations'?{items:[{name:'github',error:'integration_configuration_invalid'},{name:'mcp',available:true}]}:{configured:false,available:true}});assert.equal(h.badge('github').attributes['data-state'],'error');assert.equal(h.badge('github').textContent,'Błąd konfiguracji');assert(walk(h.group('github')).some(n=>n.textContent==='Nie można odczytać lokalnej konfiguracji GitHuba. Sprawdź ustawienia połączenia.'));assert.equal(walk(h.group('github')).find(n=>n.textContent==='Odłącz lokalnie').disabled,false);
});
test('nieudany test MCP ma błąd w zamkniętym nagłówku, bez zielonego sukcesu',async()=>{
 const h=await providers();await walk(h.group('mcp')).find(n=>n.textContent==='Test połączenia MCP').onclick();assert.equal(h.badge('mcp').attributes['data-state'],'error');assert.equal(h.badge('mcp').textContent,'Błąd testu');await walk(h.group('mcp_files')).find(n=>n.textContent==='Test odczytu').onclick();assert.equal(h.badge('mcp_files').attributes['data-state'],'error');assert.equal(h.badge('mcp_files').textContent,'Błąd operacji');
});
test('późny błąd odświeżenia po logout nie przywraca nagłówka ani danych',async()=>{
 const h=await providers();let reject;const original=h.ctx.api;h.ctx.api=(url,method)=>url==='/integrations'?new Promise((_,r)=>reject=r):original(url,method);const pending=h.ctx.window.KripIntegrations.refresh();h.ctx.window.KripIntegrations.clear();h.ctx.window.KripMcpFiles.clear();h.ctx.window.KripFeeds.clear();h.api.clear();reject(Error('PRIVATE_OLD_DETAIL'));await pending;await tick();assert.equal(h.badge('github').textContent,'Nie sprawdzono');assert(!h.doc.getElementById('integrationsPanel').textContent.includes('PRIVATE_OLD_DETAIL'));
});
test('stary błąd łączenia GitHuba nie czyści nowego pola ani nie odblokowuje nowej operacji',async()=>{
 const h=await providers();let reject;h.ctx.fetch=()=>new Promise((_,r)=>reject=r);const nodes=walk(h.group('github')),form=nodes.find(n=>n.tagName==='form'),token=nodes.find(n=>n.type==='password'),repo=nodes.find(n=>n.placeholder?.startsWith('owner/repo')),connect=nodes.find(n=>n.textContent==='2. Połącz i sprawdź'),write=nodes.find(n=>n.type==='checkbox');token.value='OLD_FIXTURE_ONLY';repo.value='owner/repo';write.checked=true;const first=form.onsubmit({preventDefault(){}});h.ctx.window.KripIntegrations.clear();assert.equal(write.checked,false);token.value='NEW_FIXTURE_ONLY';connect.disabled=true;reject(Error('OLD_PRIVATE_FAILURE'));await first;assert.equal(token.value,'NEW_FIXTURE_ONLY');assert.equal(connect.disabled,true);assert(!h.group('github').textContent.includes('OLD_PRIVATE_FAILURE'));
});
test('stan testu MCP pokazuje oczekiwanie i błąd sieci, stary finally nie zmienia nowej sesji',async()=>{
 const h=await providers();let reject;const original=h.ctx.api;h.ctx.api=(url,method)=>url==='/integrations/mcp/test'?new Promise((_,r)=>reject=r):original(url,method);const button=walk(h.group('mcp')).find(n=>n.textContent==='Test połączenia MCP');const pending=button.onclick();assert.equal(h.badge('mcp').attributes['data-state'],'pending');h.ctx.window.KripIntegrations.clear();h.api.clear();button.disabled=true;reject(Error('OLD_PRIVATE_FAILURE'));await pending;assert.equal(button.disabled,true);assert.equal(h.badge('mcp').textContent,'Nie sprawdzono');assert(!h.group('mcp').textContent.includes('OLD_PRIVATE_FAILURE'));
});

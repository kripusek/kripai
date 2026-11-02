'use strict';
window.KripIntegrations=(()=>{
 const $=id=>document.getElementById(id);
 let state,repo,token,write,drafts,connectButton,disconnectButton,mcpState,epoch=0;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const errors={tool_remote_denied:'GitHub odrzucił token, dostęp do repo lub ograniczył liczbę żądań.',tool_http_error:'Nie znaleziono repozytorium. Sprawdź nazwę i dostęp.',tool_dns_failed:'Nie można odnaleźć GitHuba.',tool_network_failed:'Nie można połączyć się z GitHubem.',integration_repositories_invalid:'Podaj od 1 do 5 nazw owner/repo, oddzielonych przecinkiem.',integration_configuration_failed:'Nie zapisano konfiguracji. Sprawdź folder danych i kopii.',integration_token_invalid:'Wpisz poprawny token w polu połączenia.'};
 function clear(){epoch++;if(token)token.value='';if(repo)repo.value='';if(state)state.textContent='';if(drafts)drafts.replaceChildren();$('integrationsDialog')?.close();}
 async function request(path,method='GET',body){
  // Sekret jest wyłącznie w ciele lokalnego żądania; nie dodajemy go do URL ani historii.
  const headers={};if(method!=='GET'){headers['X-CSRF-Token']=csrf();headers['Content-Type']='application/json';}
  const response=await fetch('/api/v1/integrations/github'+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let code='';try{code=(await response.json()).error?.code;}catch{}throw Error(errors[code]||'Połączenie nie powiodło się ('+response.status+').');}
  return response.status===204?null:response.json();
 }
 async function refresh(){
  const version=epoch;
  try{const data=await api('/integrations');if(version!==epoch)return;const github=data.items.find(x=>x.name==='github');
   const mcp=data.items.find(x=>x.name==='mcp');mcpState.textContent=mcp?.available?'Lokalny serwer dokumentacji gotowy. Włącz MCP w menu +. Dostęp tylko do odczytu.':'Lokalny serwer MCP niedostępny. Zaktualizuj program przez START.cmd.';
   state.textContent=github?.configured?'Połączono'+(github.login?' jako '+github.login:'')+' · '+github.repositories.join(', ')+((github.write_repositories||[]).length?' · tworzenie PR włączone':' · tylko odczyt. Propozycje zmian działają; publikacja PR wymaga włączenia zapisu poniżej i tokenu z uprawnieniami Contents/Pull requests: write.'):'Publiczny GitHub działa bez konta. Połącz konto do prywatnych repozytoriów i PR.';
   disconnectButton.disabled=!github?.configured;
   if(github?.configured){repo.value=github.repositories.join(', ');write.checked=!!github.write_repositories?.length;write.onchange?.();}
  }catch(e){state.textContent=e.message;}
 }
 async function refreshDrafts(){
  const version=epoch;
  try{const data=await api('/integrations/github/drafts');if(version!==epoch)return;drafts.replaceChildren();
   for(const item of data.items){
    const states={prepared:'Gotowe do publikacji',published:'PR utworzony',publishing:'Trwa publikacja',outcome_unknown:'Sprawdź wynik',branch_only:'Gałąź istnieje, brak PR'};
    const row=el('details'),title=el('summary',item.proposal.title+' · '+(states[item.state]||item.state)),content=el('pre',item.proposal.repository+'\n'+item.proposal.files.map(f=>f.diff||f.path+'\n'+f.content).join('\n\n')),publish=el('button','Utwórz gałąź i PR');
    publish.type='button';publish.disabled=item.state!=='prepared';publish.onclick=async()=>{const version=epoch;publish.disabled=true;try{const result=await api('/integrations/github/drafts/'+item.id+'/publish','POST');if(version===epoch)state.textContent='Utworzono PR: '+result.url;}catch(e){if(version===epoch)state.textContent=e.message;}finally{if(version===epoch)await refreshDrafts();}};
    row.append(title,content,publish);drafts.append(row);
    if(['publishing','outcome_unknown','branch_only'].includes(item.state)){
     const check=el('button','Sprawdź wynik w GitHub');check.type='button';check.onclick=async()=>{const version=epoch;check.disabled=true;try{const result=await api('/integrations/github/drafts/'+item.id+'/reconcile','POST');if(version===epoch)state.textContent=(result.state==='published'?'Potwierdzono PR: ':result.state==='branch_only'?'Potwierdzono gałąź, brak PR: ':'Nie potwierdzono gałęzi ani PR. Nie ponawiam zapisu: ')+result.url;}catch(e){if(version===epoch)state.textContent=e.message;}finally{if(version===epoch)await refreshDrafts();}};row.append(check);
    }
   }
   if(!data.items.length)drafts.textContent='Brak propozycji. Włącz GitHub i poproś o zmianę małego pliku w kripusek/kripusek-autoexec.';
  }catch(e){state.textContent=e.message;}
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const panel=$('integrationsPanel');state=el('p');state.setAttribute('role','status');repo=el('input');repo.placeholder='owner/repo, owner/drugie-repo';repo.maxLength=1000;repo.required=true;
  token=el('input');token.type='password';token.autocomplete='off';token.maxLength=512;token.required=true;
  write=el('input');write.type='checkbox';
  const form=el('form'),reposLabel=el('label','Repozytoria, do których zezwalasz na dostęp'),tokenLabel=el('label','Token GitHuba — tylko lokalnie, nigdy w rozmowie'),writeLabel=el('label','Tworzenie gałęzi i PR tylko w kripusek/kripusek-autoexec');writeLabel.className='check-row';
  reposLabel.append(repo);tokenLabel.append(token);writeLabel.append(write);
  const link=el('a','1. Utwórz ograniczony token w GitHub ↗');link.target='_blank';link.rel='noopener noreferrer';
  function tokenLink(){link.href='https://github.com/settings/personal-access-tokens/new?'+new URLSearchParams({name:'KripAI localhost',expires_in:'30',contents:write.checked?'write':'read',...(write.checked?{pull_requests:'write'}:{})}).toString();}
  write.onchange=tokenLink;tokenLink();
  connectButton=el('button','2. Połącz i sprawdź');connectButton.type='submit';disconnectButton=el('button','Odłącz lokalnie');disconnectButton.type='button';
  form.append(reposLabel,writeLabel,link,tokenLabel,connectButton,disconnectButton);
  const hint=el('p','Na GitHub wybierz Only select repositories i te same repozytoria. Token zapisujemy zaszyfrowany przez Windows. Nie wklejaj go do rozmowy.');hint.className='muted';
  form.onsubmit=async e=>{e.preventDefault();connectButton.disabled=true;disconnectButton.disabled=true;
   const secret=token.value,version=epoch;token.value='';try{const result=await request('/connect','POST',{repositories:repo.value.split(',').map(x=>x.trim()).filter(Boolean),token:secret,write:write.checked});if(version!==epoch)return;await refresh();state.textContent='Połączono jako '+result.login+'.';}catch(error){if(version===epoch)state.textContent=error.message;}finally{token.value='';connectButton.disabled=false;disconnectButton.disabled=false;}};
  disconnectButton.onclick=async()=>{disconnectButton.disabled=true;try{await request('/disconnect','POST');token.value='';repo.value='';write.checked=false;tokenLink();await refresh();state.textContent='Odłączono lokalnie. Unieważnij token również w ustawieniach GitHuba. Zaszyfrowana kopia konfiguracji pozostaje w folderze kopii.';}catch(e){state.textContent=e.message;}finally{disconnectButton.disabled=false;}};
  drafts=el('div');const refreshButton=el('button','Pokaż propozycje zmian');refreshButton.type='button';refreshButton.onclick=refreshDrafts;
  panel.append(state,form,hint,el('h3','Propozycje zmian'),refreshButton,drafts);
  mcpState=el('p','Lokalna dokumentacja KripAI, bez konta i internetu.');const mcpTest=el('button','Test połączenia MCP');mcpTest.type='button';mcpTest.onclick=async()=>{const version=epoch;mcpTest.disabled=true;try{const result=await api('/integrations/mcp/test','POST');if(version===epoch)mcpState.textContent=result.available?'MCP działa · dostępnych dokumentów: '+result.documents:'MCP niedostępny. '+({mcp_timeout:'Przekroczono czas połączenia.',mcp_disconnected:'Proces serwera zakończył połączenie.',mcp_protocol_invalid:'Niepoprawny protokół serwera.',mcp_remote_error:'Serwer odmówił odczytu.'}[result.error]||'Sprawdź pliki programu i uruchom test ponownie.');}catch(e){if(version===epoch)mcpState.textContent=e.message;}finally{mcpTest.disabled=false;}};
  panel.append(el('h3','MCP · dokumentacja lokalna'),mcpState,mcpTest);
  $('integrationsDialog').addEventListener('close',()=>{token.value='';});
 });
 return {refresh,clear};
})();

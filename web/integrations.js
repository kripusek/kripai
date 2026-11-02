'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const panel=document.createElement('details'),heading=document.createElement('summary'),state=document.createElement('p'),repo=document.createElement('input'),test=document.createElement('button');
 heading.textContent='Integracje i propozycje PR';repo.placeholder='owner/repo';repo.maxLength=201;test.textContent='Test połączenia GitHub';test.type='button';
 const drafts=document.createElement('div'),refresh=document.createElement('button');refresh.type='button';refresh.textContent='Pokaż propozycje zmian';panel.append(heading,state,repo,test,refresh,drafts);document.querySelector('.tools-bar').append(panel);
 panel.addEventListener('toggle',async()=>{if(!panel.open)return;try{const data=await api('/integrations');state.textContent=data.items.map(x=>x.error||(x.name==='web'?'Internet: '+x.provider:'GitHub publiczny bez konta; prywatny: '+(x.configured?x.repositories.join(', '):'nieskonfigurowany')+'. Publikacja PR: '+((x.write_repositories||[]).length?x.write_repositories.join(', '):'nieskonfigurowana. Użyj lokalnie scripts/configure-github.ps1'))).join('\n');}catch(e){state.textContent=e.message;}});
 refresh.onclick=async()=>{refresh.disabled=true;try{
  const data=await api('/integrations/github/drafts');drafts.replaceChildren();
  for(const item of data.items){
   const row=document.createElement('details'),title=document.createElement('summary'),content=document.createElement('pre'),publish=document.createElement('button');
   title.textContent=item.proposal.title+' · '+item.state;
   content.textContent=item.proposal.repository+'\n'+item.proposal.files.map(f=>f.diff||f.path+'\n'+f.content).join('\n\n');
   publish.type='button';publish.textContent='Utwórz gałąź i PR';publish.disabled=item.state!=='prepared';
   publish.onclick=async()=>{publish.disabled=true;try{const result=await api('/integrations/github/drafts/'+item.id+'/publish','POST');state.textContent='Utworzono PR: '+result.url;}catch(e){state.textContent=e.message;}finally{await refresh.onclick();}};
   row.append(title,content,publish);drafts.append(row);
  }
  if(!data.items.length)drafts.textContent='Brak propozycji. Włącz GitHub i poproś o zmianę konkretnego pliku w kripusek/kripusek-autoexec.';
 }catch(e){state.textContent=e.message;}finally{refresh.disabled=false;}};
 test.onclick=async()=>{test.disabled=true;try{const result=await api('/integrations/github/test','POST',{repository:repo.value,section:'tree'});const errors={integration_configuration_invalid:'Niepoprawna konfiguracja lokalna. Uruchom configure-github.ps1.',integration_credential_unavailable:'Nie można odszyfrować poświadczeń. Skonfiguruj je na tym koncie Windows.',tool_remote_denied:'GitHub odmówił dostępu lub przekroczono limit. Sprawdź uprawnienia tokenu.',tool_http_error:'Repozytorium niedostępne. Sprawdź nazwę i uprawnienia.',tool_dns_failed:'Nie można odnaleźć serwera GitHub.',tool_network_failed:'Nie można połączyć się z GitHub.'};state.textContent=result.available?'Połączenie działa. Dostęp tylko do odczytu.':'Połączenie niedostępne: '+(errors[result.error]||result.error);}catch(e){state.textContent=e.message;}finally{test.disabled=false;}};
});

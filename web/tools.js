'use strict';
window.KripTools=(()=>{
 const $=id=>document.getElementById(id);
 const labels={github_draft:'Przygotowuję propozycję zmian',web_read:'Czytam stronę WWW',web_search:'Szukam w internecie',github_read:'Czytam repozytorium GitHub',github_find:'Szukam repozytoriów GitHub'};
 function permissions(){return {allow_web:!!$('allowWeb').checked,allow_github:!!$('allowGithub').checked};}
 function clear(){$('allowWeb').checked=false;$('allowGithub').checked=false;}
 function renderSources(target,items){
  let list=target._toolSources;if(!list){list=document.createElement('div');list.className='rag-sources';target.parentNode.append(list);target._toolSources=list;}
  list.replaceChildren();
  for(const source of items||[]){
   const row=document.createElement('details'),title=document.createElement('summary');title.textContent='[W'+source.ordinal+'] '+source.title;
   const text=document.createElement('p');text.textContent=source.excerpt||source.text||'';row.append(title,text);
   try{const url=new URL(source.url);if(url.protocol==='https:'){const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Otwórz źródło';row.append(link);}}catch{}
   list.append(row);
  }
 }
 function activity(data){const errors={tool_resource_not_authorized:'Podaj adres HTTPS lub owner/repo w bieżącej wiadomości.',tool_address_denied:'Ten adres sieciowy jest zablokowany.',tool_timeout:'Przekroczono czas odczytu.',tool_dns_failed:'Nie udało się odnaleźć serwera.',tool_remote_denied:'Serwis odmówił odczytu lub ograniczył liczbę zapytań.',tool_response_too_large:'Odpowiedź API jest za duża.',tool_search_unavailable:'Wyszukiwarka jest chwilowo niedostępna.',tool_page_unreadable:'Nie znaleziono tekstu strony; może wymagać JavaScript lub logowania.'};return labels[data.name]?(data.state==='reading'?labels[data.name]+'…':data.state==='summarizing'?'Streszczam fragmenty długiej strony…':data.state==='completed'?'Odczyt zakończony.':errors[data.state]||'Nie udało się odczytać źródła.'):'Narzędzie niedostępne.';}
 return {permissions,clear,renderSources,activity};
})();

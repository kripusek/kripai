'use strict';
window.KripTools=(()=>{
 const $=id=>document.getElementById(id);
 const labels={mcp_files:'Czytam wybrany folder przez MCP',mcp_docs:'Czytam lokalną dokumentację przez MCP',github_draft:'Przygotowuję propozycję zmian',web_read:'Czytam stronę WWW',web_search:'Szukam w internecie',github_read:'Czytam repozytorium GitHub',github_find:'Szukam repozytoriów GitHub'};
 function permissions(){return {allow_web:!!$('allowWeb').checked,allow_github:!!$('allowGithub').checked,allow_mcp:!!$('allowMcp').checked};}
 function clear(){$('allowWeb').checked=false;$('allowGithub').checked=false;$('allowMcp').checked=false;window.KripMenu?.close();window.KripMenu?.summary();}
 function renderSources(target,items){
  let list=target._toolSources;if(!list){list=document.createElement('div');list.className='rag-sources';target.parentNode.append(list);target._toolSources=list;}
  list.replaceChildren();
  for(const source of items||[]){
   const row=document.createElement('details'),title=document.createElement('summary');title.textContent='[W'+source.ordinal+'] '+source.title;
   const text=document.createElement('p');text.textContent=source.excerpt||source.text||'';row.append(title,text);
   try{const local=(source.name==='mcp_files'&&/^\/api\/v1\/integrations\/mcp-files\/(?:catalog|document)\?root=[0-9a-f-]{36}&path=[A-Za-z0-9_.%/+\-]*$/.test(source.url))||source.name==='mcp_docs'&&/^\/api\/v1\/integrations\/mcp\/(?:catalog|document\?path=[A-Za-z0-9_.%/-]+)$/.test(source.url);const url=local?null:new URL(source.url);if(local||url.protocol==='https:'){const link=document.createElement('a');link.href=local?source.url:url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Otwórz źródło';row.append(link);}}catch{}
   list.append(row);
  }
 }
 function activity(data){const errors={mcp_files_scope_changed:'Folder MCP zmienił się. Ponów pytanie.',mcp_files_unavailable:'Przygotuj opcjonalny serwer MCP w Połączeniach.',mcp_files_path_denied:'Ta ścieżka dokumentu jest niedozwolona.',mcp_files_too_large:'Dokument przekracza limit 32 KiB.',mcp_files_directory_large:'Katalog ma ponad 200 pozycji. Wybierz mniejszy folder.',github_reference_changed:'PR zmienił się podczas odczytu. Ponów pytanie, aby odczytać spójną wersję.',github_sensitive_path_denied:'Odczyt tego pliku jest zablokowany, ponieważ jego nazwa wskazuje poświadczenia lub prywatne dane.',tool_search_domain_denied:'Przekierowanie wyniku prowadzi poza dozwolony filtr domen.',tool_search_filter_invalid:'Po site: podaj samą domenę, bez adresu URL, ścieżki ani danych logowania.',mcp_timeout:'Przekroczono czas odpowiedzi lokalnego serwera MCP.',mcp_disconnected:'Lokalny serwer MCP zakończył połączenie.',mcp_protocol_invalid:'Serwer MCP zwrócił niepoprawną odpowiedź.',mcp_remote_error:'Dokument MCP jest niedostępny lub przekracza limit odczytu.',tool_resource_not_authorized:'Podaj adres HTTPS, owner/repo lub ścieżkę dokumentu MCP w bieżącej wiadomości.',tool_address_denied:'Ten adres sieciowy jest zablokowany.',tool_timeout:'Przekroczono czas odczytu.',tool_dns_failed:'Nie udało się odnaleźć serwera.',tool_remote_denied:'Serwis odmówił odczytu lub ograniczył liczbę zapytań.',tool_response_too_large:'Odpowiedź API jest za duża.',tool_search_unavailable:'Wyszukiwarka jest chwilowo niedostępna.',tool_page_unreadable:'Nie znaleziono tekstu strony; może wymagać JavaScript lub logowania.'};return labels[data.name]?(data.state==='reading'?labels[data.name]+'…':data.state==='summarizing'?'Streszczam fragmenty długiej strony…':data.state==='completed'?'Odczyt zakończony.':errors[data.state]||'Nie udało się odczytać źródła.'):'Narzędzie niedostępne.';}
 return {permissions,clear,renderSources,activity};
})();

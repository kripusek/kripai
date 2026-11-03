'use strict';
window.KripMcpFiles=(()=>{
 let root,label,state,form,epoch=0;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const errors={mcp_files_not_configured:'Najpierw wybierz folder.',mcp_files_unavailable:'Przygotuj serwer. Wymagany Node.js 24+ w Program Files.',mcp_files_install_failed:'Nie przygotowano serwera. Sprawdź Node.js 24+, dostęp do npm i uprawnienia folderu programu.',mcp_files_configuration_invalid:'Podaj istniejący folder i krótką nazwę.',mcp_files_path_denied:'Folder lub plik niedozwolony. Nie wybieraj folderów danych, kopii, skrótów ani całego dysku.',mcp_files_directory_large:'Katalog zawiera ponad 200 pozycji. Wybierz mniejszy folder.',mcp_files_scope_changed:'Folder zmienił się. Ponów odczyt.',mcp_timeout:'Serwer nie odpowiedział w wyznaczonym czasie.',mcp_files_document_missing:'Nie można odczytać folderu lub dokumentu.'};
 async function request(path,method='GET',body){
  try{return await api('/integrations/mcp-files/'+path,method,body);}catch(e){throw Error(errors[e.code]||e.message||'Operacja MCP nie powiodła się.');}
 }
 function clear(){epoch++;if(root)root.value='';if(label)label.value='';if(state)state.textContent='';}
 async function refresh(){
  const version=epoch;if(!state)return;
  try{const data=await request('config');if(version!==epoch)return;root.value=data.root||'';label.value=data.label||'Moje dokumenty';state.textContent=(data.configured?'Wybrano: '+data.label+'. ':'Folder nie jest wybrany. ')+(data.available?'Serwer przygotowany.':'Serwer wymaga przygotowania (opcjonalny Node.js 24+).');}
  catch(e){if(version===epoch)state.textContent=e.message;}
 }
 async function action(button,operation){
  const version=epoch;button.disabled=true;
  try{const message=await operation();if(version!==epoch)return;await refresh();if(version===epoch&&message)state.textContent=message;}
  catch(e){if(version===epoch)state.textContent=e.message;}
  finally{button.disabled=false;}
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const panel=document.getElementById('integrationsPanel');state=el('p');state.setAttribute('role','status');
  root=el('input');root.required=true;root.maxLength=1024;root.placeholder='C:\\Notatki';root.autocomplete='off';
  label=el('input');label.required=true;label.maxLength=60;label.value='Moje dokumenty';
  const rootLabel=el('label','Folder dokumentów na tym komputerze'),nameLabel=el('label','Nazwa połączenia');rootLabel.append(root);nameLabel.append(label);
  const prepare=el('button','Przygotuj serwer MCP'),save=el('button','Wybierz folder'),test=el('button','Test odczytu'),disconnect=el('button','Odłącz folder');
  for(const button of [prepare,test,disconnect])button.type='button';save.type='submit';form=el('form');form.append(rootLabel,nameLabel,save);
  prepare.onclick=()=>action(prepare,async()=>{await request('prepare','POST');return 'Serwer przygotowany. Wybierz folder i sprawdź odczyt.';});
  form.onsubmit=e=>{e.preventDefault();const selection={root:root.value,label:label.value};return action(save,async()=>{await request('config','POST',selection);return 'Folder wybrany. Włącz MCP w menu + przy wysyłaniu wiadomości.';});};
  test.onclick=()=>action(test,async()=>{const data=await request('test','POST');return data.available?'MCP działa · dokumenty w katalogu: '+data.documents+' · pominięte pozycje: '+data.omitted_entries:(errors[data.error]||'Serwer odmówił odczytu. Sprawdź konfigurację folderu.');});
  disconnect.onclick=()=>action(disconnect,async()=>{await request('disconnect','POST');return 'Folder odłączony. Kopia konfiguracji pozostaje w folderze kopii.';});
  panel.append(el('h3','MCP · Twój folder dokumentów'),el('p','Opcjonalny oficjalny serwer filesystem 2.1.0. Tylko odczyt .md/.txt do 32 KiB, bez skrótów i ukrytych plików. Wybierz osobny folder przeznaczony do udostępnienia modelowi, bez prywatnych poświadczeń. Przygotowanie pobiera przypięty pakiet z npm; pozostałe funkcje KripAI działają bez Node.js.'),state,prepare,form,test,disconnect);
 });
 return {refresh,clear};
})();

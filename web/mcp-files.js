'use strict';
window.KripMcpFiles=(()=>{
 let root,label,state,form,browser,browseButton,searchInput,searchButton,rootId=null,browseEpoch=0,epoch=0;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const errors={mcp_files_query_invalid:'Podaj fragment nazwy (2–80 znaków): litery, cyfry, spacje, kropki, podkreślenia lub myślniki.',mcp_files_search_limit:'Folder jest za duży lub za głęboki do wyszukiwania. Wybierz mniejszy folder dokumentów.',mcp_files_search_links:'Wyszukiwanie wymaga folderu bez dowiązań i junction w nieukrytych podkatalogach.',mcp_files_not_configured:'Najpierw wybierz folder.',mcp_files_unavailable:'Przygotuj serwer. Wymagany Node.js 24+ w Program Files.',mcp_files_install_failed:'Nie przygotowano serwera. Sprawdź Node.js 24+, dostęp do npm i uprawnienia folderu programu.',mcp_files_configuration_invalid:'Podaj istniejący folder i krótką nazwę.',mcp_files_path_denied:'Folder lub plik niedozwolony. Nie wybieraj folderów danych, kopii, skrótów ani całego dysku.',mcp_files_directory_large:'Katalog zawiera ponad 200 pozycji. Wybierz mniejszy folder.',mcp_files_scope_changed:'Folder zmienił się. Ponów odczyt.',mcp_timeout:'Serwer nie odpowiedział w wyznaczonym czasie.',mcp_files_document_missing:'Nie można odczytać folderu lub dokumentu.'};
 async function request(path,method='GET',body){
  try{return await api('/integrations/mcp-files/'+path,method,body);}catch(e){throw Error(errors[e.code]||e.message||'Operacja MCP nie powiodła się.');}
 }
 function resetBrowser(){browseEpoch++;browser?.replaceChildren();}
 function clear(){epoch++;rootId=null;resetBrowser();if(browseButton)browseButton.disabled=true;if(searchButton)searchButton.disabled=true;if(searchInput)searchInput.value='';if(root)root.value='';if(label)label.value='';if(state)state.textContent='';}
 async function refresh(){
  const version=epoch;if(!state)return;
  try{const data=await request('config');if(version!==epoch)return;if(rootId!==(data.root_id||null)){rootId=data.root_id||null;resetBrowser();searchInput.value='';}browseButton.disabled=!(rootId&&data.configured&&data.available);searchButton.disabled=browseButton.disabled;root.value=data.root||'';label.value=data.label||'Moje dokumenty';state.textContent=(data.configured?'Wybrano: '+data.label+'. ':'Folder nie jest wybrany. ')+(data.available?'Serwer przygotowany.':'Serwer wymaga przygotowania (opcjonalny Node.js 24+).');}
  catch(e){if(version===epoch)state.textContent=e.message;}
 }
 function relative(value){return typeof value==='string'&&value.length>0&&value.length<=200&&!/[\\:\x00-\x1f\x7f]/.test(value)&&value.split('/').length<=6&&value.split('/').every(p=>p&&p!=='.'&&p!=='..'&&!p.startsWith('.'));}
 async function browse(path='',search=null){
  if(!rootId||path&&!relative(path))return;
  const id=rootId,version=++browseEpoch;browser.replaceChildren(el('p','Czytam katalog…'));
  try{
   const query=new URLSearchParams(search===null?{root:id,path}:{root:id,query:search}),data=await request((search===null?'catalog?':'search?')+query);
   if(id!==rootId||version!==browseEpoch)return;
   if(!Array.isArray(data.paths)||typeof data.text!=='string')throw Error('Niepoprawna odpowiedź katalogu.');
   browser.replaceChildren(el('p',search===null?'Katalog: '+(path||'/'):'Wyniki nazwy: '+search),el('p','Zapytaj o dokument przygotuje szkic i włączy MCP. Wiadomość wyślij samodzielnie.'));
   const navigation=el('div');
   for(const [title,next] of [['Folder główny',''],...(path?[['Katalog wyżej',path.split('/').slice(0,-1).join('/')]]:[])]){
    const button=el('button',title);button.type='button';button.onclick=()=>{if(id===rootId&&version===browseEpoch)return browse(next);};navigation.append(button);
   }
   browser.append(navigation);
   for(const line of data.text.split('\n')){
    if(!line.startsWith('[DIR] '))continue;const directory=line.slice(6);if(!relative(directory))continue;
    const button=el('button','Otwórz katalog: '+directory);button.type='button';button.onclick=()=>{if(id===rootId&&version===browseEpoch)return browse(directory);};browser.append(button);
   }
   let count=0;
   for(const file of data.paths){
    if(!relative(file)||!(/\.(md|txt)$/i).test(file))continue;count++;
    const row=el('div'),name=el('p',file),source=el('a','Otwórz źródło'),choose=el('button','Zapytaj o dokument');row.className='mcp-document-row';choose.type='button';choose.setAttribute('aria-label','Zapytaj o dokument: '+file);
    source.href='/api/v1/integrations/mcp-files/document?'+new URLSearchParams({root:id,path:file});source.target='_blank';source.rel='noopener noreferrer';
    choose.onclick=()=>{
     // Stary przycisk nie może przywrócić wyboru po zmianie folderu lub wylogowaniu.
     if(id!==rootId||version!==browseEpoch)return;
     if(window.KripAttachments?.has()){state.textContent='Usuń zdjęcie z wiadomości przed wybraniem dokumentu MCP.';return;}
     const prompt=document.getElementById('prompt'),reference=JSON.stringify(file);
     prompt.value=prompt.value.trim()?prompt.value+'\n\nDokument MCP (mcp_files): '+reference+'.':'Przeczytaj przez mcp_files dokument '+reference+' i podsumuj go po polsku.';
     document.getElementById('allowMcp').checked=true;window.KripMenu?.summary();document.getElementById('integrationsDialog').close();prompt.focus();
    };
    row.append(name,source,choose);browser.append(row);
   }
   browser.append(el('p',(search===null?'Dokumenty w tym katalogu: ':'Pokazane dokumenty: ')+count+'. Pominięte pozycje: '+(Number.isInteger(data.omitted_entries)?data.omitted_entries:0)+'.'));
   if(search!==null)browser.append(el('p','Pasujące dokumenty: '+(Number.isInteger(data.matched_documents)?data.matched_documents:count)+(data.truncated?'. Pokazano pierwsze 20; doprecyzuj nazwę.':'. Przeszukano wybrany folder i podkatalogi.')));
  }catch(e){if(id===rootId&&version===browseEpoch)browser.replaceChildren(el('p',e.message));}
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
  browser=el('div');browser.className='mcp-browser';browser.setAttribute('aria-live','polite');browseButton=el('button','Przeglądaj dokumenty');browseButton.type='button';browseButton.disabled=true;browseButton.onclick=()=>browse();
  searchInput=el('input');searchInput.required=true;searchInput.minLength=2;searchInput.maxLength=80;searchInput.placeholder='Fragment nazwy, np. raport';const searchLabel=el('label','Szukaj dokumentów po nazwie');searchLabel.append(searchInput);searchButton=el('button','Znajdź po nazwie');searchButton.type='submit';searchButton.disabled=true;const searchForm=el('form');searchForm.append(searchLabel,searchButton);searchForm.onsubmit=e=>{e.preventDefault();return browse('',searchInput.value.trim());};
  panel.append(el('h3','MCP · Twój folder dokumentów'),el('p','Opcjonalny oficjalny serwer filesystem 2.1.0. Tylko odczyt .md/.txt do 32 KiB, bez skrótów i ukrytych plików. Wybierz osobny folder przeznaczony do udostępnienia modelowi, bez prywatnych poświadczeń. Przygotowanie pobiera przypięty pakiet z npm; pozostałe funkcje KripAI działają bez Node.js.'),state,prepare,form,test,disconnect,browseButton,searchForm,browser);
 });
 return {refresh,clear};
})();

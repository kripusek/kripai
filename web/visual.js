'use strict';
// Wyniki służą do otwierania własnych plików; nie trafiają automatycznie do modelu.
window.KripVisual=(()=>{
 const $=id=>document.getElementById(id),chosen=new Set();
 let options={},epoch=0,revision=0,timer=null,loading=false,working=false,blocked=false,installed=false,statusLoaded=false,controller=null,listControls=[];
 const states={queued:'W kolejce',indexing:'Indeksuję',ready:'Gotowy',paused:'Wstrzymany',failed:'Błąd'};
 const errors={visual_not_installed:'Najpierw przygotuj lokalną pamięć obrazów.',visual_busy:'Trwa inne zadanie pamięci obrazów. Spróbuj za chwilę.',visual_not_ready:'Wybrany plik nie jest gotowy. Odśwież listę.',visual_model_changed:'Zmienił się koder. Przebuduj indeks.',visual_query_too_large:'Skróć opis wyszukiwania.',visual_query_invalid:'Wpisz krótki opis obrazu.',visual_index_failed:'Indeksowanie przerwane. Możesz wznowić od ostatniej zapisanej strony.',visual_encoder_failed:'Nie udało się uruchomić kodera. Spróbuj ponownie przygotować pamięć obrazów.',visual_encoder_timeout:'Przekroczono czas kodowania obrazu.',visual_quota:'Osiągnięto limit pamięci obrazów. Usuń niepotrzebny indeks.',visual_prepare_failed:'Nie udało się pobrać lub sprawdzić kodera. Sprawdź połączenie i spróbuj ponownie.',visual_installation_conflict:'Katalog kodera zawiera nierozpoznane pliki. Nie zostały zastąpione.',visual_python_unavailable:'Koder wymaga prywatnego Pythona 3.13 na Windows. Uruchom START.cmd.',visual_download_denied:'Nie udało się zweryfikować pobranych plików kodera. Spróbuj ponownie.',gaming_mode:'Wyłącz Gaming, aby przetwarzać obrazy.',login_required:'Zaloguj się ponownie.',backup_failed:'Nie udało się wykonać kopii. Indeks pozostał.',file_not_found:'Plik został usunięty.'};
 function node(tag,text){const element=document.createElement(tag);if(text!==undefined)element.textContent=text;return element;}
 function notice(text){$('visualNotice').textContent=text;}
 function clearResults(){$('visualResults').replaceChildren();}
 function controls(){
  $('visualPrepare').disabled=working||blocked||installed;
  $('visualRefresh').disabled=working||loading;
  $('visualSearch').disabled=working||blocked||!installed||!chosen.size||!$('visualQuery').value.trim();
  $('visualQuery').disabled=working||blocked;
  $('visualClear').disabled=working||!chosen.size;
  $('visualSelected').textContent=chosen.size?'Wybrane pliki: '+chosen.size+' / 5':'Wybierz gotowe pliki do wyszukania.';
  for(const [element,disabled] of listControls)element.disabled=disabled();
 }
 async function request(path,method='GET',body,signal){
  const headers={};if(method!=='GET')headers['X-CSRF-Token']=options.csrf();
  if(body!==undefined)headers['Content-Type']='application/json';
  const response=await fetch('/api/v1/visual'+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),signal});
  if(!response.ok){let code='';try{code=(await response.json()).error?.code;}catch{}throw Error(errors[code]||'Operacja pamięci obrazów nie powiodła się ('+response.status+').');}
  const data=response.status===204?null:await response.json();
  if(signal?.aborted){const error=Error('Anulowano');error.name='AbortError';throw error;}return data;
 }
 function schedule(active){clearTimeout(timer);timer=null;if(active&&$('visualDialog').open)timer=setTimeout(refresh,2500);}
 async function action(fn,text){
  if(working)return;const version=++epoch,change=++revision;loading=false;clearTimeout(timer);timer=null;working=true;controller=new AbortController();const signal=controller.signal;controls();notice(text);
  try{await fn(signal,version,change);}
  catch(error){if(version===epoch&&change===revision&&error.name!=='AbortError')notice(error.message);}
  finally{if(version===epoch&&change===revision){working=false;controller=null;controls();}}
 }
 function renderList(items){
  const ready=new Set(items.filter(row=>row.status==='ready').map(row=>row.id));let changed=false;
  for(const id of chosen)if(!ready.has(id)){chosen.delete(id);changed=true;}if(changed)clearResults();
  $('visualList').replaceChildren();listControls=[];
  for(const row of items){
   const section=node('section');section.className='visual-document';const label=node('label'),box=node('input');box.type='checkbox';box.checked=chosen.has(row.id);box.disabled=row.status!=='ready'||blocked||working;
   listControls.push([box,()=>row.status!=='ready'||blocked||working]);
   box.onchange=()=>{if(blocked||working)return;if(box.checked&&chosen.size>=5){box.checked=false;notice('Wybierz najwyżej 5 plików.');return;}if(box.checked)chosen.add(row.id);else chosen.delete(row.id);revision++;clearResults();controls();};
   label.append(box,node('span',row.filename));section.append(label,node('p',(states[row.status]||'Nie zindeksowano')+' · '+(row.images||0)+' obrazów · '+Math.min((row.next_page||1)-1,row.pages)+'/'+row.pages+' stron'));
   if(row.error_code)section.append(node('p',errors[row.error_code]||'Zadanie zatrzymane. Spróbuj wznowić.'));
   const button=(text,fn,allowBlocked=false)=>{const item=node('button',text);item.type='button';const disabled=()=>working||(!allowBlocked&&(blocked||!installed));item.disabled=disabled();listControls.push([item,disabled]);item.onclick=()=>{if(disabled())return;return action(async(signal,version)=>{await fn(signal);if(version===epoch){notice('Zaktualizowano zadanie.');await refresh(true);}},'Zmieniam zadanie…');};section.append(item);};
   const endpoint='/documents/'+encodeURIComponent(row.id);
   if(['queued','indexing'].includes(row.status))button('Wstrzymaj',signal=>request(endpoint+'/pause','POST',undefined,signal),true);
   else if(row.status!=='ready')button(row.status?'Wznów':'Indeksuj',signal=>request(endpoint+'/index','POST',{},signal));
   if(row.status&&!['queued','indexing'].includes(row.status))button('Przebuduj',async signal=>{if(!confirm('Przebudować indeks tego pliku? Najpierw powstanie kopia poprzednich danych.'))return;await request(endpoint+'/index','POST',{rebuild:true},signal);});
   if(row.status)button('Usuń indeks',async signal=>{if(!confirm('Usunąć indeks obrazów? Oryginalny plik pozostanie; najpierw powstanie kopia.'))return;await request(endpoint,'DELETE',undefined,signal);},true);
   $('visualList').append(section);
  }
  if(!items.length)$('visualList').append(node('p','Dodaj PNG, JPEG lub PDF w panelu „Zdjęcia i PDF”, a potem wróć tutaj.'));
 }
 async function refresh(fromAction=false,recheck=false){
  if(loading||(!fromAction&&working))return;const version=epoch;loading=true;controls();
  try{
   // Status sprawdza pliki kodera; nie liczymy setek MB hashy przy każdym odpytywaniu kolejki.
   const [state,data]=await Promise.all([recheck||!statusLoaded?request('/status'):Promise.resolve({installed}),request('/documents')]);if(version!==epoch)return;
   installed=state.installed===true;statusLoaded=true;$('visualState').textContent=installed?'Koder gotowy · lokalnie na CPU':'Koder nieprzygotowany · pobierz go raz, aby rozpocząć';
   renderList(data.items);schedule(data.items.some(row=>['queued','indexing'].includes(row.status)));
  }catch(error){if(version===epoch)notice(error.message);}
  finally{if(version===epoch){loading=false;controls();}}
 }
 function stop(){epoch++;revision++;loading=false;working=false;controller?.abort();controller=null;clearTimeout(timer);timer=null;controls();}
 function close(){stop();$('visualDialog').close();}
 function hide(){close();chosen.clear();installed=false;statusLoaded=false;listControls=[];$('visualList').replaceChildren();clearResults();$('visualQuery').value='';$('visualState').textContent='';notice('');controls();}
 function configure(value){
  options=value;
  $('visualButton').onclick=()=>{if(!$('visualDialog').open)$('visualDialog').showModal();notice('');refresh(false,true);};
  $('visualClose').onclick=close;$('visualDialog').addEventListener('cancel',stop);$('visualDialog').addEventListener('close',()=>{if(!$('visualDialog').open)stop();});
  $('visualRefresh').onclick=()=>{notice('');return refresh(false,true);};
  $('visualClear').onclick=()=>{if(working)return;chosen.clear();revision++;clearResults();controls();return refresh();};
  $('visualQuery').oninput=()=>{revision++;clearResults();controls();};
  $('visualPrepare').onclick=()=>{if(blocked||installed)return;return action(async(signal,version)=>{await request('/prepare','POST',undefined,signal);if(version===epoch){notice('Koder przygotowany. Możesz indeksować wybrane pliki.');await refresh(true,true);}},'Pobieram i sprawdzam koder CPU. Pierwsze przygotowanie może potrwać kilka minut.');};
  $('visualForm').onsubmit=event=>{
   event.preventDefault();const query=$('visualQuery').value.trim();if(blocked||!installed||!chosen.size||!query)return;
   const attachment_ids=Array.from(chosen);clearResults();return action(async(signal,version,change)=>{
    const data=await request('/search','POST',{query,attachment_ids},signal);if(version!==epoch||change!==revision)return;
    for(const row of data.items){
     if(!attachment_ids.includes(row.attachment_id)||!Number.isInteger(row.page)||row.page<1||row.page>50)continue;
     const result=node('section');result.className='visual-result';result.append(node('p',row.filename+' · str. '+row.page));
     const open=node('button','Otwórz stronę');open.type='button';open.onclick=()=>{if(working||blocked||version!==epoch||change!==revision)return;close();options.openPage?.(row.attachment_id,row.page);};
     const ask=node('button','Zapytaj o obraz');ask.type='button';ask.onclick=()=>{if(working||blocked||version!==epoch||change!==revision)return;close();options.askPage?.(row.attachment_id,row.page);};result.append(open,ask);$('visualResults').append(result);
    }
    notice($('visualResults').children.length?'Najbliższe wyniki. Sprawdź podgląd — podobieństwo nie gwarantuje zgodności.':'Brak wyników w wybranych plikach.');
   },'Szukam w wybranych obrazach…');
  };
  window.addEventListener('pagehide',stop);controls();
 }
 return {configure,hide,stop,setBlocked(value){if(blocked===value)return;blocked=value;if(value)stop();controls();if($('visualDialog').open)refresh();}};
})();

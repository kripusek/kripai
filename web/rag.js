'use strict';
// Wybór źródeł jest jawnym działaniem użytkownika, nigdy treścią odpowiedzi modelu.
window.KripRag=(()=>{
 const $=id=>document.getElementById(id),chosen=new Set();let options={},epoch=0,timer=null,blocked=false,loading=false;
 const states={queued:'W kolejce',indexing:'Indeksuję',ready:'Gotowy',paused:'Wstrzymany',failed:'Błąd'};
 const errors={rag_not_installed:'Brakuje modelu pamięci. Uruchom START.cmd.',rag_no_text:'Brak tekstu na stronie PDF. Skan wymaga OCR; indeks nie jest gotowy.',rag_page_too_long:'Strona ma ponad 12000 znaków. Podziel PDF na mniejsze dokumenty.',rag_index_failed:'Indeksowanie przerwane. Możesz wznowić od ostatniej zapisanej strony.',rag_model_changed:'Zmienił się model pamięci. Przebuduj indeks.',rag_busy:'Trwa inne zadanie pamięci. Spróbuj za chwilę.',rag_quota:'Osiągnięto limit 20000 fragmentów. Usuń niepotrzebny indeks.',rag_not_ready:'Wybrany dokument nie jest gotowy. Odśwież listę.',gaming_mode:'Wyłącz Gaming, aby indeksować dokumenty.',login_required:'Zaloguj się ponownie.',backup_failed:'Nie udało się wykonać kopii. Indeks pozostał.'};
 async function request(path,method='GET',body){
  const headers={};if(method!=='GET')headers['X-CSRF-Token']=options.csrf();
  if(body!==undefined)headers['Content-Type']='application/json';
  const response=await fetch('/api/v1/rag'+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){let code='';try{code=(await response.json()).error?.code;}catch{}throw Error(errors[code]||'Operacja pamięci nie powiodła się ('+response.status+').');}
  return response.status===204?null:response.json();
 }
 function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
 function summary(){$('ragSelected').textContent=chosen.size?'Dokumenty do pytania: '+chosen.size:'Pytanie bez dokumentów';}
 function schedule(){clearTimeout(timer);if(!$('ragDialog').hidden&&$('ragDialog').open)timer=setTimeout(refresh,2500);}
 async function refresh(){
  if(loading)return;loading=true;const version=epoch;
  try{
   const data=await request('/documents');if(version!==epoch)return;
   $('ragList').replaceChildren();const ready=new Set(data.items.filter(r=>r.status==='ready').map(r=>r.id));
   for(const id of chosen)if(!ready.has(id))chosen.delete(id);
   for(const row of data.items){
    const section=el('section');section.className='rag-document';
    const label=el('label'),box=el('input');box.type='checkbox';box.checked=chosen.has(row.id);box.disabled=row.status!=='ready'||blocked;
    box.onchange=()=>{if(box.checked&&chosen.size>=5){box.checked=false;$('ragNotice').textContent='Wybierz najwyżej 5 dokumentów.';return;}if(box.checked)chosen.add(row.id);else chosen.delete(row.id);summary();};
    label.append(box,el('span',row.filename));section.append(label);
    section.append(el('p',(states[row.status]||'Nie zindeksowano')+' · '+(row.chunks||0)+' fragmentów · '+Math.min((row.next_page||1)-1,row.pages)+'/'+row.pages+' stron'));
    if(row.error_code)section.append(el('p',errors[row.error_code]||'Zadanie zatrzymane. Spróbuj wznowić.'));
    const button=(text,action)=>{const b=el('button',text);b.type='button';b.disabled=blocked;b.onclick=async()=>{if(blocked)return;b.disabled=true;const v=epoch;try{await action();if(v===epoch)await refresh();}catch(e){if(v===epoch)$('ragNotice').textContent=e.message;}finally{if(v===epoch)b.disabled=blocked;}};section.append(b);};
    if(['queued','indexing'].includes(row.status))button('Wstrzymaj',()=>request('/documents/'+row.id+'/pause','POST'));
    else if(row.status!=='ready')button(row.status?'Wznów':'Indeksuj',()=>request('/documents/'+row.id+'/index','POST',{}));
    if(row.status&&row.status!=='indexing')button('Przebuduj',()=>request('/documents/'+row.id+'/index','POST',{rebuild:true}));
    if(row.status)button('Usuń indeks',async()=>{if(!confirm('Usunąć indeks i wycinki źródeł z historii? PDF pozostanie; kopia zachowa poprzednie dane.'))return;await request('/documents/'+row.id,'DELETE');if(version===epoch){chosen.delete(row.id);summary();}});
    $('ragList').append(section);
   }
   if(!data.items.length)$('ragList').append(el('p','Dodaj PDF w panelu „Zdjęcia i PDF”, a potem wróć tutaj.'));
   summary();
  }catch(e){if(version===epoch)$('ragNotice').textContent=e.message;}
  finally{if(version===epoch){loading=false;schedule();}}
 }
 function stop(){epoch++;loading=false;clearTimeout(timer);timer=null;}
 function hide(){stop();chosen.clear();$('ragList').replaceChildren();$('ragNotice').textContent='';$('ragDialog').close();summary();}
 function configure(value){options=value;
  $('ragButton').onclick=()=>{$('ragDialog').showModal();$('ragNotice').textContent='';refresh();};
  $('ragClose').onclick=()=>{stop();$('ragDialog').close();};$('ragDialog').addEventListener('cancel',stop);
  $('ragRefresh').onclick=refresh;$('ragClear').onclick=()=>{chosen.clear();summary();refresh();};
  window.addEventListener('pagehide',stop);summary();
 }
 function renderSources(target,items){
  let list=target._sourcesNode;
  if(!list){list=el('div');list.className='rag-sources';target.parentNode.append(list);target._sourcesNode=list;}
  list.replaceChildren();
  for(const source of items||[]){const row=el('details'),title=el('summary','['+source.ordinal+'] '+source.filename+' · str. '+source.page);
   row.append(title,el('p',source.excerpt||source.text||''));const link=el('a','Pobierz PDF');link.href='/api/v1/files/'+encodeURIComponent(source.attachment_id)+'/download';row.append(link);list.append(row);}
 }
 return {configure,hide,stop,selection:()=>Array.from(chosen),setBlocked(value){if(value!==blocked){blocked=value;stop();if($('ragDialog').open)refresh();}},renderSources};
})();

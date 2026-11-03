'use strict';
window.KripConversationSearch=(()=>{
 let options={},nodes=null,epoch=0,query='',cursor=null,working=false;
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 function node(tag,text){const value=document.createElement(tag);if(text)value.textContent=text;return value;}
 function paint(){nodes.submit.disabled=working;nodes.next.hidden=cursor===null;nodes.next.disabled=working;nodes.results.setAttribute('aria-busy',String(working));}
 function clear(){++epoch;query='';cursor=null;working=false;if(!nodes)return;nodes.input.value='';nodes.results.replaceChildren();nodes.status.textContent='Wyszukaj fragment treści wiadomości. Wyszukiwanie rozpoczyna się po kliknięciu Szukaj.';paint();}
 function response(value){
  if(!value||!Array.isArray(value.items)||value.items.length>20||typeof value.partial!=='boolean'||!Number.isSafeInteger(value.scanned_messages)||value.scanned_messages<0||value.scanned_messages>2000||(value.next_cursor!==null&&(typeof value.next_cursor!=='string'||!/^\d{1,19}$/.test(value.next_cursor)||BigInt(value.next_cursor)<1n||BigInt(value.next_cursor)>9223372036854775807n)))throw Error('Nieprawidłowa odpowiedź wyszukiwania. Spróbuj ponownie.');
  for(const item of value.items){if(!item||!UUID.test(item.conversation_id||'')||typeof item.title!=='string'||typeof item.excerpt!=='string'||!['user','assistant'].includes(item.role)||!Number.isSafeInteger(item.seq)||item.seq<1||typeof item.created_at!=='number'||!Number.isFinite(new Date(item.created_at*1000).getTime()))throw Error('Nieprawidłowa odpowiedź wyszukiwania. Spróbuj ponownie.');}
  return value;
 }
 async function search(older=false){
  if(working)return;
  const next=older?query:nodes.input.value.trim();
  if(!older&&(Array.from(next).length<2||Array.from(next).length>120||/[\p{Cc}]/u.test(next))){nodes.status.textContent='Wpisz od 2 do 120 znaków fragmentu wiadomości.';return;}
  if(older&&cursor===null)return;
  const requestedCursor=older?cursor:null,version=++epoch;query=next;working=true;cursor=null;nodes.results.replaceChildren();nodes.status.textContent='Przeszukuję wiadomości…';paint();
  try{
   const path='/conversations/search?q='+encodeURIComponent(next)+(requestedCursor===null?'':'&cursor='+encodeURIComponent(requestedCursor));
   const raw=await options.api(path);if(version!==epoch)return;
   const data=response(raw);cursor=data.next_cursor;
   if(requestedCursor!==null&&cursor!==null&&BigInt(cursor)>=BigInt(requestedCursor))throw Error('Serwer nie przesunął wyszukiwania do starszych wiadomości. Spróbuj ponownie.');
   for(const item of data.items){
    const button=node('button'),title=node('strong',item.title||'Rozmowa bez nazwy'),excerpt=node('span',item.excerpt),details=node('small',(item.role==='user'?'Ty':'Asystent')+' · '+new Date(item.created_at*1000).toLocaleString('pl-PL'));
    button.type='button';button.className='conversation-search-result';title.className='conversation-search-title';excerpt.className='conversation-search-excerpt';details.className='conversation-search-details';button.append(title,excerpt,details);
    button.onclick=async()=>{if(version!==epoch)return;try{await options.onSelect?.({...item});}catch{if(version===epoch)nodes.status.textContent='Nie udało się otworzyć znalezionej wiadomości. Spróbuj ponownie.';}};
    nodes.results.append(button);
   }
   const found=data.items.length?'Wyniki na tej stronie: '+data.items.length+'.':'Brak dopasowań na tej stronie.';
   nodes.status.textContent=found+' Sprawdzono wiadomości: '+data.scanned_messages+'. '+(cursor!==null?'Nie sprawdzono jeszcze całej historii. Kliknij „Przeszukaj starsze”.':data.partial?'Wyszukiwanie częściowe: nie sprawdzono całej historii.':'Sprawdzono historię do najstarszej wiadomości w tym wyszukiwaniu.');
  }catch(error){if(version!==epoch)return;cursor=requestedCursor;nodes.results.replaceChildren();nodes.status.textContent='Nie udało się wyszukać wiadomości. '+(error.message||'Spróbuj ponownie.');}
  finally{if(version===epoch){working=false;paint();}}
 }
 function configure(value){
  options=value;if(nodes)return;
  const host=options.host||document.getElementById('conversationSearch'),form=node('form'),label=node('label','Fragment wiadomości'),input=node('input'),submit=node('button','Szukaj'),reset=node('button','Wyczyść'),status=node('p'),results=node('div'),next=node('button','Przeszukaj starsze');
  host.className+=' conversation-search';host.setAttribute('aria-label','Wyszukiwanie wiadomości w historii');form.className='conversation-search-form';input.type='search';input.autocomplete='off';input.name='conversation-message-query';input.id='conversationSearchQuery';label.htmlFor=input.id;submit.type='submit';reset.type='button';next.type='button';status.className='conversation-search-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');results.className='conversation-search-results';label.append(input);form.append(label,submit,reset);host.append(form,status,results,next);nodes={host,form,input,submit,reset,status,results,next};
  form.onsubmit=event=>{event.preventDefault();return search();};next.onclick=()=>search(true);reset.onclick=()=>{clear();input.focus();};
  // Pisanie unieważnia poprzedni wynik, ale nie wysyła zapytania do serwera.
  input.addEventListener('input',()=>{++epoch;working=false;query='';cursor=null;results.replaceChildren();status.textContent='Kliknij Szukaj, aby przeszukać wiadomości.';paint();});
  clear();
 }
 return {configure,clear};
})();

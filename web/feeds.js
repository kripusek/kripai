'use strict';
window.KripFeeds=(()=>{
 let options={},epoch=0,serial=0,pending=false,input,status,results,test,group;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const errors={feed_format_denied:'Nieprawidłowy lub nieobsługiwany kanał RSS 2.0 / Atom 1.0.',feed_encoding_denied:'Kanał wymaga innego kodowania. Obsługiwane jest UTF-8.',feed_xml_denied:'Kanał zawiera niedozwoloną deklarację XML.',feed_xml_limit:'Kanał przekracza limit złożoności XML.',tool_address_denied:'Adres lokalny lub prywatny jest zablokowany.',tool_url_invalid:'Podaj publiczny adres HTTPS bez danych logowania.',tool_remote_denied:'Serwis odmówił dostępu lub ograniczył zapytania.',tool_response_too_large:'Kanał przekracza limit odczytu 512 KiB.',tool_network_failed:'Nie udało się połączyć z wydawcą kanału.',tool_http_error:'Wydawca nie udostępnił kanału pod tym adresem.',tool_timeout:'Przekroczono czas odczytu kanału.',login_required:'Sesja wygasła. Zaloguj się ponownie.'};
 function configure(value){options=value;}
 function clear(){++epoch;++serial;pending=false;if(input)input.value='';if(status)status.textContent='Gotowy do testu publicznego kanału.';results?.replaceChildren();if(test)test.disabled=false;group?.setStatus('neutral','Bez konta');}
 function safeUrl(value){const url=new URL(value);if(url.protocol!=='https:'||url.username||url.password||value.length>2048)throw Error('tool_url_invalid');return url.href;}
 function prepare(url,version,feed=false){
  if(version!==epoch)return;
  if(window.KripAttachments?.has()){options.notice?.('Odłącz zdjęcie przed dodaniem pytania o kanał lub artykuł.');return;}
  const prompt=document.getElementById('prompt'),question=(feed?'Podsumuj wpisy kanału RSS/Atom ':'Przeczytaj i podsumuj ')+url;
  const value=prompt.value.trim();if(value.length+question.length+2>4000){options.notice?.('Szkic jest za długi. Skróć go przed dodaniem adresu.');return;}
  prompt.value=value?value+'\n\n'+question:question;document.getElementById('allowWeb').checked=true;window.KripMenu?.summary();document.getElementById('integrationsDialog').close();prompt.focus();options.notice?.('Pytanie dodano do szkicu. Kliknij Wyślij, gdy będzie gotowe.');
 }
 function render(data,version){
  if(typeof data.title!=='string'||!Array.isArray(data.items)||data.items.length>5||data.count!==data.items.length||typeof data.truncated!=='boolean')throw Error('feed_protocol');
  const url=safeUrl(data.url),rows=data.items.map(item=>{
   if(typeof item.title!=='string'||typeof item.date!=='string'||typeof item.excerpt!=='string')throw Error('feed_protocol');
   return {...item,url:safeUrl(item.url)};
  });
  results.replaceChildren();group?.setStatus('ok',rows.length+' wpisów'+(data.truncated?' · częściowo':''));status.textContent=data.title+' · wpisów: '+rows.length+(data.truncated?' · zakres częściowy':'')+'. To zajawki, nie przeczytane artykuły.';
  const ask=el('button','Dodaj pytanie o kanał');ask.type='button';ask.onclick=()=>prepare(url,version,true);results.append(ask);
  for(const item of rows){
   const row=el('section'),link=el('a',item.title);link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';row.append(link,el('small',item.date),el('p',item.excerpt));
   const ask=el('button','Zapytaj o artykuł');ask.type='button';ask.onclick=()=>prepare(item.url,version);row.append(ask);results.append(row);
  }
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const panel=document.getElementById('integrationsPanel');group=window.KripIntegrationGroups?.mount({id:'feeds',title:'RSS / Atom',parent:panel});group?.setStatus('neutral','Bez konta');const section=group?.body||el('section');section.className+=' feed-panel';section.append(el('h3','Kanały RSS / Atom'),el('p','Publiczny kanał HTTPS, bez konta. Test pobiera do 5 wpisów i krótkie opisy; nie uruchamia modelu ani subskrypcji.'));
  const form=el('form'),label=el('label','Adres kanału');input=el('input');input.type='url';input.required=true;input.maxLength=2048;input.placeholder='https://www.djangoproject.com/rss/weblog/';label.append(input);
  test=el('button','Test i odczyt kanału');test.type='submit';status=el('p','Gotowy do testu publicznego kanału.');status.setAttribute('role','status');results=el('div');results.className='feed-results';
  input.oninput=()=>{++epoch;group?.setStatus('neutral','Adres zmieniony');results.replaceChildren();status.textContent='Adres zmieniony. Uruchom test ponownie.';};
  form.onsubmit=async event=>{
   event.preventDefault();if(pending)return;const version=++epoch,request=++serial;results.replaceChildren();pending=true;test.disabled=true;group?.setStatus('pending','Czytam…');status.textContent='Czytam kanał…';
   try{
    const url=safeUrl(input.value.trim()),data=await options.api('/integrations/feeds/test','POST',{url});
    if(version!==epoch)return;if(!data.available)throw Error(data.error||'feed_protocol');render(data,version);
   }catch(error){if(version===epoch){group?.setStatus('error','Błąd odczytu');status.textContent=errors[error.code||error.message]||'Nie udało się odczytać kanału. Sprawdź adres i spróbuj ponownie.';}}
   finally{if(request===serial){pending=false;test.disabled=false;}}
  };
  form.append(label,test);section.append(form,status,results);if(!group)panel.append(section);
 });
 return {configure,clear};
})();

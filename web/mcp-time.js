'use strict';
window.KripMcpTime=(()=>{
 let options={},epoch=0,serial=0,pending=false,available=false,group,zone,status,output,source,prepare,test,ask;
 const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
 const errors={mcp_time_unavailable:'Najpierw przygotuj opcjonalny serwer czasu.',mcp_time_timezone_invalid:'Podaj dokładną nazwę IANA, np. Europe/Warsaw lub UTC.',mcp_time_arguments_invalid:'Nieprawidłowa strefa lub godzina. Użyj nazwy IANA i HH:MM; konwersja dotyczy dzisiaj.',mcp_time_python_unavailable:'Serwer wymaga prywatnego Pythona 3.13 na Windows.',mcp_time_installation_conflict:'W folderze runtime są nieznane pliki. Zachowano je; sprawdź instalację.',mcp_time_prepare_failed:'Nie przygotowano serwera czasu. Sprawdź dostęp do PyPI i folderu programu.',mcp_time_lock_invalid:'Nieprawidłowy manifest serwera. Zaktualizuj program.',mcp_timeout:'Serwer czasu nie odpowiedział na czas.',mcp_disconnected:'Serwer czasu zakończył połączenie.',mcp_protocol_invalid:'Serwer czasu zwrócił nieprawidłowe dane.',login_required:'Sesja wygasła. Zaloguj się ponownie.'};
 function configure(value){options=value;}
 function paint(){if(!prepare)return;prepare.disabled=pending||available;test.disabled=pending||!available;ask.disabled=pending||!available;zone.disabled=pending;}
 function clear(){++epoch;++serial;pending=false;available=false;if(zone)zone.value='Europe/Warsaw';if(status)status.textContent='Opcjonalny serwer czasu wymaga sprawdzenia.';output?.replaceChildren();if(source){source.hidden=true;source.removeAttribute('href');}paint();}
 function getEpoch(){return epoch;}
 function update(value,version=epoch){if(version!==epoch)return;available=value?.available===true;paint();if(!pending)group?.setStatus('neutral',available?'Gotowy do testu':'Wymaga przygotowania');if(status&&!pending)status.textContent=available?'Serwer przygotowany. Uruchom test odczytu.':'Przygotowanie pobierze przypięte zależności z PyPI. Kolejne odczyty działają lokalnie.';}
 function timezone(){const value=zone.value.trim();if(value.length>80||!/^\w[\w+-]*(?:\/[\w+-]+){0,3}$/.test(value))throw Error('mcp_time_timezone_invalid');return value;}
 function clockText(text,expected){
  let snapshot;try{snapshot=JSON.parse(text);}catch{throw Error('mcp_protocol_invalid');}const value=snapshot?.result;
  if(snapshot?.action!=='now'||!value||value.timezone!==expected||typeof value.datetime!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value.datetime)||!Number.isFinite(new Date(value.datetime).getTime()))throw Error('mcp_protocol_invalid');
  const date=value.datetime.slice(0,10).split('-').reverse().join('.'),offset=value.datetime.endsWith('Z')?'+00:00':value.datetime.slice(-6);
  return value.timezone+' · '+date+'\n'+value.datetime.slice(11,19)+' (UTC'+offset+')';
 }
 async function work(kind){
  if(pending)return;const version=++epoch,request=++serial;pending=true;paint();group?.setStatus('pending',kind==='prepare'?'Przygotowuję…':'Testuję…');output.replaceChildren();source.hidden=true;source.removeAttribute('href');
  try{
   const body=kind==='prepare'?undefined:{action:'now',timezone:timezone()},data=await options.api('/integrations/mcp-time/'+kind,'POST',body);
   if(version!==epoch)return;
   if(kind==='prepare'){
    if(data.prepared!==true)throw Error('mcp_protocol_invalid');available=true;status.textContent='Serwer przygotowany. Wykonaj test czasu.';group?.setStatus('neutral','Gotowy do testu');
   }else{
    if(data.available!==true)throw Error(data.error||'mcp_protocol_invalid');
    if(data.content_kind!=='time_snapshot'||typeof data.text!=='string'||data.text.length>8000||typeof data.url!=='string'||!/^\/api\/v1\/integrations\/mcp-time\/result\?data=[A-Za-z0-9_-]{1,1800}$/.test(data.url))throw Error('mcp_protocol_invalid');
    const label=clockText(data.text,body.timezone);available=true;output.textContent=label;source.href=data.url;source.hidden=false;status.textContent='Odczyt czasu przez MCP zakończony. To zapis chwili odczytu.';group?.setStatus('ok','Test odczytu OK');
   }
  }catch(error){if(version===epoch){const code=error.code||error.message;if(code==='mcp_time_unavailable')available=false;status.textContent=errors[code]||'Nie udało się wykonać operacji serwera czasu. Ponów próbę.';group?.setStatus('error','Błąd operacji');}}
  finally{if(request===serial){pending=false;++epoch;paint();}}
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const panel=document.getElementById('integrationsPanel');group=window.KripIntegrationGroups?.mount({id:'mcp_time',title:'MCP · czas i strefy',parent:panel});const section=group?.body||el('section');
  section.append(el('p','Oficjalny serwer MCP czasu, tylko odczyt. Bez konta i GPU. Przygotowanie pobiera około 16 MB zależności; odczyt i konwersje nie potrzebują internetu. Konwersja HH:MM dotyczy dzisiejszej daty w strefie źródłowej.'));
  prepare=el('button','Przygotuj serwer czasu');prepare.type='button';prepare.onclick=()=>work('prepare');
  const form=el('form'),label=el('label','Strefa IANA do testu');zone=el('input');zone.value='Europe/Warsaw';zone.maxLength=80;zone.required=true;label.append(zone);
  test=el('button','Test odczytu czasu');test.type='submit';form.onsubmit=e=>{e.preventDefault();return work('test');};form.append(label,test);
  zone.oninput=()=>{++epoch;output.replaceChildren();source.hidden=true;source.removeAttribute('href');status.textContent='Strefa zmieniona. Uruchom test ponownie.';group?.setStatus('neutral','Strefa zmieniona');};
  ask=el('button','Dodaj pytanie o czas');ask.type='button';ask.onclick=()=>{
   if(pending||!available)return;
   try{
    const selected=timezone();if(window.KripAttachments?.has()){options.notice?.('Odłącz zdjęcie przed dodaniem pytania o czas.');return;}
    const prompt=document.getElementById('prompt'),question='Odczytaj przez MCP aktualny czas w strefie IANA '+selected+'.',value=prompt.value;
    if(value.length+question.length+(value?2:0)>4000){options.notice?.('Szkic jest za długi. Skróć go przed dodaniem pytania.');return;}
    prompt.value=value?value+'\n\n'+question:question;document.getElementById('allowMcp').checked=true;window.KripMenu?.summary();document.getElementById('integrationsDialog').close();prompt.focus();options.notice?.('Pytanie dodano do szkicu. Kliknij Wyślij, gdy będzie gotowe.');
   }catch{options.notice?.(errors.mcp_time_timezone_invalid);}
  };
  status=el('p','Opcjonalny serwer czasu wymaga przygotowania.');status.setAttribute('role','status');output=el('p');output.className='mcp-time-output';source=el('a','Otwórz zapisany wynik czasu');source.hidden=true;source.target='_blank';source.rel='noopener noreferrer';
  section.append(prepare,form,ask,status,output,source);if(!group)panel.append(section);paint();
 });
 return {configure,clear,update,getEpoch};
})();

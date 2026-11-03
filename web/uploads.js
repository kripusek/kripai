'use strict';
window.KripUploads=(()=>{
 const KEY='kripai.uploads.v1',MAX=8*1024*1024,CHUNK=524288,LIMIT=12;
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 let epoch=0;const pending=new Set(),active=new Set();
 const aborted=()=>Object.assign(new Error('Wysyłanie przerwano. Wybierz ponownie ten sam plik, aby wznowić.'),{name:'AbortError'});
 const protocol=()=>new Error('Nieprawidłowa odpowiedź serwera przesyłania pliku.');
 function records(){try{const value=JSON.parse(sessionStorage.getItem(KEY)||'[]');return Array.isArray(value)?value.slice(-LIMIT).filter(r=>r&&UUID.test(r.id)&&typeof r.name==='string'&&r.name.length>0&&r.name.length<=180&&Number.isInteger(r.size)&&r.size>0&&r.size<=MAX&&/^[a-f0-9]{64}$/.test(r.sha256)).map(({id,name,size,sha256})=>({id,name,size,sha256})):[];}catch{return [];}}
 function save(rows){try{sessionStorage.setItem(KEY,JSON.stringify(rows.slice(-LIMIT)));}catch{/* Prywatny tryb przeglądarki może wyłączyć pamięć sesji. */}}
 function clear(){++epoch;for(const request of pending)request.abort();try{sessionStorage.removeItem(KEY);}catch{} }
 async function send(file,options={}){
  const version=epoch,controller=new AbortController(),signal=controller.signal;
  const check=()=>{if(version!==epoch||signal.aborted||options.signal?.aborted)throw aborted();};
  const cancel=()=>controller.abort();options.signal?.addEventListener('abort',cancel,{once:true});pending.add(controller);
  let fingerprint,resumeId,ownsActive=false;
  try{
   check();
   if(!file||typeof file.arrayBuffer!=='function'||typeof file.slice!=='function'||!Number.isInteger(file.size)||file.size<=0||file.size>MAX)throw new Error('Wybierz niepusty plik o rozmiarze do 8 MiB.');
   if(!globalThis.crypto?.subtle||typeof crypto.randomUUID!=='function')throw new Error('Przeglądarka nie obsługuje bezpiecznego wznawiania plików. Otwórz aplikację pod adresem localhost w aktualnej przeglądarce.');
   if(!UUID.test(options.job||'')||typeof options.csrf!=='function')throw new Error('Brak danych sesji przesyłania pliku.');
   const name=String(file.name||'plik').replaceAll('\\','/').split('/').pop().trim();
   if(!name||name.length>180||/[\u0000-\u001f\u007f]/.test(name))throw new Error('Nazwa pliku musi mieć od 1 do 180 znaków i nie może zawierać znaków sterujących.');
   const bytes=await file.arrayBuffer();check();
   const digest=await crypto.subtle.digest('SHA-256',bytes);check();
   const sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
   fingerprint=JSON.stringify([version,name,file.size,sha256]);
   if(active.has(fingerprint))throw new Error('Ten plik jest już przesyłany. Poczekaj na zakończenie.');
   active.add(fingerprint);ownsActive=true;
   const rows=records();let record=rows.find(r=>r.name===name&&r.size===file.size&&r.sha256===sha256);
   if(!record){record={id:crypto.randomUUID(),name,size:file.size,sha256};rows.push(record);save(rows);}
   resumeId=record.id;const base='/api/v1/media/uploads/'+record.id;
   async function request(url,method='GET',body){
    check();const headers={};if(method!=='GET')headers['X-CSRF-Token']=options.csrf();
    if(method==='POST'&&body!==undefined)headers['Content-Type']='application/json';
    let response;
    try{response=await fetch(url,{method,headers,body,signal,credentials:'same-origin'});}catch(error){check();throw Object.assign(new Error('Utracono połączenie podczas przesyłania. Wybierz ponownie plik, aby wznowić.'),{retryable:true});}
    check();
    if(!response.ok){
     const messages={401:'Sesja wygasła. Zaloguj się ponownie.',403:'Brak uprawnień do przesłania pliku. Odśwież sesję.',404:'Nie znaleziono przesyłanego pliku.',410:'Przesyłanie wygasło. Wybierz plik ponownie.',409:'Serwer nie może teraz przyjąć pliku. Sprawdź tryb Gaming i limit plików.',413:'Plik lub fragment przekracza dozwolony rozmiar.'};
     const codes={
      upload_quota:'Są już 3 niedokończone przesyłania. W panelu Zdjęcia i PDF użyj przycisku „Usuń niedokończone wysyłki”, aby zwolnić miejsce.',
      upload_digest_mismatch:'Suma kontrolna pliku nie zgadza się. Usuń niedokończone przesyłania i wybierz plik ponownie.',
      upload_offset_conflict:'Nie zgadza się pozycja fragmentu pliku. Wybierz ponownie ten sam plik, aby wznowić od pozycji potwierdzonej przez serwer.',
      upload_incomplete:'Serwer nie otrzymał jeszcze całego pliku. Wybierz ponownie ten sam plik, aby dokończyć przesyłanie.',
      upload_expired:'Przesyłanie wygasło. Wybierz plik ponownie.',
      upload_file_gone:'Gotowy plik został usunięty lub wygasł. Wybierz plik ponownie.',
      file_quota:'Osiągnięto limit liczby plików lub miejsca. Usuń niepotrzebne pliki albo niedokończone przesyłania w panelu Zdjęcia i PDF.',
      gaming_mode:'Przesyłanie plików jest niedostępne w trybie Gaming. Włącz tryb Normalny i wybierz plik ponownie.',
      backup_failed:'Nie udało się wykonać kopii danych przed porządkowaniem przesyłań. Sprawdź miejsce na dysku i spróbuj ponownie.'
     };
     // Serwer wybiera wyłącznie znany komunikat; treść pliku ani opis błędu nie trafiają do UI.
     let code;try{const data=await response.json();if(typeof data?.error?.code==='string')code=data.error.code;}catch{}check();
     const message=response.status===401||response.status===403?messages[response.status]:Object.hasOwn(codes,code)?codes[code]:messages[response.status]||'Nie udało się przesłać pliku.';
     throw Object.assign(new Error(message),{status:response.status,retryable:response.status>=500});
    }
    let result;try{result=await response.json();}catch(error){check();if(error.name==='TypeError')throw Object.assign(new Error('Utracono odpowiedź serwera. Wybierz ponownie plik, aby wznowić.'),{retryable:true});throw protocol();}check();return result;
   }
   function status(value){
    if(!value||value.id!==record.id||value.size!==file.size||value.sha256!==sha256||value.filename!==name||value.chunk_size!==CHUNK||!Number.isFinite(value.expires_at)||value.expires_at<=0||!Number.isInteger(value.received)||value.received<0||value.received>file.size||!['uploading','completed'].includes(value.status)||(value.status==='completed'&&(value.received!==file.size||!UUID.test(value.attachment_id||'')))||(value.status==='uploading'&&value.attachment_id!==null))throw protocol();
    return value;
   }
   async function read(){for(let attempt=0;;attempt++){try{return status(await request(base));}catch(error){if(!error.retryable||attempt>=2)throw error;}}}
   function progress(value){check();options.onProgress?.(value.received,file.size);check();return value;}
   let state;
   for(let attempt=0;!state;attempt++){
    try{state=status(await request('/api/v1/media/uploads','POST',JSON.stringify(record)));}
    catch(error){if(!error.retryable||attempt>=2)throw error;try{state=await read();}catch(found){if(found.status!==404)throw found;}}
   }
   progress(state);
   while(state.status==='uploading'&&state.received<file.size){
    const offset=state.received,end=Math.min(offset+CHUNK,file.size);let advanced=false;
    for(let attempt=0;!advanced;attempt++){
     let next;
     try{next=status(await request(base+'/chunks?offset='+offset,'PUT',file.slice(offset,end)));}
     catch(error){if(!error.retryable||attempt>=2)throw error;next=await read();}
     if(next.received!==offset&&next.received!==end)throw protocol();
     if(next.received===end){state=progress(next);advanced=true;}
     else if(attempt>=2)throw new Error('Serwer nie potwierdził fragmentu pliku. Wybierz plik ponownie, aby wznowić.');
    }
   }
   function attachment(value){if(!value||!UUID.test(value.id||'')||value.id!==record.id||typeof value.filename!=='string'||!value.filename)throw protocol();return value;}
   for(let attempt=0;;attempt++){
    if(state.status==='completed'){
     for(let readAttempt=0;;readAttempt++){try{return attachment(await request('/api/v1/files/'+state.attachment_id));}catch(error){if(!error.retryable||readAttempt>=2)throw error;}}
    }
    try{return attachment(await request('/api/v1/media/jobs/'+options.job+'/uploads/'+record.id+'/complete','POST'));}
    catch(error){if(!error.retryable||attempt>=2)throw error;state=progress(await read());}
   }
  }catch(error){if(error.status===410&&resumeId&&version===epoch)save(records().filter(r=>r.id!==resumeId));throw error;
  }finally{pending.delete(controller);options.signal?.removeEventListener('abort',cancel);if(ownsActive)active.delete(fingerprint);}
 }
 return {send,clear};
})();

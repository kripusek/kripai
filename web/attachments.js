'use strict';
window.KripAttachments=(()=>{
 const $=id=>document.getElementById(id);let options={},pending=null,locked=false,epoch=0,request=null,job=null;
 function clear(){++epoch;if(job)fetch('/api/v1/media/jobs/'+job+'/cancel',{method:'POST',headers:{'X-CSRF-Token':options.csrf()},keepalive:true}).catch(()=>{});request?.abort();request=null;job=null;if(pending)URL.revokeObjectURL(pending.url);pending=null;$('attachedImage').removeAttribute('src');$('attachmentPreview').hidden=true;$('imagePicker').value='';}
 function add(file){
  if(locked){options.notice('Poczekaj na zakończenie bieżącej operacji.');return;}
  if(!file||!['image/png','image/jpeg'].includes(file.type)){options.notice('Wybierz PNG lub JPEG.');return;}
  if(file.size>8*1024*1024){options.notice('Obraz może mieć najwyżej 8 MiB.');return;}
  clear();pending={file,url:URL.createObjectURL(file),id:null};$('attachedImage').src=pending.url;$('attachmentPreview').hidden=false;options.notice('Zdjęcie dodane. Dopisz pytanie i kliknij Wyślij.');
 }
 async function upload(){
  if(!pending)return null;if(pending.id)return pending.id;const selected=pending,version=epoch;job=crypto.randomUUID();request=new AbortController();
  try{const response=await fetch('/api/v1/media/jobs/'+job+'/files?name='+encodeURIComponent(selected.file.name||'wklejony-obraz.png'),{method:'POST',headers:{'X-CSRF-Token':options.csrf()},body:selected.file,signal:request.signal});
   if(!response.ok)throw Error('Nie udało się przesłać zdjęcia. Sprawdź plik, tryb Gaming i limit plików w panelu Zdjęcia i PDF.');
   const data=await response.json();if(version!==epoch)throw Error('Wysyłanie anulowano.');selected.id=data.id;return data.id;
  }finally{if(version===epoch){job=null;request=null;}}
 }
 function configure(value){options=value;$('attachButton').onclick=()=>$('imagePicker').click();$('imagePicker').onchange=()=>add($('imagePicker').files[0]);$('removeImage').onclick=()=>{if(!locked)clear();};
  $('prompt').addEventListener('paste',event=>{const files=[...(event.clipboardData?.items||[])].filter(i=>i.kind==='file').map(i=>i.getAsFile()).filter(Boolean);if(!files.length)return;event.preventDefault();if(files.length!==1){options.notice('Do jednej wiadomości dodaj jedno zdjęcie.');return;}add(files[0]);});
  $('composer').addEventListener('dragover',event=>{if([...(event.dataTransfer?.types||[])].includes('Files'))event.preventDefault();});
  $('composer').addEventListener('drop',event=>{const files=[...(event.dataTransfer?.files||[])];if(!files.length)return;event.preventDefault();if(files.length!==1){options.notice('Do jednej wiadomości dodaj jedno zdjęcie.');return;}add(files[0]);});window.addEventListener('pagehide',clear);
 }
 return {configure,clear,upload,has:()=>!!pending,currentId:()=>pending?.id||null,setLocked(value){locked=value;$('attachButton').disabled=value;$('removeImage').disabled=value;}};
})();

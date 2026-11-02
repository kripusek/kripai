'use strict';
window.KripGpu=(()=>{
 const $=id=>document.getElementById(id);let epoch=0;
 const errors={gpu_probe_unavailable:'Pomiar NVIDIA jest niedostępny. Czat może nadal działać.',gpu_driver_unavailable:'Sterownik NVIDIA nie udostępnił pomiaru.',gpu_probe_timeout:'Pomiar karty przekroczył czas oczekiwania.',gpu_data_invalid:'Sterownik zwrócił nieobsługiwany format pomiaru.',gpu_probe_failed:'Nie udało się uruchomić pomiaru NVIDIA.'};
 function clear(){epoch++;$('gpuMetrics').replaceChildren();$('gpuRefresh').disabled=false;$('settings').close();}
 async function refresh(){
  const mine=++epoch,box=$('gpuMetrics'),button=$('gpuRefresh');button.disabled=true;box.textContent='Odczytuję pamięć karty…';
  try{
   const data=await api('/system/gpu');if(mine!==epoch)return;
   box.replaceChildren();
   if(!data.available){box.textContent=errors[data.error]||'Pomiar karty jest niedostępny.';return;}
   if(!Array.isArray(data.devices)||!data.devices.length)throw Error('Brak danych karty.');
   for(const device of data.devices){
    if(!Number.isInteger(device.total_mib)||device.total_mib<=0||!Number.isInteger(device.used_mib)||device.used_mib<0||device.used_mib>device.total_mib||!Number.isInteger(device.free_mib)||device.free_mib<0||device.free_mib>device.total_mib)throw Error('Niepoprawne dane pamięci karty.');
    const card=document.createElement('div');card.className='gpu-card';
    const name=document.createElement('strong');name.textContent=String(device.name||'NVIDIA GPU');
    const value=document.createElement('p');value.textContent=device.used_mib+' / '+device.total_mib+' MiB zajęte · '+device.free_mib+' MiB wolne wg sterownika';
    const bar=document.createElement('progress');bar.max=device.total_mib;bar.value=device.used_mib;bar.setAttribute('aria-label','Zajętość VRAM całej karty');
    card.append(name,value,bar);box.append(card);
   }
   const note=document.createElement('small');note.textContent='Cała karta, również inne programy. Kontekst: '+data.context_tokens+' tokenów; odpowiedź do '+data.output_tokens_per_segment+' tokenów na porcję. Pomiar: '+new Date(data.sampled_at*1000).toLocaleTimeString()+'.';box.append(note);
  }catch(error){if(mine===epoch)box.textContent='Nie udało się odczytać pomiaru karty. Spróbuj ponownie.';}
  finally{if(mine===epoch)button.disabled=false;}
 }
 document.addEventListener('DOMContentLoaded',()=>{$('gpuRefresh').onclick=refresh;$('settings').addEventListener('close',()=>{epoch++;$('gpuRefresh').disabled=false;});});
 return {refresh,clear};
})();

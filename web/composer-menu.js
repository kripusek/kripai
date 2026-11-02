'use strict';
window.KripMenu=(()=>{
 const $=id=>document.getElementById(id);
 function close(){const menu=$('composerMenu');if(menu)menu.hidden=true;$('composerPlus')?.setAttribute('aria-expanded','false');}
 function summary(){const names=[];if($('allowWeb').checked)names.push('Internet');if($('allowGithub').checked)names.push('GitHub');$('enabledTools').textContent=names.join(' · ');}
 document.addEventListener('DOMContentLoaded',()=>{
  const button=$('composerPlus'),menu=$('composerMenu');
  button.onclick=()=>{const opening=menu.hidden;menu.hidden=!opening;button.setAttribute('aria-expanded',String(opening));if(opening)$('attachButton').focus();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!menu.hidden){close();button.focus();}});
  document.addEventListener('click',e=>{if(!menu.hidden&&!menu.contains(e.target)&&!button.contains(e.target))close();});
  for(const name of ['allowWeb','allowGithub'])$(name).addEventListener('change',summary);
  for(const [source,target] of [['menuFiles','filesButton'],['menuRag','ragButton']])$(source).onclick=()=>{close();$(target).click();};
  $('attachButton').addEventListener('click',close);
  $('composer').addEventListener('submit',close);
  $('menuIntegrations').onclick=()=>{close();$('integrationsDialog').showModal();window.KripIntegrations?.refresh();};
  $('integrationsClose').onclick=()=>$('integrationsDialog').close();
  summary();
 });
 return {close,summary};
})();

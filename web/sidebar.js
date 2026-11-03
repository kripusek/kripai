'use strict';
window.KripSidebar=(()=>{
 const $=id=>document.getElementById(id),media=window.matchMedia('(max-width:700px)');let opened=false;
 function paint(){
  const active=media.matches&&opened,side=$('sidebar');side.hidden=media.matches&&!opened;
  $('sidebarBackdrop').hidden=!active;$('chatMain').inert=active;
  $('workspace').setAttribute('data-sidebar-open',String(active));$('sidebarToggle').setAttribute('aria-expanded',String(active));
  if(active){side.setAttribute('role','dialog');side.setAttribute('aria-modal','true');}
  else{side.removeAttribute('role');side.removeAttribute('aria-modal');}
 }
 function close(restore=false){opened=false;paint();if(restore&&media.matches)$('sidebarToggle').focus();}
 function toggle(){if(!media.matches)return;opened=!opened;window.KripMenu?.close();paint();if(opened)$('sidebarClose').focus();else $('sidebarToggle').focus();}
 document.addEventListener('DOMContentLoaded',()=>{
  $('sidebarToggle').onclick=toggle;$('sidebarClose').onclick=()=>close(true);$('sidebarBackdrop').onclick=()=>close(true);
  $('sidebar').addEventListener('click',event=>{
   const button=event.target.closest?.('button,a');if(!opened||!button||button.id==='sidebarClose')return;
   if($('conversationSearch')?.contains?.(button))return;
   close();if(!document.querySelector('dialog[open]'))$('prompt').focus();
  });
  document.addEventListener('keydown',event=>{
   if(!media.matches||!opened)return;
   if(event.key==='Escape'){event.preventDefault();close(true);return;}
   if(event.key!=='Tab')return;
   const nodes=[...$('sidebar').querySelectorAll('button,a[href],input,select,textarea,[tabindex]')].filter(node=>!node.disabled&&node.tabIndex!==-1&&node.getClientRects().length);
   const first=nodes[0],last=nodes[nodes.length-1];if(!first)return;
   if(!$('sidebar').contains(document.activeElement)){event.preventDefault();first.focus();}
   else if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
   else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  });
  media.addEventListener('change',()=>{const focused=$('sidebar').contains(document.activeElement);close();if(media.matches&&focused)$('sidebarToggle').focus();});
  paint();
 });
 return {close};
})();

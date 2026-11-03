'use strict';
window.KripConversationBranch=(()=>{
 const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
 let options={},current=null,busy=false,working=false,epoch=0,buttons=new Set();const attached=new WeakMap();
 function paint(){for(const item of buttons)item.button.disabled=busy||working||item.version!==epoch||item.cid!==current;}
 function configure(value){options=value;}
 function setContext(cid,reset=false){const next=UUID.test(cid||'')?cid:null;if(next===current&&!reset)return;++epoch;current=next;working=false;for(const item of buttons)item.button.disabled=true;buttons=new Set();}
 function clear(){setContext(null);busy=false;}
 function setBusy(value){busy=!!value;paint();}
 function valid(value,cid){return value&&UUID.test(value.id||'')&&value.id!==cid&&typeof value.title==='string'&&Array.from(value.title).length<=200&&typeof value.created_at==='number'&&Number.isFinite(new Date(value.created_at*1000).getTime())&&Number.isSafeInteger(value.copied_messages)&&value.copied_messages>0&&value.copied_messages<=1000;}
 function attach(container,{conversationId,messageId,role}={}){
  if(!container||role!=='assistant'||!UUID.test(conversationId||'')||!UUID.test(messageId||'')||conversationId!==current)return null;
  const previous=attached.get(container);if(previous&&previous.version===epoch&&previous.cid===conversationId&&previous.mid===messageId)return previous.button;
  const button=document.createElement('button');button.type='button';button.className='conversation-branch';button.textContent='Nowa rozmowa od tej odpowiedzi';
  const item={button,cid:conversationId,mid:messageId,version:epoch,key:null};buttons.add(item);attached.set(container,item);container.append(button);paint();
  button.onclick=async()=>{
   if(busy||working||item.version!==epoch||item.cid!==current)return;
   const version=epoch;working=true;paint();
   try{
    if(!item.key){if(typeof globalThis.crypto?.randomUUID!=='function')throw Error('branch_crypto');item.key=crypto.randomUUID();}
    // Ten sam klucz przy ponowieniu odzyskuje wynik po utracie odpowiedzi.
    const value=await options.api('/conversations/'+encodeURIComponent(item.cid)+'/branch','POST',{message_id:item.mid},item.key);
    if(version!==epoch||current!==item.cid)return;
    if(!valid(value,item.cid))throw Error('branch_protocol');
    await options.onBranch?.(value);
   }catch(error){
    if(version!==epoch||current!==item.cid)return;
    const messages={branch_crypto:'Przeglądarka nie obsługuje bezpiecznego tworzenia nowej rozmowy. Otwórz aplikację w aktualnej przeglądarce pod adresem localhost.',branch_protocol:'Serwer zwrócił nieprawidłowe dane nowej rozmowy. Spróbuj ponownie.',not_found:'Nie znaleziono rozmowy lub wybranej odpowiedzi. Odśwież historię.',branch_point:'Nową rozmowę można utworzyć tylko od odpowiedzi asystenta.',branch_too_large:'Rozmowa przekracza limit kopiowania: 1000 wiadomości lub 8 MiB. Wybierz wcześniejszą odpowiedź.',generation_busy:'Poczekaj na zakończenie bieżącej odpowiedzi i spróbuj ponownie.',login_required:'Sesja wygasła. Zaloguj się ponownie.'};
    const code=error.code||error.message;options.notice?.(Object.hasOwn(messages,code)?messages[code]:'Nie udało się otworzyć nowej rozmowy od tej odpowiedzi. Kliknij ponownie, aby bezpiecznie ponowić próbę.');
   }finally{if(version===epoch){working=false;paint();}}
  };
  return button;
 }
 return {configure,setContext,setBusy,clear,attach};
})();

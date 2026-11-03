'use strict';
window.KripMessageCopy=(()=>{
 let options={},epoch=0,working=false,buttons=new Set();const attached=new WeakMap();
 function configure(value={}){options=value;}
 function paint(){
  for(const item of buttons){item.button.disabled=item.version!==epoch;item.button.setAttribute('aria-disabled',String(working));}
 }
 function clear(){++epoch;working=false;for(const item of buttons){item.button.disabled=true;item.button.setAttribute('aria-disabled','true');}buttons=new Set();}
 function attach(container,{getText}={}){
  if(!container||typeof getText!=='function')return null;
  let item=attached.get(container);
  if(item){item.getText=getText;item.version=epoch;buttons.add(item);paint();return item.button;}
  const button=document.createElement('button');button.type='button';button.className='message-copy';button.textContent='Kopiuj całą wiadomość';
  item={button,getText,version:epoch};attached.set(container,item);buttons.add(item);container.append(button);paint();
  button.onclick=async()=>{
   if(working||item.version!==epoch)return;
   const version=epoch;
   if(typeof globalThis.navigator?.clipboard?.writeText!=='function'){options.notice?.('Ta przeglądarka nie udostępnia kopiowania do schowka. Zaznacz tekst wiadomości i skopiuj go ręcznie.');return;}
   working=true;paint();
   try{
    // Pobieramy aktualne źródło dopiero po kliknięciu, także podczas streamingu.
    const text=item.getText();
    if(version!==epoch)return;
    if(typeof text!=='string')throw Error();
    if(!text){options.notice?.('Ta wiadomość nie zawiera jeszcze tekstu do skopiowania.');return;}
    await navigator.clipboard.writeText(text);
    if(version===epoch)options.notice?.('Skopiowano całą wiadomość.');
   }catch{
    if(version===epoch)options.notice?.('Nie udało się skopiować wiadomości. Zezwól przeglądarce na dostęp do schowka lub zaznacz tekst i skopiuj go ręcznie.');
   }finally{if(version===epoch){working=false;paint();}}
  };
  return button;
 }
 return {configure,attach,clear};
})();

'use strict';
window.KripConversations=(()=>{
 let options={},current=null,title='',epoch=0,working=false,nodes=null;
 function node(tag,text){const value=document.createElement(tag);if(text)value.textContent=text;return value;}
 function closeMenu(restore=false){nodes.actions.hidden=true;nodes.toggle.setAttribute('aria-expanded','false');if(restore)nodes.toggle.focus();}
 function paint(){
  nodes.toggle.disabled=!current;nodes.rename.disabled=!current;
  for(const [format,link] of nodes.exports){
   if(current)link.href='/api/v1/conversations/'+encodeURIComponent(current)+'/export?format='+format;
   else link.removeAttribute('href');
   link.setAttribute('aria-disabled',String(!current));link.tabIndex=current?0:-1;
  }
  nodes.save.disabled=working||!current;nodes.input.disabled=working;
 }
 function closeDialog(restore=true){++epoch;working=false;nodes.dialog.close();paint();if(restore&&current)nodes.toggle.focus();}
 function setCurrent(id,value=''){
  current=id||null;title=typeof value==='string'?value:'';++epoch;working=false;
  if(!nodes)return;
  closeMenu();nodes.dialog.close();nodes.input.value='';nodes.status.textContent='';paint();
 }
 function configure(value){
  options=value;if(nodes)return;
  const holder=node('section'),toggle=node('button','Rozmowa'),actions=node('div');
  holder.className='conversation-actions';toggle.className='conversation-actions-toggle';actions.className='conversation-actions-list';
  holder.setAttribute('aria-label','Działania rozmowy');toggle.type='button';toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls','conversationActions');
  actions.id='conversationActions';actions.hidden=true;actions.setAttribute('role','group');actions.setAttribute('aria-label','Działania wybranej rozmowy');
  const rename=node('button','Zmień nazwę');rename.type='button';actions.append(rename);
  const exports=[];
  for(const [format,label] of [['md','Pobierz Markdown'],['json','Pobierz JSON']]){
   const link=node('a',label);link.download='';link.target='_blank';link.rel='noopener noreferrer';link.onclick=event=>{if(!current)event.preventDefault();else closeMenu();};actions.append(link);exports.push([format,link]);
  }
  holder.append(toggle,actions);(options.header||document.querySelector('#chatMain header')).append(holder);
  const dialog=node('dialog'),heading=node('h2','Nazwa rozmowy'),form=node('form'),label=node('label','Nowa nazwa'),input=node('input'),status=node('p'),save=node('button','Zapisz nazwę'),cancel=node('button','Anuluj');
  heading.id='conversationRenameHeading';dialog.setAttribute('aria-labelledby',heading.id);label.htmlFor='conversationTitle';input.id='conversationTitle';input.type='text';input.maxLength=200;input.required=true;input.autocomplete='off';status.setAttribute('role','status');status.setAttribute('aria-live','polite');save.type='submit';cancel.type='button';
  label.append(input);form.append(label,status,save,cancel);dialog.append(heading,form);document.body.append(dialog);
  nodes={holder,toggle,actions,rename,exports,dialog,input,status,save,cancel,form};
  toggle.onclick=()=>{if(!current)return;const opening=actions.hidden;actions.hidden=!opening;toggle.setAttribute('aria-expanded',String(opening));if(opening)rename.focus();};
  holder.addEventListener('keydown',event=>{if(event.key==='Escape'&&!actions.hidden){event.preventDefault();closeMenu(true);}});
  document.addEventListener('click',event=>{if(!actions.hidden&&!holder.contains(event.target))closeMenu();});
  rename.onclick=()=>{if(!current)return;closeMenu();input.value=title;status.textContent='';dialog.showModal();input.focus();input.select();};
  cancel.onclick=()=>closeDialog();dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog();});
  form.onsubmit=async event=>{
   event.preventDefault();if(!current||working)return;
   const raw=input.value,next=raw.trim();
   if(!next||next.length>200||/[\p{Cc}\p{Cs}\u2028\u2029]/u.test(raw)){status.textContent='Wpisz od 1 do 200 znaków w jednej linii.';input.focus();return;}
   const id=current,version=++epoch;working=true;status.textContent='Zapisuję nazwę…';paint();
   try{
    const result=await options.api('/conversations/'+encodeURIComponent(id),'PATCH',{title:next});
    if(version!==epoch||current!==id)return;
    title=result.title;working=false;dialog.close();paint();toggle.focus();await options.onRename?.(id,title);
   }catch(error){if(version===epoch&&current===id){working=false;status.textContent=error.code==='conversation_title'?'Wpisz od 1 do 200 znaków w jednej linii.':error.message;paint();}}
  };
  paint();
 }
 return {configure,setCurrent,clear(){setCurrent(null);}};
})();

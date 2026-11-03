const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk,Node}=require('./dom.cjs');
const source=fs.readFileSync(path.join(__dirname,'../web/conversation-actions.js'),'utf8');
function harness(){
 const doc=document(),header=new Node('header'),calls=[],renamed=[];doc.body=new Node('body');doc.listeners={};doc.addEventListener=(k,fn)=>doc.listeners[k]=fn;
 const create=doc.createElement;doc.createElement=tag=>{
  const value=create(tag);value.focus=()=>doc.activeElement=value;value.select=()=>value.selected=true;value.contains=other=>walk(value).includes(other);return value;
 };
 let handler=async()=>({title:'Nowa nazwa'});
 const ctx={document:doc,window:{}};vm.createContext(ctx);vm.runInContext(source,ctx);
 const api=ctx.window.KripConversations;api.configure({header,api:async(...args)=>{calls.push(args);return handler(...args);},onRename:(...args)=>renamed.push(args)});
 const find=text=>walk(header).find(n=>n.textContent===text),dialog=doc.body.children[0],form=dialog.children[1],input=form.children[0].children[0],status=form.children[1],save=form.children[2],cancel=form.children[3];
 return {doc,header,calls,renamed,api,find,dialog,form,input,status,save,cancel,setHandler(fn){handler=fn;},submit:()=>form.onsubmit({preventDefault(){}})};
}
test('brak rozmowy blokuje działania, eksport ma wyłącznie stałe lokalne trasy',()=>{
 const h=harness(),toggle=h.header.children[0].children[0];assert(toggle.disabled);
 const links=walk(h.header).filter(n=>n.tagName==='a');assert(links.every(n=>!n.href&&n.tabIndex===-1));
 h.api.setCurrent('id /?#','Nazwa');assert.equal(toggle.disabled,false);
 assert.equal(links[0].href,'/api/v1/conversations/id%20%2F%3F%23/export?format=md');assert.equal(links[1].href,'/api/v1/conversations/id%20%2F%3F%23/export?format=json');assert.equal(h.calls.length,0);
 h.api.clear();assert(links.every(n=>!n.href));assert(toggle.disabled);
});
test('dialog nazwy wysyła PATCH po zapisie, odświeża listę i przywraca fokus',async()=>{
 const h=harness();h.api.setCurrent('cid','Poprzednia');h.find('Zmień nazwę').onclick();assert(h.dialog.open);assert.equal(h.input.value,'Poprzednia');assert(h.input.selected);
 h.input.value='  Nowa nazwa  ';assert.equal(h.calls.length,0);await h.submit();
 assert.equal(JSON.stringify(h.calls),JSON.stringify([['/conversations/cid','PATCH',{title:'Nowa nazwa'}]]));assert.equal(h.dialog.open,false);assert.equal(JSON.stringify(h.renamed),JSON.stringify([['cid','Nowa nazwa']]));assert.equal(h.doc.activeElement,h.header.children[0].children[0]);
});
test('błąd zapisu zachowuje szkic, odblokowuje ponowienie i niczego nie eksportuje',async()=>{
 const h=harness();h.api.setCurrent('cid','Poprzednia');h.find('Zmień nazwę').onclick();h.input.value='Niezapisany szkic';h.setHandler(async()=>{throw Error('Brak połączenia');});await h.submit();
 assert.equal(h.input.value,'Niezapisany szkic');assert(h.dialog.open);assert.equal(h.status.textContent,'Brak połączenia');assert.equal(h.save.disabled,false);assert.equal(h.renamed.length,0);
});
test('puste, za długie i sterujące tytuły nie wysyłają żądań',async()=>{
 const h=harness();h.api.setCurrent('cid','Nazwa');h.find('Zmień nazwę').onclick();
 for(const title of ['   ','x'.repeat(201),'Nazwa\n','Linia\u2028druga','x\u0000']){h.input.value=title;await h.submit();assert.match(h.status.textContent,/1 do 200/);}
 assert.equal(h.calls.length,0);
});
test('zmiana rozmowy i wylogowanie ignorują spóźnione odpowiedzi oraz błędy',async()=>{
 for(const success of [true,false])for(const logout of [true,false]){
  const h=harness();let finish;h.setHandler(()=>new Promise((resolve,reject)=>finish=()=>success?resolve({title:'Stara'}):reject(Error('Stary błąd'))));
  h.api.setCurrent('old','Stara');h.find('Zmień nazwę').onclick();h.input.value='Zmieniona';const pending=h.submit();assert(h.save.disabled);
  if(logout)h.api.clear();else h.api.setCurrent('new','Nowa');finish();await pending;assert.equal(h.renamed.length,0);assert.equal(h.status.textContent,'');assert.equal(h.dialog.open,false);
  h.api.clear();assert.equal(h.input.value,'');
 }
});
test('Escape zamyka listę działań i dialog, bez zmiany rozmowy',()=>{
 const h=harness();h.api.setCurrent('cid','Nazwa');const holder=h.header.children[0],toggle=holder.children[0];toggle.onclick();assert.equal(toggle.attributes['aria-expanded'],'true');let prevented=0;
 holder.listeners.keydown({key:'Escape',preventDefault(){prevented++;}});assert.equal(toggle.attributes['aria-expanded'],'false');assert.equal(h.doc.activeElement,toggle);
 h.find('Zmień nazwę').onclick();h.dialog.listeners.cancel({preventDefault(){prevented++;}});assert.equal(h.dialog.open,false);assert.equal(h.calls.length,0);assert.equal(prevented,2);
});

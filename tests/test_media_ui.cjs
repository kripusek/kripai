const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/media.js'),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){
 const elements={};
 function element(){return {value:'',children:[],hidden:false,disabled:false,files:[],addEventListener(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},append(child){this.children.push(child);},replaceChildren(){this.children=[];},removeAttribute(name){delete this[name];}};}
 const get=id=>elements[id]||(elements[id]=element());
 const calls=[];const row={id:'file-id',filename:'plik.png',pages:1,current_page:1,text_layer:'Tekst z pliku'};
 const context={document:{getElementById:get,createElement:element},window:{addEventListener(){}},Blob,AbortController,crypto:{randomUUID:()=> 'job-id'},confirm:()=>true,
  fetch:async(url,options)=>{calls.push([url,options]);return {ok:true,status:200,json:async()=>url==='/api/v1/files'?{items:[row]}:row};}};
 vm.createContext(context);vm.runInContext(source,context);
 const api=context.window.KripMedia;api.configure({csrf:()=> 'token',notice(){}});
 return {elements,context,calls,api,row,get};
}
test('lista po zakończeniu operacji pozwala wybrać plik; wstawianie nie wysyła wiadomości',async()=>{
 const h=harness();h.get('filesButton').onclick();await tick();
 assert.equal(h.get('fileList').children[0].disabled,false);
 h.get('fileList').children[0].onclick();await tick();
 assert.equal(h.get('fileResult').value,'Tekst z pliku');
 h.get('fileInsert').onclick();assert.match(h.get('prompt').value,/niezaufana treść/);
 assert(!h.calls.some(([url])=>url.includes('/messages')));
});
test('za duży upload nie jest wysyłany; Gaming blokuje przetwarzanie',()=>{
 const h=harness();h.get('filePick').files=[{size:8*1024*1024+1}];h.get('filePick').onchange();
 assert.equal(h.calls.length,0);assert.match(h.get('fileNotice').textContent,/8 MiB/);
 h.api.setBlocked(true);h.get('filePick').files=[new Blob(['test'])];h.get('filePick').onchange();
 assert.equal(h.calls.length,0);assert.equal(h.get('filePick').disabled,true);
});
test('wylogowanie usuwa prywatny podgląd i ignoruje spóźnioną odpowiedź',async()=>{
 const h=harness();let resolve;
 h.context.fetch=(url,options)=>url.endsWith('/cancel')?Promise.resolve({ok:true,status:204}):new Promise(r=>resolve=r);
 h.get('filesButton').onclick();h.api.hide();
 resolve({ok:true,status:200,json:async()=>({items:[h.row]})});await tick();
 assert.equal(h.get('fileList').children.length,0);assert.equal(h.get('filesDialog').open,false);
 assert.equal(h.get('fileResult').value,'');assert.equal(h.get('filePreview').src,undefined);
});
test('anulowanie analizy nie wstawia późnego wyniku',async()=>{
 const h=harness();h.get('filesButton').onclick();await tick();h.get('fileList').children[0].onclick();await tick();
 let resolve;h.context.fetch=(url,options)=>{h.calls.push([url,options]);return url.endsWith('/cancel')?Promise.resolve({ok:true,status:204}):new Promise(r=>resolve=r);};
 h.get('fileAsk').onclick();h.api.stop();resolve({ok:true,status:200,json:async()=>({text:'spóźniony wynik'})});await tick();
 assert.equal(h.get('fileResult').value,'Tekst z pliku');assert(h.calls.some(([url])=>url.endsWith('/cancel')));
});
test('błąd API odblokowuje panel i pokazuje opis',async()=>{
 const h=harness();h.context.fetch=async()=>({ok:false,status:503,json:async()=>({error:{code:'vision_failed'}})});
 h.get('filesButton').onclick();await tick();assert.equal(h.get('filePick').disabled,false);assert.match(h.get('fileNotice').textContent,/Model obrazu/);
});

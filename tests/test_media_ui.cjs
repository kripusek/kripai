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

test('wynik pamięci obrazów otwiera wskazaną stronę przez istniejący dekoder bez VLM ani wiadomości',async()=>{
 const h=harness();h.row.pages=3;
 const original=h.context.fetch;h.context.fetch=async(url,options)=>{
  if(url.endsWith('/page')){h.calls.push([url,options]);return {ok:true,status:200,json:async()=>({...h.row,current_page:2})};}
  return original(url,options);
 };
 await h.api.openPage('file-id',2);
 assert.equal(h.get('filesDialog').open,true);assert.equal(h.get('filePage').value,2);assert.equal(h.get('filePreview').hidden,false);
 const [,options]=h.calls.find(([u])=>u.endsWith('/page'));assert.equal(options.headers['X-CSRF-Token'],'token');assert.deepEqual(JSON.parse(options.body),{page:2});
 assert(!h.calls.some(([u])=>/analyze|messages/.test(u)));
});

test('otwarcie wyniku respektuje Gaming, granice stron i błąd uprawnień',async()=>{
 const h=harness();h.api.setBlocked(true);await h.api.openPage('file-id',1);assert.equal(h.calls.length,0);
 h.api.setBlocked(false);await h.api.openPage('file-id',0);assert.equal(h.calls.length,0);
 h.context.fetch=async()=>({ok:false,status:404,json:async()=>({error:{code:'file_not_found'}})});await h.api.openPage('other',1);
 assert.equal(h.get('filePreview').src,undefined);assert.match(h.get('fileNotice').textContent,/usunięty/);assert.equal(h.get('fileRender').disabled,true);
});

test('wylogowanie podczas otwierania strony nie przywraca starego podglądu',async()=>{
 const h=harness();let release;h.context.fetch=(url)=>url.endsWith('/cancel')?Promise.resolve({ok:true,status:204}):new Promise(resolve=>release=resolve);
 const pending=h.api.openPage('file-id',1);h.api.hide();release({ok:true,status:200,json:async()=>h.row});await pending;
 assert.equal(h.get('filePreview').src,undefined);assert.equal(h.get('fileName').textContent,'');assert.equal(h.get('filesDialog').open,false);
});


function transport(h){
 const saved=new Map();h.context.crypto=require('node:crypto').webcrypto;
 h.context.sessionStorage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/uploads.js'),'utf8'),h.context);
 return saved;
}
test('panel używa rzeczywistego transportu fragmentów, pokazuje postęp i wstrzymuje bez późnego podglądu',async()=>{
 const h=harness(),saved=transport(h);let state,release,started;
 const chunkStarted=new Promise(r=>started=r);
 h.context.fetch=async(url,options={})=>{
  h.calls.push([url,options]);let data;
  if(url==='/api/v1/media/uploads'&&options.method==='POST'){
   const body=JSON.parse(options.body);state={...body,filename:body.name,received:0,chunk_size:524288,expires_at:Date.now()/1000+3600,status:'uploading',attachment_id:null};data=state;
  }else if(url.includes('/chunks?')){started();return new Promise(r=>release=()=>r({ok:true,status:200,json:async()=>({...state,received:state.size})}));}
  else if(url.endsWith('/cancel'))return {ok:true,status:204};
  return {ok:true,status:200,json:async()=>data};
 };
 const file=new Blob(['image bytes']);file.name='x.png';h.get('filePick').files=[file];h.get('filePick').onchange();await chunkStarted;
 assert.match(h.get('fileNotice').textContent,/Wysyłanie pliku: 0%/);assert(h.get('fileUploadsDiscard').disabled);
 h.get('fileCancel').onclick();assert.match(h.get('fileNotice').textContent,/Wstrzymano/);release();await tick();
 assert.equal(h.get('filePreview').src,undefined);assert(saved.get('kripai.uploads.v1'));
 assert(!h.calls.some(([u])=>u.includes('/files?name=')));assert(!h.calls.some(([u])=>u.endsWith('/complete')));
});

test('udane przesłanie transportem kończy plik nową trasą i nie wysyła wiadomości',async()=>{
 const h=harness();transport(h);let state;
 h.context.fetch=async(url,options={})=>{
  h.calls.push([url,options]);let data;
  if(url==='/api/v1/media/uploads'&&options.method==='POST'){
   const body=JSON.parse(options.body);state={...body,filename:body.name,received:0,chunk_size:524288,expires_at:Date.now()/1000+3600,status:'uploading',attachment_id:null};data=state;
  }else if(url.includes('/chunks?'))data=state={...state,received:state.size};
  else if(url.endsWith('/complete'))data={...h.row,id:state.id};
  else data={items:[]};
  return {ok:true,status:200,json:async()=>data};
 };
 const file=new Blob(['image bytes']);file.name='x.png';h.get('filePick').files=[file];h.get('filePick').onchange();
 for(let n=0;n<40&&!h.calls.some(([u])=>u.endsWith('/complete'));n++)await tick();await tick();
 assert(h.calls.some(([u])=>/\/media\/jobs\/[^/]+\/uploads\/[^/]+\/complete$/.test(u)));
 assert(h.get('filePreview').src);assert.equal(h.get('filePick').disabled,false);
 assert(!h.calls.some(([u])=>u.includes('/messages')));
});

test('usuwanie niedokończonych wysyłek czyści zakładki dopiero po udanej kopii i zachowuje gotowy plik',async()=>{
 const h=harness();let cleared=0;h.context.window.KripUploads={clear(){cleared++;}};
 h.get('filesButton').onclick();await tick(); // Lista gotowych plików pozostaje dostępna.
 let fail=true;h.context.fetch=async(url,options)=>{
  h.calls.push([url,options]);return {ok:!fail,status:fail?503:200,json:async()=>fail?{error:{code:'backup_failed'}}:{discarded:2}};
 };
 h.get('fileUploadsDiscard').onclick();await tick();assert.equal(cleared,0);assert.match(h.get('fileNotice').textContent,/Kopia zapasowa/);assert.equal(h.get('fileUploadsDiscard').disabled,false);
 fail=false;h.get('fileUploadsDiscard').onclick();await tick();assert.equal(cleared,1);assert.match(h.get('fileUploads').textContent,/Gotowe pliki zachowano/);
 const call=h.calls.find(([u])=>u==='/api/v1/media/uploads/discard');assert.equal(call[1].method,'POST');assert.equal(call[1].headers['X-CSRF-Token'],'token');
 assert(!h.calls.some(([,o])=>o.method==='DELETE'));assert.equal(h.get('fileList').children.length,1);
});

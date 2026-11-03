const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const source=fs.readFileSync(require('node:path').join(__dirname,'../web/uploads.js'),'utf8');
const JOB='12345678-1234-4234-8234-123456789abc',CHUNK=524288;
const file=(size=CHUNK+53)=>Object.assign(new Blob([Uint8Array.from({length:size},(_,i)=>i%251)]),{name:'zdjęcie.png'});
const ok=value=>({ok:true,status:200,json:async()=>structuredClone(value)});
function harness(shared={}){
 const storage=shared.storage||new Map(),server=shared.server||{row:null,bytes:Buffer.alloc(0),decodes:0};
 const calls=[];let hook=null;
 const context={window:{},Blob,Uint8Array,AbortController,crypto:webcrypto,
  sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  fetch:async(url,options)=>{
   calls.push({url,...options});if(hook){const result=await hook(url,options);if(result)return result;}
   return route(url,options);
  }};
 async function route(url,options){
  if(options.method!=='GET')assert.equal(options.headers['X-CSRF-Token'],'csrf-test');
  if(url==='/api/v1/media/uploads'){
   const body=JSON.parse(options.body);
   if(!server.row)server.row={id:body.id,filename:body.name,size:body.size,sha256:body.sha256,received:0,status:'uploading',attachment_id:null,expires_at:Date.now()/1000+3600,chunk_size:CHUNK};
   assert.equal(body.id,server.row.id);return ok(server.row);
  }
  if(url.includes('/chunks?')){
   const offset=Number(url.split('offset=')[1]),bytes=Buffer.from(await options.body.arrayBuffer());
   assert(bytes.length<=CHUNK);
   if(offset<server.bytes.length)assert.deepEqual(bytes,server.bytes.subarray(offset,offset+bytes.length));
   else{assert.equal(offset,server.bytes.length);server.bytes=Buffer.concat([server.bytes,bytes]);}
   server.row.received=server.bytes.length;return ok(server.row);
  }
  if(url.endsWith('/complete')){server.decodes++;server.row.status='completed';server.row.attachment_id=server.row.id;return ok({id:server.row.id,filename:server.row.filename});}
  if(url.startsWith('/api/v1/files/'))return ok({id:server.row.id,filename:server.row.filename});
  return server.row?ok(server.row):{ok:false,status:404};
 }
 vm.createContext(context);vm.runInContext(source,context);
 return {api:context.window.KripUploads,context,storage,server,calls,route,hook(value){hook=value;},options:extra=>({csrf:()=> 'csrf-test',job:JOB,...extra})};
}
test('rzeczywisty SHA256, fragmenty i CSRF; w pamięci sesji wyłącznie ograniczone metadane',async()=>{
 const h=harness(),input=file(),progress=[];const result=await h.api.send(input,h.options({onProgress:(a,b)=>progress.push([a,b])}));
 assert.equal(result.id,h.server.row.id);assert.deepEqual(h.server.bytes,Buffer.from(await input.arrayBuffer()));
 assert.equal(h.server.row.sha256,Buffer.from(await webcrypto.subtle.digest('SHA-256',await input.arrayBuffer())).toString('hex'));
 assert.deepEqual(progress.map(p=>p[0]),[0,CHUNK,input.size]);
 const saved=JSON.parse([...h.storage.values()][0]);assert.deepEqual(Object.keys(saved[0]).sort(),['id','name','sha256','size']);
 assert(!h.calls.some(c=>c.url.includes('/messages')));
});
test('ponowne wybranie po przeładowaniu wznawia od potwierdzonego offsetu',async()=>{
 const h=harness(),controller=new AbortController(),input=file();
 await assert.rejects(h.api.send(input,h.options({signal:controller.signal,onProgress:n=>{if(n===CHUNK)controller.abort();}})),{name:'AbortError'});
 const next=harness(h);await next.api.send(input,next.options());
 assert.equal(next.calls.filter(c=>c.method==='PUT')[0].url.split('offset=')[1],String(CHUNK));
 assert.deepEqual(next.server.bytes,Buffer.from(await input.arrayBuffer()));
});
test('utracona odpowiedź utworzenia zachowuje UUID i odzyskuje stan',async()=>{
 const h=harness();let lost=false;h.hook(async(url,o)=>{if(url==='/api/v1/media/uploads'&&!lost){lost=true;await h.route(url,o);throw new TypeError('lost');}});
 await h.api.send(file(30),h.options());assert.equal(h.calls.filter(c=>c.url==='/api/v1/media/uploads').length,1);assert.equal(h.server.decodes,1);
});
test('utrata żądania i odpowiedzi fragmentu: powtórzenie bez pomijania bajtów',async()=>{
 const h=harness();let step=0;h.hook(async(url,o)=>{if(url.includes('/chunks?offset=0')&&step<2){step++;if(step===2)await h.route(url,o);throw new TypeError('lost');}});
 const input=file();await h.api.send(input,h.options());assert.equal(step,2);assert.deepEqual(h.server.bytes,Buffer.from(await input.arrayBuffer()));
});
test('dokładne powtórzenie fragmentu pozostaje zgodne z protokołem',async()=>{
 const h=harness();let stale=false;h.hook(async(url,o)=>{if(url.includes('/chunks?offset=0')&&!stale){stale=true;await h.route(url,o);return ok({...h.server.row,received:0});}});
 const input=file();await h.api.send(input,h.options());assert.deepEqual(h.server.bytes,Buffer.from(await input.arrayBuffer()));
 assert.equal(h.calls.filter(c=>c.url.includes('/chunks?offset=0')).length,2);
});
test('utrata finalnego potwierdzenia i ponowne wybranie używają gotowego pliku bez drugiej analizy',async()=>{
 const h=harness();let lost=false;h.hook(async(url,o)=>{if(url.endsWith('/complete')&&!lost){lost=true;await h.route(url,o);throw new TypeError('lost');}});
 const input=file(10);await h.api.send(input,h.options());await h.api.send(input,h.options());
 assert.equal(h.server.decodes,1);assert.equal(h.calls.filter(c=>c.url.startsWith('/api/v1/files/')).length,2);
});
test('przerwanie w czasie odczytu/hash i wylogowanie blokują późne zapisy',async()=>{
 for(const logout of [false,true]){
  const h=harness(),controller=new AbortController();let release;const input=file(2);input.arrayBuffer=()=>new Promise(resolve=>release=resolve);
  const sending=h.api.send(input,h.options({signal:controller.signal}));
  if(logout)h.api.clear();else controller.abort();release(new Uint8Array([1,2]).buffer);
  await assert.rejects(sending,{name:'AbortError'});assert.equal(h.calls.length,0);assert.equal(h.storage.size,0);
 }
 const h=harness();let release;h.hook(async(url,o)=>{if(url.endsWith('/complete'))return new Promise(resolve=>release=()=>resolve(ok({id:h.server.row.id,filename:'plik.png'})));});
 const sending=h.api.send(file(2),h.options());while(!release)await new Promise(r=>setImmediate(r));
 h.api.clear();release();await assert.rejects(sending,{name:'AbortError'});assert.equal(h.storage.size,0);
});
test('niepoprawne metadane protokołu nigdy nie przesuwają offsetu',async()=>{
 for(const mutation of [{received:-1},{received:1.5},{received:100},{chunk_size:1},{sha256:'a'.repeat(64)},{status:'completed',attachment_id:'../../x'},{id:'../../x'}]){
  const h=harness();h.hook(async(url,o)=>url==='/api/v1/media/uploads'?ok({...await (await h.route(url,o)).json(),...mutation}):null);
  await assert.rejects(h.api.send(file(4),h.options()),/Nieprawidłowa odpowiedź/);assert.equal(h.calls.length,1);
 }
});
test('401 i 403 nie są ponawiane ani traktowane jako sukces; awaria ma skończoną liczbę prób',async()=>{
 for(const code of [401,403]){const h=harness();h.hook(async()=>({ok:false,status:code}));await assert.rejects(h.api.send(file(4),h.options()),error=>error.status===code);assert.equal(h.calls.length,1);}
 const h=harness();h.hook(async()=>{throw new TypeError('offline');});await assert.rejects(h.api.send(file(4),h.options()),/Utracono połączenie/);assert.equal(h.calls.length,4);
});
test('brak kryptografii i przekroczony limit kończą się przed zapisem do serwera',async()=>{
 const h=harness();h.context.crypto={};await assert.rejects(h.api.send(file(1),h.options()),/Przeglądarka/);
 await assert.rejects(h.api.send({size:8*1024*1024+1},h.options()),/8 MiB/);assert.equal(h.calls.length,0);
});
test('nazwa jest normalizowana jak w API, a za długa nazwa jest jawnie odrzucona',async()=>{
 const h=harness(),input=file(2);input.name=' C:\\katalog\\plik.png ';await h.api.send(input,h.options());assert.equal(h.server.row.filename,'plik.png');
 const next=harness(),long=file(2);long.name='x'.repeat(181);await assert.rejects(next.api.send(long,next.options()),/180 znaków/);assert.equal(next.calls.length,0);
});
test('wygasłe potwierdzenie jest usuwane, kolejne wybranie tworzy nowe UUID',async()=>{
 const h=harness(),input=file(2);await h.api.send(input,h.options());const old=h.server.row.id;
 h.hook(async()=>({ok:false,status:410}));await assert.rejects(h.api.send(input,h.options()),e=>e.status===410);
 assert.deepEqual(JSON.parse([...h.storage.values()][0]),[]);h.hook(null);h.server.row=null;h.server.bytes=Buffer.alloc(0);
 await h.api.send(input,h.options());assert.notEqual(h.server.row.id,old);
});
test('zerwane ciało odpowiedzi finalnej i odczytu metadanych jest odzyskiwane',async()=>{
 const h=harness();let final=false,receipt=false;
 h.hook(async(url,o)=>{
  if(url.endsWith('/complete')&&!final){final=true;await h.route(url,o);return {ok:true,status:200,json:async()=>{throw new TypeError('stream lost');}};}
  if(url.startsWith('/api/v1/files/')&&!receipt){receipt=true;throw new TypeError('lost');}
 });
 await h.api.send(file(2),h.options());assert.equal(h.server.decodes,1);assert.equal(receipt,true);
});
test('znane kody błędów wskazują konkretną czynność po polsku i zachowują status oraz retryability',async()=>{
 for(const [code,status,message] of [
  ['upload_quota',409,/3 niedokończone.*Usuń niedokończone wysyłki/],
  ['upload_digest_mismatch',422,/Suma kontrolna.*Usuń.*wybierz plik ponownie/],
  ['upload_offset_conflict',409,/pozycja fragmentu.*wznowić/],
  ['upload_incomplete',409,/całego pliku.*dokończyć/],
  ['upload_expired',410,/wygasło.*ponownie/],
  ['upload_file_gone',410,/usunięty lub wygasł.*ponownie/],
  ['file_quota',409,/limit liczby plików lub miejsca.*Usuń/],
  ['gaming_mode',409,/Gaming.*Normalny/],
  ['backup_failed',503,/kopii danych.*miejsce na dysku/]
 ]){
  const h=harness();h.hook(async()=>({ok:false,status,json:async()=>({error:{code,message:'SERVER_PRIVATE_TEXT',data:'SECRET'}})}));
  await assert.rejects(h.api.send(file(2),h.options()),error=>{assert.equal(error.status,status);assert.equal(error.retryable,status>=500);assert.match(error.message,message);assert(!/SERVER_PRIVATE_TEXT|SECRET/.test(error.message));return true;});
  assert.equal(h.calls.length,status>=500?4:1);
 }
});
test('nieznany kod i dowolny opis serwera nie trafiają do komunikatu, a 401 ma pierwszeństwo',async()=>{
 for(const [code,status] of [['__proto__',422],['PRIVATE_CODE',422],['upload_quota',401]]){
  const h=harness();h.hook(async()=>({ok:false,status,json:async()=>({error:{code,message:'PRIVATE_MESSAGE'}})}));
  await assert.rejects(h.api.send(file(2),h.options()),error=>{assert.equal(error.status,status);assert.equal(error.message,status===401?'Sesja wygasła. Zaloguj się ponownie.':'Nie udało się przesłać pliku.');return true;});
  assert.equal(h.calls.length,1);
 }
});

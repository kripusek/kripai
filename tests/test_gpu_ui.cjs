const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function harness(api){const doc=document(),events={};doc.addEventListener=(name,fn)=>events[name]=fn;const ctx={document:doc,window:{},api};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/gpu.js'),'utf8'),ctx);events.DOMContentLoaded();return {doc,api:ctx.window.KripGpu};}
function data(){return {available:true,devices:[{index:0,name:'<img onerror=bad>',used_mib:7000,total_mib:8192,free_mib:1000}],context_tokens:4096,output_tokens_per_segment:2048,sampled_at:1700000000};}
test('pomiar karty jest tekstem, pasek ma prawdziwy zakres i kontekst',async()=>{
 const calls=[],h=harness(async path=>{calls.push(path);return data();});await h.api.refresh();
 const box=h.doc.getElementById('gpuMetrics'),nodes=walk(box);assert.match(box.textContent,/7000 \/ 8192/);assert.match(box.textContent,/4096/);
 assert(!nodes.some(n=>n.tagName==='img'));const bar=nodes.find(n=>n.tagName==='progress');assert.equal(bar.max,8192);assert.equal(bar.value,7000);
 assert.deepEqual(calls,['/system/gpu']);assert.equal(h.doc.getElementById('gpuRefresh').disabled,false);
});
test('brak sterownika i zły pomiar nie są przedstawiane jako zero wolnej pamięci',async()=>{
 const h=harness(async()=>({available:false,error:'gpu_probe_unavailable'}));await h.api.refresh();assert.match(h.doc.getElementById('gpuMetrics').textContent,/niedostępny/);assert(!walk(h.doc.getElementById('gpuMetrics')).some(n=>n.tagName==='progress'));
 const invalid=data();invalid.devices[0].used_mib=9999;const other=harness(async()=>invalid);await other.api.refresh();assert.match(other.doc.getElementById('gpuMetrics').textContent,/Nie udało/);
});
test('wylogowanie czyści pomiar i odrzuca spóźnioną odpowiedź',async()=>{
 let resolve;const pending=new Promise(r=>resolve=r),h=harness(()=>pending);const done=h.api.refresh();h.doc.getElementById('settings').open=true;h.api.clear();resolve(data());await done;
 assert.equal(h.doc.getElementById('gpuMetrics').textContent,'');assert.equal(h.doc.getElementById('settings').open,false);assert.equal(h.doc.getElementById('gpuRefresh').disabled,false);
});

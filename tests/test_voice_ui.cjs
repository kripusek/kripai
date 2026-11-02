// Testy rzeczywistego kodu UI bez mikrofonu i głośników. Node jest tylko narzędziem QA.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {encodeWav}=require('../web/pcm.js');
const source=fs.readFileSync(path.join(__dirname,'../web/voice.js'),'utf8');

function harness() {
  const elements=Object.fromEntries(['record','stopVoice','voiceLanguage','prompt'].map(id=>[id,{value:id==='voiceLanguage'?'pl':'',setAttribute(){},focus(){}}]));
  const messages=[],calls=[];
  const context={document:{getElementById:id=>elements[id],addEventListener(){}},
    window:{addEventListener(){},AudioWorkletNode:function(){}}, navigator:{mediaDevices:{}},
    fetch:async(...args)=>{calls.push(args);return {ok:true,json:async()=>({text:'spóźniona transkrypcja'}),blob:async()=>({})};},
    crypto:{randomUUID:()=> 'test-job'},AbortController,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    setTimeout,clearTimeout,console,encodeWav};
  vm.createContext(context);vm.runInContext(source,context);
  context.window.KripVoice.configure({csrf:()=> 'test-token',notice:text=>messages.push(text)});
  return {context,elements,messages,calls,voice:context.window.KripVoice};
}

test('PCM ma właściwy nagłówek, długość, clipping i brak NaN',()=>{
  const samples=new Float32Array(4000);samples.set([-2,2,NaN]);
  const wav=new DataView(encodeWav(samples));
  assert.equal(wav.byteLength,8044);assert.equal(wav.getUint32(24,true),16000);
  assert.equal(wav.getInt16(44,true),-32768);assert.equal(wav.getInt16(46,true),32767);assert.equal(wav.getInt16(48,true),0);
  assert.throws(()=>encodeWav(new Float32Array(3999)));
  assert.throws(()=>encodeWav(new Float32Array(480001)));
});

test('anulowanie podczas zgody na mikrofon zamyka spóźniony strumień',async()=>{
  const h=harness();let resolve,stopped=0;
  h.context.navigator.mediaDevices.getUserMedia=()=>new Promise(r=>resolve=r);
  const pending=h.elements.record.onclick();assert.equal(h.elements.stopVoice.hidden,false);
  h.voice.stop();resolve({getTracks:()=>[{stop:()=>stopped++}]});await pending;
  assert.equal(stopped,1);assert.equal(h.elements.stopVoice.hidden,true);assert.equal(h.calls.length,0);
});

test('odmowa dostępu do mikrofonu daje czytelny błąd i pozwala spróbować ponownie',async()=>{
  const h=harness();h.context.navigator.mediaDevices.getUserMedia=async()=>{throw {name:'NotAllowedError'};};
  await h.elements.record.onclick();assert.match(h.messages.at(-1),/Zezwól/);assert.equal(h.elements.record.disabled,false);
});

test('błąd uruchomienia AudioContext nie pozostawia otwartego mikrofonu',async()=>{
  const h=harness();let stopped=0;
  h.context.navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop:()=>stopped++}]});
  h.context.AudioContext=function(){throw Error('AudioContext niedostępny');};
  await h.elements.record.onclick();assert.equal(stopped,1);assert.equal(h.elements.stopVoice.hidden,true);
});

test('anulowanie opóźnionego TTS wysyła cancel i nie odtwarza wyniku',async()=>{
  const h=harness();let resolve,played=0;
  h.context.fetch=(url,options)=>{
    h.calls.push([url,options]);
    if(url.endsWith('/cancel'))return Promise.resolve({ok:true});
    return new Promise(r=>resolve=r);
  };
  h.context.Audio=function(){played++;};
  const pending=h.voice.speak('Zażółć gęślą jaźń.');
  h.voice.stop();resolve({ok:true,blob:async()=>({})});await pending;
  assert.equal(played,0);assert(h.calls.some(([url])=>url.endsWith('/cancel')));
});

test('odczyt całego długiego tekstu jest porcjowany, bez cichego ucięcia',async()=>{
  const h=harness();let played=0;
  h.context.Audio=function(){this.pause=()=>{};this.removeAttribute=()=>{};this.load=()=>{};
    this.play=()=>{played++;queueMicrotask(()=>this.onended());return Promise.resolve();};};
  await h.voice.speak('a'.repeat(2500));
  const parts=h.calls.filter(([url])=>url.includes('/speak')).map(([,options])=>JSON.parse(options.body).text);
  assert.deepEqual(parts.map(x=>x.length),[1200,1200,100]);assert.equal(played,3);
});

test('Gaming blokuje nagrywanie i odczyt',async()=>{
  const h=harness();h.voice.setBlocked(true);await h.elements.record.onclick();await h.voice.speak('test');
  assert.equal(h.elements.record.disabled,true);assert.equal(h.calls.length,0);
  h.voice.setBlocked(false);assert.equal(h.elements.record.disabled,false);
});

test('worklet kończy nagrywanie dokładnie po limicie i nie kopiuje dalszych próbek',()=>{
  let Processor;const posted=[];
  const context={sampleRate:16000,AudioWorkletProcessor:class {constructor(){this.port={postMessage:value=>posted.push(value)};}},
    registerProcessor:(name,value)=>Processor=value};
  vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/recorder-worklet.js'),'utf8'),context);
  const recorder=new Processor();
  for(let n=0;n<4000;n++)recorder.process([[new Float32Array(128)]]);
  assert.equal(posted.filter(x=>x!=='limit').reduce((sum,x)=>sum+x.length,0),480000);
  assert.equal(posted.filter(x=>x==='limit').length,1);
});

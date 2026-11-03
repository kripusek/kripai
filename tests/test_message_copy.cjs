const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {document,Node}=require('./dom.cjs');
const source=fs.readFileSync(path.join(__dirname,'../web/message-copy.js'),'utf8');
function harness(){
 const doc=document(),copied=[],notices=[],queue=[],ctx={document:doc,window:{},navigator:{clipboard:{writeText:async text=>{copied.push(text);const next=queue.shift();if(next)return await next();}}},fetch(){throw Error('Nie wolno używać sieci.');}};
 vm.createContext(ctx);vm.runInContext(source,ctx);const api=ctx.window.KripMessageCopy;api.configure({notice:text=>notices.push(text)});
 const attach=(getText=()=> 'Treść',container=new Node('article'))=>({container,button:api.attach(container,{getText})});
 return {api,doc,ctx,copied,notices,queue,attach};
}
test('jawny klik kopiuje całe źródło user lub assistant, bez automatu i zmiany fokusu/szkicu',async()=>{
 const h=harness(),focus=new Node('textarea');focus.value='NIEWYSŁANY SZKIC';h.doc.activeElement=focus;
 for(const text of ['Wiadomość użytkownika','**Odpowiedź** [W1]\n\n```js\nconst x=1;\n```']){
  const before=h.copied.length,{button}=h.attach(()=>text);assert.equal(h.copied.length,before);assert.equal(button.textContent,'Kopiuj całą wiadomość');await button.onclick();assert.equal(h.copied.at(-1),text);
 }
 assert.equal(h.doc.activeElement,focus);assert.equal(focus.value,'NIEWYSŁANY SZKIC');assert.equal(h.notices.at(-1),'Skopiowano całą wiadomość.');
});
test('duża wiadomość Unicode/Markdown nie jest skracana ani zamieniana na HTML',async()=>{
 const h=harness(),text='# Zażółć 🐈\n'+('**źródło**\n```html\n<img onerror=bad()>\n```\n'.repeat(30000)),{button,container}=h.attach(()=>text);
 await button.onclick();assert.equal(h.copied[0],text);assert.equal(container.children.length,1);assert(!container.textContent.includes('<img'));
});
test('źródło jest czytane w chwili kliknięcia i ma najnowszy tekst streamingu',async()=>{
 const h=harness();let text='Początek',reads=0;const {button}=h.attach(()=>{reads++;return text;});assert.equal(reads,0);text+=' i dalszy ciąg';await button.onclick();text+=' zakończony';await button.onclick();assert.deepEqual(h.copied,['Początek i dalszy ciąg','Początek i dalszy ciąg zakończony']);
});
test('Promise denied daje statyczny komunikat i umożliwia ponowienie',async()=>{
 const h=harness(),{button}=h.attach();h.queue.push(async()=>{throw Error('PRIVATE_BROWSER_DETAIL');});await button.onclick();assert.match(h.notices[0],/Nie udało się skopiować.*ręcznie/);assert(!h.notices[0].includes('PRIVATE'));
 await button.onclick();assert.equal(h.copied.length,2);assert.equal(h.notices.at(-1),'Skopiowano całą wiadomość.');
});
test('brak API schowka jest uczciwie zgłaszany bez fallbacku',async()=>{
 const h=harness();h.ctx.navigator={};h.doc.execCommand=()=>{throw Error('Zabroniony fallback');};const {button}=h.attach();await button.onclick();assert.match(h.notices[0],/nie udostępnia kopiowania.*ręcznie/);assert.equal(h.copied.length,0);
});
test('powtórny klik podczas oczekiwania jest blokowany, aria-disabled zachowuje fokus',async()=>{
 const h=harness(),first=h.attach().button,second=h.attach().button;h.doc.activeElement=first;let release;h.queue.push(()=>new Promise(resolve=>release=resolve));const waiting=first.onclick();
 assert.equal(first.attributes['aria-disabled'],'true');assert.equal(first.disabled,false);await first.onclick();await second.onclick();assert.equal(h.copied.length,1);assert.equal(h.doc.activeElement,first);release();await waiting;assert.equal(first.attributes['aria-disabled'],'false');await first.onclick();assert.equal(h.copied.length,2);
});
test('clear po wylogowaniu/zmianie rozmowy odrzuca późny sukces i odmowę oraz stare kliknięcia',async()=>{
 for(const reject of [false,true]){
  const h=harness(),{button}=h.attach();let release;h.queue.push(()=>new Promise((resolve,fail)=>release=()=>reject?fail(Error('denied')):resolve()));const waiting=button.onclick();h.api.clear();release();await waiting;assert.equal(h.notices.length,0);assert(button.disabled);await button.onclick();assert.equal(h.copied.length,1);
 }
});
test('attach jest idempotentne i aktualizuje getText także po clear',async()=>{
 const h=harness(),{button,container}=h.attach(()=> 'stare');assert.equal(h.attach(()=> 'nowe',container).button,button);assert.equal(container.children.length,1);await button.onclick();assert.equal(h.copied[0],'nowe');h.api.clear();assert.equal(h.attach(()=> 'po zmianie',container).button,button);assert.equal(container.children.length,1);await button.onclick();assert.equal(h.copied[1],'po zmianie');
});
test('pusty tekst, błędny typ i wyjątek getText nie powodują zapisu do schowka',async()=>{
 const h=harness();for(const callback of [()=>'',()=>null,()=>{throw Error('PRIVATE_TEXT');}]){await h.attach(callback).button.onclick();}assert.equal(h.copied.length,0);assert.match(h.notices[0],/nie zawiera jeszcze tekstu/);assert(!h.notices.some(text=>text.includes('PRIVATE')));assert.equal(h.api.attach(new Node(),{}),null);
});
test('stara obietnica nie odblokowuje nowej operacji po clear',async()=>{
 const h=harness(),old=h.attach().button;let finishOld,finishNew;h.queue.push(()=>new Promise(r=>finishOld=r));const first=old.onclick();h.api.clear();const next=h.attach(()=> 'nowy tekst').button;h.queue.push(()=>new Promise(r=>finishNew=r));const second=next.onclick();finishOld();await first;assert.equal(h.notices.length,0);assert.equal(next.attributes['aria-disabled'],'true');await next.onclick();assert.equal(h.copied.length,2);finishNew();await second;assert.equal(h.notices.length,1);
});

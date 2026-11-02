const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
test('plus otwiera menu, Escape i klik poza zamykają; uprawnienia pozostają jawne',()=>{
 const doc=document(),events={};doc.addEventListener=(name,fn)=>events[name]=fn;
 const menu=doc.getElementById('composerMenu'),button=doc.getElementById('composerPlus');menu.hidden=true;menu.contains=n=>walk(menu).includes(n);button.contains=n=>n===button;
 const ctx={document:doc,window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/composer-menu.js'),'utf8'),ctx);events.DOMContentLoaded();
 button.onclick();assert.equal(menu.hidden,false);assert.equal(button.attributes['aria-expanded'],'true');
 events.keydown({key:'Escape'});assert.equal(menu.hidden,true);assert.equal(button.attributes['aria-expanded'],'false');
 button.onclick();events.click({target:{}});assert.equal(menu.hidden,true);
 doc.getElementById('allowWeb').checked=true;doc.getElementById('allowWeb').listeners.change();assert.equal(doc.getElementById('enabledTools').textContent,'Internet');
 let opened=false;doc.getElementById('integrationsDialog').showModal=()=>opened=true;doc.getElementById('menuIntegrations').onclick();assert(opened);assert(menu.hidden);
});

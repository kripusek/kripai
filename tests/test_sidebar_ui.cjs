const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,walk}=require('./dom.cjs');
function harness(mobile=true){
 const doc=document(),events={},focused=[],media={matches:mobile,addEventListener(name,fn){this.change=fn;}};doc.addEventListener=(name,fn)=>events[name]=fn;doc.querySelector=()=>null;
 const ids=['sidebar','sidebarToggle','sidebarClose','sidebarBackdrop','chatMain','workspace','prompt','historyItem','settingsItem'];
 for(const id of ids){const node=doc.getElementById(id);node.id=id;node.focus=()=>{doc.activeElement=node;focused.push(id);};node.getClientRects=()=>node.hidden?[]:[{}];node.tabIndex=0;}
 const side=doc.getElementById('sidebar');side.append(...['sidebarClose','historyItem','settingsItem'].map(id=>doc.getElementById(id)));side.contains=node=>walk(side).includes(node);side.querySelectorAll=()=>side.children;
 let menuClosed=0;const ctx={document:doc,window:{matchMedia:()=>media,KripMenu:{close(){menuClosed++;}}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/sidebar.js'),'utf8'),ctx);events.DOMContentLoaded();
 function key(key,shiftKey=false){const e={key,shiftKey,preventDefault(){this.prevented=true;}};events.keydown(e);return e;}
 return {doc,media,focused,key,api:ctx.window.KripSidebar,menuClosed:()=>menuClosed};
}
test('mobilna historia domyślnie zamknięta, Escape i tło przywracają fokus',()=>{
 const h=harness(),d=h.doc;assert.equal(d.getElementById('sidebar').hidden,true);d.getElementById('sidebarToggle').onclick();
 assert.equal(d.getElementById('sidebar').hidden,false);assert.equal(d.getElementById('chatMain').inert,true);assert.equal(d.getElementById('sidebar').attributes['aria-modal'],'true');assert.equal(h.menuClosed(),1);
 assert.equal(d.activeElement.id,'sidebarClose');assert(h.key('Escape').prevented);assert.equal(d.getElementById('sidebar').hidden,true);assert.equal(d.activeElement.id,'sidebarToggle');
 d.getElementById('sidebarToggle').onclick();d.getElementById('sidebarBackdrop').onclick();assert.equal(d.getElementById('chatMain').inert,false);
});
test('Tab pozostaje w otwartej historii',()=>{
 const h=harness(),d=h.doc;d.getElementById('sidebarToggle').onclick();assert(h.key('Tab',true).prevented);assert.equal(d.activeElement.id,'settingsItem');assert(h.key('Tab').prevented);assert.equal(d.activeElement.id,'sidebarClose');
 d.activeElement=d.getElementById('prompt');h.key('Tab');assert.equal(d.activeElement.id,'sidebarClose');
});
test('wybór rozmowy zamyka historię, modal zachowuje własny fokus',()=>{
 const h=harness(),d=h.doc;d.getElementById('sidebarToggle').onclick();const item=d.getElementById('historyItem');item.closest=()=>item;d.getElementById('sidebar').listeners.click({target:item});assert.equal(d.activeElement.id,'prompt');assert.equal(d.getElementById('sidebar').hidden,true);
 d.getElementById('sidebarToggle').onclick();d.querySelector=()=>({open:true});const before=d.activeElement;d.getElementById('sidebar').listeners.click({target:item});assert.equal(d.activeElement,before);
});
test('zmiana rozmiaru i zamknięcie po wylogowaniu resetują stan',()=>{
 const h=harness(),d=h.doc;d.getElementById('sidebarToggle').onclick();h.media.matches=false;h.media.change();assert.equal(d.getElementById('sidebar').hidden,false);assert.equal(d.getElementById('chatMain').inert,false);assert(!('role' in d.getElementById('sidebar').attributes));
 h.media.matches=true;h.media.change();d.getElementById('sidebarToggle').onclick();h.api.close();assert.equal(d.getElementById('sidebar').hidden,true);assert.equal(d.getElementById('sidebarToggle').attributes['aria-expanded'],'false');
});

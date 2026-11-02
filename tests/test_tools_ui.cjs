const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,Node,walk}=require('./dom.cjs');
function harness(){const doc=document(),ctx={document:doc,window:{},URL};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/tools.js'),'utf8'),ctx);return {doc,api:ctx.window.KripTools};}
test('internet i GitHub domyślnie wyłączone, przełączniki niezależne i czyszczone',()=>{
 const h=harness();assert.equal(h.api.permissions().allow_web,false);assert.equal(h.api.permissions().allow_github,false);
 h.doc.getElementById('allowGithub').checked=true;assert.equal(h.api.permissions().allow_github,true);assert.equal(h.api.permissions().allow_web,false);
 h.api.clear();assert.equal(h.api.permissions().allow_github,false);
});
test('źródła sieci są tekstem; tylko HTTPS i bez aktywnego HTML',()=>{
 const h=harness(),box=new Node('article'),target=new Node('div');box.append(target);
 h.api.renderSources(target,[{ordinal:1,title:'<img onerror=x>',excerpt:'<script>x</script>',url:'javascript:bad()'},{ordinal:2,title:'Publiczne źródło',text:'tekst',url:'https://example.org/'}]);
 const nodes=walk(box);assert(!nodes.some(n=>['img','script'].includes(n.tagName)));const links=nodes.filter(n=>n.tagName==='a');assert.equal(links.length,1);assert.equal(links[0].rel,'noopener noreferrer');
 h.api.renderSources(target,[]);assert.equal(walk(box).filter(n=>n.tagName==='details').length,0);
});
test('błędy odczytu mają czytelne opisy',()=>{const h=harness();assert.match(h.api.activity({name:'web_read',state:'tool_resource_not_authorized'}),/bieżącej wiadomości/);assert.match(h.api.activity({name:'web_read',state:'tool_dns_failed'}),/serwera/);});

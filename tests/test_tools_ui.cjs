const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {document,Node,walk}=require('./dom.cjs');
test('błędny site i przekierowanie poza filtr mają czytelne opisy',()=>{assert.match(harness().api.activity({name:'web_search',state:'tool_search_filter_invalid'}),/samą domenę/);assert.match(harness().api.activity({name:'web_read',state:'tool_search_domain_denied'}),/poza dozwolony filtr/);});
function harness(){const doc=document(),ctx={document:doc,window:{},URL};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/tools.js'),'utf8'),ctx);return {doc,api:ctx.window.KripTools};}
test('zmienione zgłoszenie i pomylony numer PR mają czytelne komunikaty',()=>{const h=harness();assert.match(h.api.activity({name:'github_read',state:'github_issue_changed'}),/zmieniło się/);assert.match(h.api.activity({name:'github_read',state:'github_issue_is_pull_request'}),/Ten numer jest PR/);});
test('źródło wyszukiwania nazw MCP zachowuje query i odrzuca obcą trasę',()=>{
 const h=harness(),box=new Node('article'),target=new Node('div');box.append(target);const url='/api/v1/integrations/mcp-files/search?root=12345678-1234-1234-1234-123456789abc&query=g%C4%99%C5%9Bl%C4%85+raport';
 h.api.renderSources(target,[{name:'mcp_files',url},{name:'web_read',url},{name:'mcp_files',url:url+'&write=true'}]);const links=walk(box).filter(n=>n.tagName==='a');assert.equal(links.length,1);assert.equal(links[0].href,url);
});

test('zewnętrzne źródło MCP wymaga nazwy adaptera i nie przyjmuje zmienionej trasy',()=>{
 const h=harness(),box=new Node('article'),target=new Node('div');box.append(target);
 const url='/api/v1/integrations/mcp-files/document?root=12345678-1234-1234-1234-123456789abc&path=za%C5%BC%C3%B3%C5%82%C4%87+test.txt';
 h.api.renderSources(target,[{name:'mcp_files',url},{name:'web_read',url},{name:'mcp_files',url:url+'&command=write'},{name:'mcp_files',url:'/api/v1/private'}]);
 const links=walk(box).filter(n=>n.tagName==='a');assert.equal(links.length,1);assert.equal(links[0].href,url);
});
test('zmiana PR i zablokowany sekret mają czytelny błąd',()=>{const h=harness();assert.match(h.api.activity({name:'github_read',state:'github_reference_changed'}),/PR zmienił/);assert.match(h.api.activity({name:'github_read',state:'github_sensitive_path_denied'}),/poświadczenia/);});
test('MCP domyślnie wyłączone, czyszczone przy wylogowaniu i bezpieczny link lokalnego źródła',()=>{
 const h=harness();assert.equal(h.api.permissions().allow_mcp,false);h.doc.getElementById('allowMcp').checked=true;assert.equal(h.api.permissions().allow_mcp,true);h.api.clear();assert.equal(h.api.permissions().allow_mcp,false);
 const box=new Node('article'),target=new Node('div');box.append(target);
 h.api.renderSources(target,[{ordinal:1,name:'mcp_docs',title:'Dokument',url:'/api/v1/integrations/mcp/document?path=README.md',text:'tekst'},{ordinal:2,name:'web_read',title:'Nieuprawniony',url:'/api/v1/integrations/mcp/document?path=README.md'},{ordinal:3,name:'mcp_docs',title:'Obcy',url:'http://external.invalid/x'}]);
 const links=walk(box).filter(n=>n.tagName==='a');assert.equal(links.length,1);assert.equal(links[0].href,'/api/v1/integrations/mcp/document?path=README.md');
});
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
test('błędy odczytu mają czytelne opisy',()=>{const h=harness();assert.match(h.api.activity({name:'web_read',state:'tool_resource_not_authorized'}),/bieżącej wiadomości/);assert.match(h.api.activity({name:'web_read',state:'tool_dns_failed'}),/serwera/);assert.match(h.api.activity({name:'web_search',state:'reading'}),/Szukam/);assert.match(h.api.activity({name:'web_read',state:'summarizing'}),/Streszczam/);});

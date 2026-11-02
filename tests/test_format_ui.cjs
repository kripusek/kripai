const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {Node,document,walk}=require('./dom.cjs'),marked=require('../web/vendor/marked/marked.umd.js');
function harness(){const copied=[],ctx={document:document(),window:{},marked,URL,navigator:{clipboard:{writeText:async t=>copied.push(t)}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/syntax.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/format.js'),'utf8'),ctx);const root=new Node('div');return {root,ctx,copied,render:t=>ctx.window.KripFormat.render(root,t)};}
test('Markdown: nagłówki, pogrubienie, lista, cytat i tabela',()=>{const h=harness();h.render('### Wynik\n\n**ważne** i *tekst*\n\n- jeden\n- dwa\n\n> cytat\n\n|A|B|\n|-|-|\n|1|2|');for(const tag of ['h3','strong','em','ul','blockquote','table'])assert(walk(h.root).some(n=>n.tagName===tag),tag);});
test('kod HTML jest tekstem, kopiowanie zachowuje zawartość',async()=>{const h=harness();h.render('```html\n<img src="x" onerror="bad()">\n```');await walk(h.root).find(n=>n.tagName==='button').onclick();assert.equal(h.copied[0],'<img src="x" onerror="bad()">');assert(!walk(h.root).some(n=>n.tagName==='img'));});
test('częściowy blok w streamie nie dubluje się po domknięciu',()=>{const h=harness();h.render('```js\nlet x=1;');assert.equal(walk(h.root).filter(n=>n.tagName==='pre').length,1);h.render('```js\nlet x=1;\n```\n\n**Koniec**');assert.equal(walk(h.root).filter(n=>n.tagName==='pre').length,1);assert(walk(h.root).some(n=>n.tagName==='strong'));});
test('XSS, zdalne obrazy i aktywne URL zablokowane',()=>{const h=harness();h.render('<script>alert(1)</script>\n\n<img src="https://evil/x" onerror="bad()">\n\n![spy](https://evil/x)\n\n[x](javascript:alert%281%29)\n\n[ok](https://example.org)');const nodes=walk(h.root);assert(!nodes.some(n=>['script','img','iframe','style'].includes(n.tagName)));assert.equal(nodes.filter(n=>n.tagName==='a').length,1);});
test('wzory ze zrzutu i ułamki renderują MathML',()=>{const h=harness();h.render('$(-\\infty,2]$ i $[5,+\\infty)$\n\n$\\left|x-3.5\\right| \\geq 1.5$\n\n$$\n\\boxed{\\text{Brak odpowiedzi}}\n$$\n\n$\\frac{x_1^2}{\\sqrt{4}}$');const nodes=walk(h.root);for(const tag of ['math','menclose','mfrac','msqrt','msubsup'])assert(nodes.some(n=>n.tagName===tag),tag);assert(h.root.textContent.includes('∞'));assert(h.root.textContent.includes('≥'));});
test('TeX wewnątrz kodu i nieznane polecenia nie są wykonywane',()=>{const h=harness();h.render('`$x^2$`\n\n$\\href{javascript:bad()}{x}$');assert(!walk(h.root).some(n=>n.tagName==='a'||n.tagName==='math'));assert(h.root.textContent.includes('\\href'));h.render('$'+'{'.repeat(100)+'x'+'}'.repeat(100)+'$');assert(walk(h.root).some(n=>n.className.includes('math-fallback')));});
test('odmowa schowka pokazuje ręczne kopiowanie',async()=>{const h=harness();h.ctx.navigator.clipboard.writeText=async()=>{throw Error();};h.render('```\nx\n```');const b=walk(h.root).find(n=>n.tagName==='button');await b.onclick();assert.match(b.textContent,/ręcznie/);});

test('kolory słów, napisów i komentarzy nie zmieniają źródła JS/Python/CSS/JSON/SQL/shell/PS/HTML',async()=>{
 const samples={js:'const x = "return"; // if\nreturn 42;',py:'def foo():\n    # return\n    return "a"',css:'a { color: #fff; width: 12px; }',json:'{"a": true, "n": 42}',sql:"SELECT * FROM t WHERE id = 42; -- test",bash:'if true; then echo "$HOME"; fi',ps1:'if ($true) { return "ok" }',html:'<!-- x -->\n<img src="x" onerror="bad()">'};
 for(const [lang,source] of Object.entries(samples)){
  const h=harness();h.render('```'+lang+'\n'+source+'\n```');
  const code=walk(h.root).find(n=>n.tagName==='code');assert.equal(code.textContent,source,lang);
  assert(walk(code).some(n=>n.className.startsWith('syntax-')),lang);
  assert(!walk(code).some(n=>['img','script'].includes(n.tagName)),lang);
  await walk(h.root).find(n=>n.tagName==='button').onclick();assert.equal(h.copied[0],source);
 }
});
test('napisy i komentarze pozostają pojedynczym tokenem; stream odzyskuje kolorowanie',()=>{
 const h=harness();h.render('```js\nconst x = "return');
 assert(walk(h.root).some(n=>n.className==='syntax-string'&&n.textContent==='"return'));
 h.render('```js\nconst x = "return"; // if true\n```');
 assert.equal(walk(h.root).filter(n=>n.className==='syntax-keyword').length,1);
 assert(walk(h.root).some(n=>n.className==='syntax-comment'&&n.textContent==='// if true'));
 assert.equal(walk(h.root).filter(n=>n.tagName==='pre').length,1);
});
test('nieznany język, duży blok i nadmiar tokenów mają bezpieczny zwykły tekst',()=>{
 for(const [lang,source] of [['unknown','<script>bad()</script>'],['toString','const x=1'],['js','x'.repeat(40001)],['js','x '.repeat(8001)]]){
  const h=harness();h.render('```'+lang+'\n'+source+'\n```');
  const code=walk(h.root).find(n=>n.tagName==='code');assert.equal(code.textContent,source);
  assert(!walk(code).some(n=>n.tagName==='span'));assert(!walk(code).some(n=>n.tagName==='script'));
 }
});
test('awaria lub brak kolorowania pozostawia kod i działający schowek',async()=>{
 for(const highlighter of [undefined,{render(){throw Error('lexer failure');}}]){
  const h=harness();h.ctx.window.KripSyntax=highlighter;h.render('```js\nconst x = 1;\n```');
  assert.equal(walk(h.root).find(n=>n.tagName==='code').textContent,'const x = 1;');
  await walk(h.root).find(n=>n.tagName==='button').onclick();assert.equal(h.copied[0],'const x = 1;');
 }
});

'use strict';
// Parser daje tokeny. Budujemy tylko dozwolone węzły, nigdy HTML z odpowiedzi.
window.KripFormat=(()=>{
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const mn=(tag,...children)=>{const n=document.createElementNS('http://www.w3.org/1998/Math/MathML',tag);for(const c of children)n.append(typeof c==='string'?document.createTextNode(c):c);return n;};
 const symbols={infty:'∞',geq:'≥',ge:'≥',leq:'≤',le:'≤',neq:'≠',times:'×',cdot:'·',pm:'±',approx:'≈',to:'→',Rightarrow:'⇒',in:'∈',notin:'∉',cup:'∪',cap:'∩',pi:'π',alpha:'α',beta:'β',gamma:'γ',delta:'δ',theta:'θ',lambda:'λ',mu:'μ',sigma:'σ',omega:'ω',sum:'∑',int:'∫',ldots:'…'};
 function formula(source,display){
  const holder=el(display?'div':'span');holder.className=display?'math-display':'math-inline';
  try{
   if(source.length>2000)throw Error();let pos=0,depth=0;
   const skip=()=>{while(pos<source.length&&/\s/.test(source[pos]))pos++;};
   function group(){skip();if(source[pos]==='{'){pos++;const n=row('}');if(source[pos++]!=='}')throw Error();return n;}return atom();}
   function atom(){
    skip();if(++depth>40)throw Error();let n;const c=source[pos++];if(!c)throw Error();
    if(c==='{'){n=row('}');if(source[pos++]!=='}')throw Error();}
    else if(c==='\\'){
     const match=/^[A-Za-z]+/.exec(source.slice(pos));const cmd=match?match[0]:source[pos++];if(match)pos+=cmd.length;
     if(cmd==='left'||cmd==='right'){skip();n=source[pos]==='.'?(pos++,mn('mrow')):atom();}
     else if(['frac','dfrac','tfrac'].includes(cmd))n=mn('mfrac',group(),group());
     else if(cmd==='sqrt')n=mn('msqrt',group());
     else if(['text','mathrm','operatorname'].includes(cmd)){skip();if(source[pos++]!=='{')throw Error();const end=source.indexOf('}',pos);if(end<0)throw Error();n=mn('mtext',source.slice(pos,end));pos=end+1;}
     else if(cmd==='boxed'){n=mn('menclose',group());n.setAttribute('notation','box');}
     else if(symbols[cmd])n=mn('mo',symbols[cmd]);
     else if(['sin','cos','tan','log','ln','lim'].includes(cmd))n=mn('mi',cmd);
     else if([',',';',':','!',' '].includes(cmd))n=mn('mtext',' ');
     else if(['{','}','|','%','$','_'].includes(cmd))n=mn('mo',cmd);
     else throw Error();
    }else if(/[0-9]/.test(c)){let text=c;while(pos<source.length&&/[0-9.]/.test(source[pos]))text+=source[pos++];n=mn('mn',text);}
    else n=mn(/[A-Za-z]/.test(c)?'mi':'mo',c);
    depth--;return n;
   }
   function row(end){const nodes=[];while(pos<source.length){skip();if(pos>=source.length||source[pos]===end)break;
    if(source[pos]==='^'||source[pos]==='_'){
     if(!nodes.length)throw Error();const base=nodes.pop();let sup=null,sub=null;
     for(let i=0;i<2;i++){const op=source[pos];if(!['^','_'].includes(op))break;pos++;if(op==='^')sup=group();else sub=group();}
     nodes.push(sup&&sub?mn('msubsup',base,sub,sup):mn(sup?'msup':'msub',base,sup||sub));
    }else nodes.push(atom());
   }return mn('mrow',...nodes);}
   const tree=row(null);if(pos!==source.length)throw Error();const math=mn('math',tree);math.setAttribute('display',display?'block':'inline');math.setAttribute('aria-label',source);holder.append(math);
  }catch{holder.className+=' math-fallback';holder.textContent=source;holder.title='Nieobsługiwany zapis TeX — pokazuję źródło.';}
  return holder;
 }
 function mathToken(src,block){
  for(const [a,b] of block?[['$$','$$'],['\\[','\\]']]:[['$','$'],['\\(','\\)']]){
   if(!src.startsWith(a)||(!block&&src.startsWith('$$')))continue;const end=src.indexOf(b,a.length);if(end<0)continue;
   const text=src.slice(a.length,end);if(!text.trim()||(!block&&text.includes('\n')))continue;
   return {type:'math',raw:src.slice(0,end+b.length),text,display:block};
  }
 }
 const parser=new marked.Marked({gfm:true,breaks:true,extensions:[
  {name:'math',level:'block',start:s=>s.search(/\$\$|\\\[/),tokenizer:s=>mathToken(s,true)},
  {name:'math',level:'inline',start:s=>s.search(/\$|\\\(/),tokenizer:s=>mathToken(s,false)}
 ]});
 function decode(text){return String(text||'').replace(/&(amp|lt|gt|quot|apos|#39|#\d+|#x[\da-f]+);/gi,(all,v)=>{const map={amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",'#39':"'"};if(map[v])return map[v];const n=v[1]?.toLowerCase()==='x'?parseInt(v.slice(2),16):parseInt(v.slice(1),10);return n>0&&n<=0x10ffff?String.fromCodePoint(n):all;});}
 function append(parent,tokens,depth=0){
  if(depth>30){parent.append(document.createTextNode('[Zbyt głębokie formatowanie]'));return;}
  for(const t of tokens||[]){let n;const children=(target,items=t.tokens)=>append(target,items,depth+1);
   switch(t.type){
    case 'space':continue;
    case 'math':n=formula(t.text,t.display);break;
    case 'heading':n=el('h'+Math.max(1,Math.min(6,t.depth)));children(n);break;
    case 'paragraph':n=el('p');children(n);break;
    case 'strong':case 'em':case 'del':case 'blockquote':n=el(t.type);children(n);break;
    case 'br':case 'hr':n=el(t.type);break;
    case 'codespan':n=el('code',decode(t.text));break;
    case 'list':n=el(t.ordered?'ol':'ul');if(t.ordered&&Number.isSafeInteger(t.start))n.start=Math.max(1,Math.min(1000000,t.start));for(const item of t.items){const li=el('li');children(li,item.tokens);n.append(li);}break;
    case 'table':{n=el('div');n.className='table-scroll';const table=el('table'),head=el('thead'),body=el('tbody');for(const [cells,target,tag] of [[t.header,head,'th'],...t.rows.map(r=>[r,body,'td'])]){const tr=el('tr');for(const cell of cells){const td=el(tag);children(td,cell.tokens);tr.append(td);}target.append(tr);}table.append(head,body);n.append(table);break;}
    case 'link':{n=el('span');let url;try{url=new URL(decode(t.href));}catch{}if(url&&['http:','https:','mailto:'].includes(url.protocol)){n=el('a');n.href=url.href;n.target='_blank';n.rel='noopener noreferrer';}children(n);break;}
    case 'image':n=el('span','[Obraz: '+decode(t.text)+']');break;
    case 'code':{n=el('section');n.className='code-block';const bar=el('div');bar.className='code-bar';bar.append(el('span',(t.lang||'kod').split(/\s/)[0].slice(0,30)));const button=el('button','Kopiuj');button.type='button';button.onclick=async()=>{try{await navigator.clipboard.writeText(t.text);button.textContent='Skopiowano';}catch{button.textContent='Zaznacz i skopiuj ręcznie';}};bar.append(button);const pre=el('pre'),code=el('code',t.text);try{window.KripSyntax?.render(code,t.text,(t.lang||'').split(/\s/)[0]);}catch{code.textContent=t.text;}pre.append(code);n.append(bar,pre);break;}
    case 'text':if(t.tokens){children(parent);continue;}n=document.createTextNode(decode(t.text));break;
    default:n=document.createTextNode(decode(t.raw||t.text));
   }parent.append(n);
  }
 }
 return {render(target,text){target._raw=text;target.classList.add('formatted');try{const f=document.createDocumentFragment();append(f,parser.lexer(text));target.replaceChildren(f);}catch{target.textContent=text;}}};
})();

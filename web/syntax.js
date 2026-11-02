'use strict';
// Mały lokalny lexer: wyłącznie tekst i span, bez parsowania HTML z modelu.
window.KripSyntax=(()=>{
 const aliases={js:'javascript',jsx:'javascript',ts:'javascript',tsx:'javascript',javascript:'javascript',typescript:'javascript',py:'python',python:'python',html:'html',xml:'html',svg:'html',css:'css',json:'json',sql:'sql',sh:'shell',bash:'shell',shell:'shell',ps1:'powershell',powershell:'powershell'};
 const words={
  javascript:'async await break case catch class const continue debugger default delete do else export extends false finally for from function if import in instanceof let new null of return static super switch this throw true try typeof undefined var void while with yield',
  python:'and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield',
  sql:'ALL ALTER AND AS ASC BEGIN BY CASE COMMIT CREATE DELETE DESC DISTINCT DROP ELSE END EXISTS FALSE FROM GROUP HAVING IN INDEX INNER INSERT INTO IS JOIN LEFT LIKE LIMIT NOT NULL OFFSET ON OR ORDER OUTER PRIMARY REFERENCES RIGHT ROLLBACK SELECT SET TABLE THEN TRUE UNION UNIQUE UPDATE VALUES WHEN WHERE',
  powershell:'begin break catch class continue data do dynamicparam else elseif end enum exit filter finally for foreach from function if in param process return switch throw trap try until using var while',
  shell:'if then else elif fi for while do done case esac function in select until'
 };
 const keywords=Object.fromEntries(Object.entries(words).map(([k,v])=>[k,new Set(v.split(' '))]));
 function language(label){const key=String(label||'').toLowerCase();return Object.hasOwn(aliases,key)?aliases[key]:null;}
 function pattern(lang){
  // Każda alternatywa zużywa co najmniej jeden znak. Brak zagnieżdżonych kwantyfikatorów.
  if(lang==='html')return /<!--[\s\S]*?(?:-->|$)|<\/?[A-Za-z][^<>]*>|<!DOCTYPE[^>]*>|&(?:#\d+|#x[\da-fA-F]+|[A-Za-z]+);/gi;
  if(lang==='json')return /"(?:\\[\s\S]|[^"\\])*"?|\b(?:true|false|null)\b|-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  if(lang==='css')return /\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\])*"?|'(?:\\[\s\S]|[^'\\])*'?|#[\da-fA-F]{3,8}\b|\b\d+(?:\.\d+)?(?:px|em|rem|vh|vw|s|ms|%)?|--[\w-]+|[A-Za-z_-][\w-]*(?=\s*:)/g;
  if(lang==='python')return /#[^\n]*|"""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|"(?:\\[\s\S]|[^"\\\n])*"?|'(?:\\[\s\S]|[^'\\\n])*'?|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b/g;
  if(lang==='sql')return /--[^\n]*|\/\*[\s\S]*?(?:\*\/|$)|'(?:''|[^'])*'?|"(?:""|[^"])*"?|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b/g;
  if(lang==='shell'||lang==='powershell')return /#[^\n]*|"(?:\\[\s\S]|`[\s\S]|[^"\\`])*"?|'[^']*'?|\$[A-Za-z_][\w:]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b/g;
  return /\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\\n])*"?|'(?:\\[\s\S]|[^'\\\n])*'?|`(?:\\[\s\S]|[^`\\])*`?|\b(?:0x[\da-fA-F]+|\d+(?:\.\d+)?)\b|\b[A-Za-z_$][\w$]*\b/g;
 }
 function kind(token,lang,source,end){
  if(lang==='html')return token.startsWith('<!--')?'comment':token[0]==='&'?'number':'tag';
  if(token.startsWith('//')||token.startsWith('/*')||(lang==='sql'&&token.startsWith('--'))||(['python','shell','powershell'].includes(lang)&&token[0]==='#'))return 'comment';
  if('"\'`'.includes(token[0]))return lang==='json'&&/^\s*:/.test(source.slice(end))?'property':'string';
  if(lang==='css')return token[0]==='#'||/^[\d]/.test(token)?'number':'property';
  if(lang==='json')return ['true','false','null'].includes(token)?'keyword':'number';
  if(/^-?\d/.test(token))return 'number';
  if(token[0]==='$'&&['shell','powershell'].includes(lang))return 'variable';
  const word=lang==='sql'?token.toUpperCase():lang==='powershell'?token.toLowerCase():token;
  return keywords[lang]?.has(word)?'keyword':null;
 }
 function render(target,source,label){
  const lang=language(label);
  // SSE renderuje ponownie cały blok; limity ograniczają koszt i rozmiar DOM.
  if(!lang||source.length>40000){target.textContent=source;return;}
  const fragment=document.createDocumentFragment();let pos=0,count=0;
  for(const match of source.matchAll(pattern(lang))){
   if(++count>8000){target.textContent=source;return;}
   if(match.index>pos)fragment.append(document.createTextNode(source.slice(pos,match.index)));
   const token=match[0],end=match.index+token.length,type=kind(token,lang,source,end);
   if(type){const span=document.createElement('span');span.className='syntax-'+type;span.textContent=token;fragment.append(span);}
   else fragment.append(document.createTextNode(token));
   pos=end;
  }
  if(pos<source.length)fragment.append(document.createTextNode(source.slice(pos)));
  target.replaceChildren(fragment);
 }
 return {render,language};
})();

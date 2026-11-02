// Model DOM testuje logikę, nie układ wizualny przeglądarki.
class Node {
 constructor(tag='text',text=''){this.tagName=tag;this.children=[];this.value='';this._text=text;this.attributes={};this.listeners={};this.className='';this.hidden=false;this.classList={add:n=>this.className+=' '+n};}
 append(...nodes){for(const n of nodes){if(n.tagName==='fragment')this.append(...n.children);else{this.children.push(n);n.parentNode=this;}}}
 replaceChildren(...nodes){this.children=[];this._text='';this.append(...nodes);}
 get textContent(){return this._text+this.children.map(n=>n.textContent).join('');}
 set textContent(v){this._text=String(v);this.children=[];}
 setAttribute(k,v){this.attributes[k]=String(v);}removeAttribute(k){delete this.attributes[k];delete this[k];}
 addEventListener(k,fn){this.listeners[k]=fn;}focus(){}click(){}close(){this.open=false;}showModal(){this.open=true;}
}
function walk(n){return [n,...n.children.flatMap(walk)];}
function document(){const nodes={};return {nodes,getElementById:id=>nodes[id]||(nodes[id]=new Node('div')),createElement:t=>new Node(t),createElementNS:(ns,t)=>new Node(t),createTextNode:t=>new Node('text',t),createDocumentFragment:()=>new Node('fragment')};}
module.exports={Node,walk,document};

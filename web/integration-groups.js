'use strict';
window.KripIntegrationGroups=(()=>{
 const groups=new Map(),order=['github','mcp','mcp_files','mcp_time','feeds'];
 function mount({id,title,parent}){
  if(groups.has(id))return groups.get(id);
  const element=document.createElement('details'),summary=document.createElement('summary'),name=document.createElement('span'),status=document.createElement('span'),body=document.createElement('div');
  element.className='integration-group';element.setAttribute('data-integration',id);element.open=false;
  name.textContent=title;status.className='integration-status';status.textContent='Nie sprawdzono';body.className='integration-body';summary.append(name,status);element.append(summary,body);
  const group={element,body,setStatus(kind,label){const value=['neutral','pending','ok','error'].includes(kind)?kind:'neutral';status.setAttribute('data-state',value);status.textContent=String(label).slice(0,80);}};
  groups.set(id,group);
  // Kolejność nie zależy od kolejności ładowania adapterów. Montujemy tylko na starcie.
  const unrelated=[...parent.children].filter(node=>![...groups.values()].some(item=>item.element===node));
  const sorted=[...groups.entries()].sort(([a],[b])=>(order.indexOf(a)<0?99:order.indexOf(a))-(order.indexOf(b)<0?99:order.indexOf(b))).map(([,item])=>item.element);
  parent.replaceChildren(...unrelated,...sorted);return group;
 }
 function clear(){for(const group of groups.values()){group.element.open=false;group.setStatus('neutral','Nie sprawdzono');}}
 return {mount,clear};
})();

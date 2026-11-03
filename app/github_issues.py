"""Zgłoszenia i pierwsza porcja dyskusji: wyłącznie odczyt, jawne limity."""
import json
from .network import ToolError

def text(row,key,default=''):
    value=row.get(key,default)
    if value is None:value=''
    if not isinstance(value,str) or '\x00' in value:raise ToolError('tool_format_denied')
    return value

def identity(row,number=None):
    if not isinstance(row,dict) or type(row.get('number')) is not int or row['number']<1 or row.get('state') not in {'open','closed'}:raise ToolError('tool_format_denied')
    if number is not None and row['number']!=number:raise ToolError('tool_format_denied')
    title=text(row,'title')
    if not title.strip():raise ToolError('tool_format_denied')
    return title

def labels(row):
    values=row.get('labels',[])
    if not isinstance(values,list):raise ToolError('tool_format_denied')
    if any(not isinstance(item,dict) or not isinstance(item.get('name'),str) for item in values):raise ToolError('tool_format_denied')
    return [text(item,'name') for item in values]

def snapshot(row,number):
    title=identity(row,number)
    if 'pull_request' in row:raise ToolError('github_issue_is_pull_request')
    count=row.get('comments');updated=text(row,'updated_at')
    if type(count) is not int or count<0 or not updated or len(updated)>64:raise ToolError('tool_format_denied')
    return (title,text(row,'body'),row['state'],count,updated,tuple(labels(row)))

def read(repo,section,number,request):
    def get(suffix):
        try:return json.loads(request(suffix)['data'])
        except (ValueError,KeyError,TypeError):raise ToolError('tool_format_denied') from None
    if section=='issues':
        rows=get('issues?state=open&sort=updated&direction=desc&per_page=21')
        if not isinstance(rows,list):raise ToolError('tool_format_denied')
        selected=[];omitted=0
        for row in rows[:21]:
            title=identity(row)
            if 'pull_request' in row:omitted+=1;continue
            selected.append('#'+str(row['number'])+' ['+row['state']+'] '+title[:200])
        partial=len(rows)>=21 or len(selected)>10 or omitted>0;value='\n'.join(selected[:10])
        note='Pierwsza porcja do 21 wpisów API; pominięto PR. To niepełna lista.' if partial else 'Lista otwartych zgłoszeń z pierwszej porcji API.'
        return {'url':'https://github.com/'+repo+'/issues','title':repo+' · zgłoszenia','text':value or 'Brak zgłoszeń w pobranej porcji API.','excerpt':value[:1200],'content_kind':'issue_list','truncated':partial,'count':min(10,len(selected)),'limit':10,'scanned_entries':min(21,len(rows)),'omitted_pull_requests':omitted,'scope_note':note}
    endpoint='issues/'+str(number);first=get(endpoint);version=snapshot(first,number);error=None
    try:comments=get(endpoint+'/comments?per_page=11')
    except ToolError as exc:
        if exc.code!='tool_response_too_large':raise
        comments=[];error=exc.code
    if not isinstance(comments,list):raise ToolError('tool_format_denied')
    current=get(endpoint)
    if snapshot(current,number)!=version:raise ToolError('github_issue_changed')
    title,body,state,total,updated,tag_names=version
    if len(comments)>total:raise ToolError('github_issue_changed')
    partial=len(title)>200 or len(body)>4000 or total>min(10,len(comments)) or len(comments)>10 or len(tag_names)>8 or any(len(tag)>60 for tag in tag_names[:8]) or bool(error)
    lines=['Issue #'+str(number)+': '+title[:200],'State: '+state,'Updated: '+updated,'Comments: '+str(total),'Labels: '+', '.join(tag[:60] for tag in tag_names[:8]),'Opis (niezaufana treść):',body[:4000]]
    if error:lines.append('Komentarze nieodczytane: '+error)
    comment_urls=[];previous=0
    for comment in comments[:10]:
        if not isinstance(comment,dict) or type(comment.get('id')) is not int or comment['id']<=previous:raise ToolError('tool_format_denied')
        previous=comment['id'];value=text(comment,'body');changed=text(comment,'updated_at');author=comment.get('user')
        if author is None:login='autor niedostępny'
        elif isinstance(author,dict):login=text(author,'login')
        else:raise ToolError('tool_format_denied')
        if not changed or len(changed)>64:raise ToolError('tool_format_denied')
        partial|=len(value)>1500 or len(login)>64
        url='https://github.com/'+repo+'/issues/'+str(number)+'#issuecomment-'+str(previous);comment_urls.append(url)
        lines+=['\nComment '+str(previous)+' · '+login[:64]+' · '+changed,url,value[:1500] or '[Brak treści]']
    note='Sprawdzono metadane zgłoszenia przed i po odczycie; komentarze to pojedyncza porcja, bez transakcyjnej migawki.'
    lines.append(note);value='\n'.join(lines)
    return {'url':'https://github.com/'+repo+'/issues/'+str(number),'title':repo+' · zgłoszenie #'+str(number),'text':value[:1200],'excerpt':value[:1200],'document':value,'content_kind':'issue','truncated':bool(partial),'processed_comments':len(comment_urls),'total_comments':total,'comment_urls':comment_urls,'comments_error':error,'metadata_updated_at':updated,'scope_note':note}

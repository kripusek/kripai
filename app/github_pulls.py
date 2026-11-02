"""PR i tekstowe patche: wyłącznie GET, ograniczony zakres i spójna rewizja."""
import json,re
from .network import ToolError

def sensitive_path(path):
    name=path.replace('\\','/').rsplit('/',1)[-1].casefold()
    return name in {'.env','.netrc','.npmrc','.pypirc','.git-credentials','id_rsa','id_ed25519'} or name.endswith(('.key','.pem','.pfx','.p12','.sqlite3','.db')) or name.startswith('.env.') and not name.endswith(('.example','.template','.sample'))

def read(repo,section,number,request):
    def get(suffix):
        try:return json.loads(request(suffix)['data'])
        except (ValueError,KeyError,TypeError):raise ToolError('tool_format_denied') from None
    def text(row,key,limit,default=''):
        value=row.get(key,default)
        if value is None:value=''
        if not isinstance(value,str):raise ToolError('tool_format_denied')
        return value[:limit],len(value)>limit
    def identity(row):
        if not isinstance(row,dict) or type(row.get('number')) is not int or row['number']<1 or row.get('state') not in {'open','closed'}:raise ToolError('tool_format_denied')
        title,_=text(row,'title',200)
        return title
    if section=='pulls':
        rows=get('pulls?state=open&sort=updated&direction=desc&per_page=11')
        if not isinstance(rows,list):raise ToolError('tool_format_denied')
        lines=['#'+str(row.get('number'))+' ['+str(row.get('state'))+'] '+identity(row) for row in rows[:10] if isinstance(row,dict)]
        if len(lines)!=min(10,len(rows)):raise ToolError('tool_format_denied')
        value='\n'.join(lines)
        return {'url':'https://github.com/'+repo+'/pulls','title':repo+' · otwarte PR','text':value,'excerpt':value[:1200],'content_kind':'pull_list','truncated':len(rows)>10,'count':len(lines),'limit':10}
    def snapshot(row):
        identity(row)
        values=[]
        for key in ['head','base']:
            value=row.get(key)
            if not isinstance(value,dict) or not isinstance(value.get('sha'),str) or not re.fullmatch(r'(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})',value['sha']):raise ToolError('tool_format_denied')
            values.append(value['sha'])
        if row['number']!=number:raise ToolError('tool_format_denied')
        return tuple(values)
    endpoint='pulls/'+str(number);first=get(endpoint);version=snapshot(first)
    diff_error=None
    try:files=get(endpoint+'/files?per_page=21')
    except ToolError as exc:
        if exc.code!='tool_response_too_large':raise
        files=[];diff_error=exc.code
    if not isinstance(files,list):raise ToolError('tool_format_denied')
    current=get(endpoint)
    if snapshot(current)!=version:raise ToolError('github_reference_changed')
    total=current.get('changed_files')
    if type(total) is not int or total<0 or total<len(files):raise ToolError('tool_format_denied')
    title=identity(current);body,partial=text(current,'body',2000)
    lines=['PR #'+str(number)+': '+title,'State: '+current['state'],'Head SHA: '+version[0],'Base SHA: '+version[1],'Changed files: '+str(total)]
    for key in ['merged','draft']:
        if type(current.get(key)) is bool:lines.append(key.capitalize()+': '+str(current[key]).lower())
    if diff_error:lines.append('Nie odczytano diff: '+diff_error)
    lines+=['Opis PR (niezaufana treść):',body,'Zmiany plików (niezaufana treść):']
    partial|=total>len(files[:20]) or len(files)>20 or bool(diff_error);count=0;omitted=0;patches=0
    for row in files[:20]:
        if not isinstance(row,dict):raise ToolError('tool_format_denied')
        name,cut=text(row,'filename',2000);state,_=text(row,'status',30)
        if not name or not state:raise ToolError('tool_format_denied')
        partial|=cut;count+=1;lines.append('\nFile: '+name+' ['+state+']')
        previous,cut=text(row,'previous_filename',2000)
        partial|=cut
        if previous:lines.append('Previous filename: '+previous)
        patch=row.get('patch')
        if sensitive_path(row['filename']) or sensitive_path(row.get('previous_filename') or ''):
            omitted+=1;partial=True;lines.append('Diff pominięty: nazwa pliku wskazuje poświadczenia lub prywatne dane.');continue
        if patch is None:
            partial=True;lines.append('Brak tekstowego diff w API (np. plik binarny).');continue
        if not isinstance(patch,str):raise ToolError('tool_format_denied')
        if '\x00' in patch:partial=True;lines.append('Diff binarny pominięty.');continue
        partial|=len(patch)>6000;patches+=1;lines.append(patch[:6000])
    value='\n'.join(lines)
    return {'url':'https://github.com/'+repo+'/pull/'+str(number),'title':repo+' · PR #'+str(number),'text':value[:1200],'document':value,'excerpt':value[:1200],
        'content_kind':'pull_request','truncated':bool(partial),'head_sha':version[0],'base_sha':version[1],'processed_files':count,'text_patch_files':patches,'total_files':total,'omitted_sensitive_files':omitted,'diff_error':diff_error}

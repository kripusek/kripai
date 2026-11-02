"""Publiczny HTTPS GET: przypięcie sprawdzonego IP, TLS i brak sekretów/proxy/cookies."""
import base64
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import urlsplit,urlunsplit,urljoin,quote,urlencode

MAX_BODY=512*1024
class ToolError(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)

def canonical(url):
    if not isinstance(url,str) or len(url)>2048 or any(ord(c)<33 or ord(c)==127 for c in url) or '\\' in url:raise ToolError('tool_url_invalid')
    try:
        p=urlsplit(url);host=(p.hostname or '').rstrip('.').encode('idna').decode('ascii').lower()
        if p.scheme!='https' or p.username is not None or p.password is not None or p.port not in (None,443) or not host:raise ValueError()
        if host=='localhost' or host.endswith(('.localhost','.local','.internal','.home.arpa','.onion')):raise ValueError()
        authority='['+host+']' if ':' in host else host
        return urlunsplit(('https',authority,quote(p.path or '/',safe="/%:@!$&'()*+,;=-._~"),quote(p.query,safe="%=&?/:@!$'()*+,;-._~"),''))
    except (ValueError,UnicodeError):raise ToolError('tool_url_invalid') from None

def public_ip(value):
    try:
        address=ipaddress.ip_address(value)
        if not address.is_global or address.is_multicast or address.is_reserved:return False
        if isinstance(address,ipaddress.IPv6Address):
            if address.ipv4_mapped:return public_ip(str(address.ipv4_mapped))
            if address.sixtofour is not None or address.teredo is not None:return False
            if address in ipaddress.ip_network('64:ff9b::/96') or address in ipaddress.ip_network('64:ff9b:1::/48'):return False
        return True
    except ValueError:return False

def resolve(host):
    try:addresses=list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
    except OSError:raise ToolError('tool_dns_failed') from None
    if not addresses or len(addresses)>32 or any(not public_ip(ip) for ip in addresses):raise ToolError('tool_address_denied')
    return addresses[0]

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,ip):
        context=ssl.create_default_context();context.set_alpn_protocols(['http/1.1'])
        super().__init__(host,443,timeout=5,context=context);self.ip=ip
    def connect(self):
        raw=socket.create_connection((self.ip,443),timeout=self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:raw.close();raise

def fetch(url):
    current=canonical(url)
    for _ in range(4):
        p=urlsplit(current);ip=resolve(p.hostname);conn=PinnedHTTPS(p.hostname,ip)
        try:
            conn.request('GET',p.path+('?' +p.query if p.query else ''),headers={'User-Agent':'KripAI/1.0 read-only','Accept':'text/html,text/plain,application/json','Accept-Encoding':'identity'})
            response=conn.getresponse()
            if response.status in (301,302,303,307,308):
                location=response.getheader('Location')
                if not location:raise ToolError('tool_redirect_invalid')
                current=canonical(urljoin(current,location));continue
            if response.status in (403,429):raise ToolError('tool_remote_denied')
            if response.status!=200:raise ToolError('tool_http_error')
            kind=response.getheader('Content-Type','').split(';')[0].strip().lower()
            if kind not in {'text/html','text/plain','application/json','application/vnd.github+json'}:raise ToolError('tool_format_denied')
            if response.getheader('Content-Encoding','identity').lower()!='identity':raise ToolError('tool_encoding_denied')
            length=response.getheader('Content-Length')
            if length and (not length.isdigit() or int(length)>MAX_BODY):raise ToolError('tool_response_too_large')
            data=response.read(MAX_BODY+1)
            if len(data)>MAX_BODY:raise ToolError('tool_response_too_large')
            return {'url':current,'kind':kind,'data':data}
        except (OSError,http.client.HTTPException):raise ToolError('tool_network_failed') from None
        finally:conn.close()
    raise ToolError('tool_redirect_limit')

class Text(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.hidden=[];self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','head','iframe','svg','template','noscript'}:self.hidden.append(tag)
        if not self.hidden and tag in {'p','br','li','div','h1','h2','h3'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if self.hidden and tag==self.hidden[-1]:self.hidden.pop()
    def handle_data(self,data):
        if not self.hidden and len(self.parts)<10000:self.parts.append(data)

def policy(text,web=False,github=False):
    urls=[];repos=set()
    for raw in re.findall(r'https://[^\s<>"\[\]()]+',text):
        try:
            url=canonical(raw.rstrip('.,;!'));urls.append(url)
            p=urlsplit(url)
            if p.hostname=='github.com':
                pair='/'.join(p.path.strip('/').split('/')[:2])
                if valid_repo(pair):repos.add(pair.lower())
        except ToolError:continue
    for match in re.finditer(r'(?<![\w./-])([A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100})(?![\w./-])',text):
        pair=match[1].rstrip('.,;!')
        if valid_repo(pair):repos.add(pair.lower())
    return {'web':bool(web),'github':bool(github),'urls':urls,'repositories':sorted(repos),'request':text}

def valid_repo(value):
    return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}',value)) and all(part not in {'.','..'} for part in value.split('/'))

def execute(name,args,scope):
    if not isinstance(args,dict):raise ToolError('tool_arguments_invalid')
    if name=='web_read':
        if not scope['web']:raise ToolError('tool_permission_denied')
        if set(args)!={'url'}:raise ToolError('tool_arguments_invalid')
        url=canonical(args['url'])
        if url not in scope['urls']:raise ToolError('tool_resource_not_authorized')
        result=fetch(url);raw=result['data'].decode('utf-8',errors='replace')
        if result['kind']=='text/html':
            parser=Text();parser.feed(raw);raw=' '.join(parser.parts)
        if '\x00' in raw:raise ToolError('tool_format_denied')
        text=re.sub(r'\s+',' ',raw).strip()
        return {'url':result['url'],'title':urlsplit(result['url']).hostname,'text':text[:1200],'truncated':len(text)>1200}
    if name not in {'github_read','github_find'}:raise ToolError('tool_not_allowed')
    if not scope['github']:raise ToolError('tool_permission_denied')
    if name=='github_find':
        if set(args)!={'query'} or not isinstance(args['query'],str) or not 3<=len(args['query'])<=120:raise ToolError('tool_arguments_invalid')
        query=args['query']
        if query.casefold() not in scope['request'].casefold():raise ToolError('tool_resource_not_authorized')
        result=fetch('https://api.github.com/search/repositories?'+urlencode({'q':query,'per_page':3}))
        data=json.loads(result['data']);items=data['items'][:3]
        text=json.dumps([{'repository':r['full_name'],'description':r.get('description'),'url':r['html_url']} for r in items],ensure_ascii=False)
        return {'url':'https://github.com/search?'+urlencode({'q':query,'type':'repositories'}),'title':'GitHub — repozytoria','text':text[:1200],'truncated':len(text)>1200 or data.get('incomplete_results',False) or data.get('total_count',len(items))>len(items)}
    if set(args)!={'repository','section'} or not valid_repo(args['repository']) or args['section'] not in {'readme','issues'}:raise ToolError('tool_arguments_invalid')
    repo=args['repository']
    if repo.lower() not in scope['repositories']:raise ToolError('tool_resource_not_authorized')
    suffix='readme' if args['section']=='readme' else 'issues?state=open&per_page=3'
    result=fetch('https://api.github.com/repos/'+repo+'/'+suffix);data=json.loads(result['data'])
    if args['section']=='readme':
        if data.get('encoding')!='base64':raise ToolError('tool_format_denied')
        raw=base64.b64decode(data['content'],validate=False)
        try:text=raw.decode('utf-8')
        except UnicodeError:raise ToolError('tool_format_denied') from None
        if '\x00' in text:raise ToolError('tool_format_denied')
    else:text=json.dumps([{'title':r['title'],'body':(r.get('body') or '')[:500],'url':r['html_url']} for r in data[:3]],ensure_ascii=False)
    return {'url':'https://github.com/'+repo+('/issues' if args['section']=='issues' else '#readme'),'title':repo+' · '+args['section'],'text':text[:1200],'truncated':len(text)>1200}

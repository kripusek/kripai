"""Publiczny HTTPS GET: przypięcie sprawdzonego IP, TLS i brak sekretów/proxy/cookies."""
import base64
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
import zlib
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit,urlunsplit,urljoin,quote,urlencode

MAX_BODY=512*1024
MAX_PAGE_BYTES=8*1024**2
MAX_DECODED=16*1024**2
MAX_TEXT=160000
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

def body(response,partial=False):
    encoding=response.getheader('Content-Encoding','identity').strip().lower()
    if encoding not in {'identity','gzip','deflate'}:raise ToolError('tool_encoding_denied')
    length=response.getheader('Content-Length')
    if length and not length.isdigit():raise ToolError('tool_http_error')
    limit=MAX_PAGE_BYTES if partial else MAX_BODY
    decoded_limit=MAX_DECODED if partial else MAX_BODY
    if not partial and length and int(length)>limit:raise ToolError('tool_response_too_large')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS if encoding=='gzip' else zlib.MAX_WBITS) if encoding!='identity' else None
    output=bytearray();wire=0;truncated=False
    try:
        while True:
            chunk=response.read(min(65536,limit-wire+1))
            if not chunk:break
            room=limit-wire
            if len(chunk)>room:chunk=chunk[:room];truncated=True
            wire+=len(chunk)
            available=decoded_limit-len(output)
            part=decoder.decompress(chunk,available+1) if decoder else chunk
            if len(part)>available:part=part[:available];truncated=True
            output.extend(part)
            if truncated:break
        if length and wire<int(length):truncated=True
        if decoder and not truncated and not decoder.eof:raise ToolError('tool_encoding_failed')
    except zlib.error:raise ToolError('tool_encoding_failed') from None
    if truncated and not partial:raise ToolError('tool_response_too_large')
    return bytes(output),truncated

def fetch(url,partial=False,token=None,sites=None):
    current=canonical(url)
    if token and urlsplit(current).hostname!='api.github.com':raise ToolError('tool_permission_denied')
    for _ in range(4):
        p=urlsplit(current)
        if sites and not search_host_allowed(p.hostname,sites):raise ToolError('tool_search_domain_denied')
        ip=resolve(p.hostname);conn=PinnedHTTPS(p.hostname,ip)
        try:
            headers={'User-Agent':'KripAI/1.0 read-only','Accept':'text/html,text/plain,application/json,application/rss+xml,application/xml','Accept-Encoding':'gzip, deflate'}
            if token:headers['Authorization']='Bearer '+token
            conn.request('GET',p.path+('?' +p.query if p.query else ''),headers=headers)
            response=conn.getresponse()
            if response.status in (301,302,303,307,308):
                if token:raise ToolError('tool_redirect_invalid')
                location=response.getheader('Location')
                if not location:raise ToolError('tool_redirect_invalid')
                current=canonical(urljoin(current,location));continue
            if response.status in (401,403,429):raise ToolError('tool_remote_denied')
            if response.status!=200:raise ToolError('tool_http_error')
            content_type=response.getheader('Content-Type','');kind=content_type.split(';')[0].strip().lower()
            if kind not in {'text/html','text/plain','application/json','application/vnd.github+json','text/xml','application/xml','application/rss+xml','application/atom+xml'}:raise ToolError('tool_format_denied')
            data,truncated=body(response,partial)
            charset=re.search(r'charset=[\"\']?([A-Za-z0-9_-]+)',content_type,re.I)
            return {'url':current,'kind':kind,'data':data,'download_truncated':truncated,'charset':charset[1] if charset else None}
        except (OSError,http.client.HTTPException):raise ToolError('tool_network_failed') from None
        finally:conn.close()
    raise ToolError('tool_redirect_limit')

class Text(HTMLParser):
    """Główna treść ma pierwszeństwo przed nawigacją, skryptami i stopką."""
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    HIDDEN={'script','style','nav','aside','footer','iframe','svg','template','noscript'}
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.hidden=0;self.main=0;self.head=0;self.title_depth=0
        self.parts=[];self.article=[];self.size=0;self.article_size=0;self.title=[];self.truncated=False;self.fallback_truncated=False;self.article_truncated=False
    def handle_starttag(self,tag,attrs):
        if tag in self.VOID:
            if tag in {'br','hr'}:self.handle_data('\n')
            return
        if len(self.stack)>=256:raise ToolError('tool_html_too_deep')
        hidden=tag in self.HIDDEN;main=tag in {'main','article'};head=tag=='head';title=tag=='title'
        self.stack.append((tag,hidden,main,head,title));self.hidden+=hidden;self.main+=main;self.head+=head;self.title_depth+=title
        if tag in {'p','div','li','section','h1','h2','h3','tr'}:self.handle_data('\n')
    def handle_startendtag(self,tag,attrs):
        if tag not in self.VOID:self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                for _,hidden,main,head,title in self.stack[i:]:self.hidden-=hidden;self.main-=main;self.head-=head;self.title_depth-=title
                del self.stack[i:];break
    def handle_data(self,data):
        if self.title_depth and sum(map(len,self.title))<200:self.title.append(data[:200])
        if self.hidden or self.head:return
        if self.size<MAX_TEXT:
            self.fallback_truncated|=len(data)>MAX_TEXT-self.size
            value=data[:MAX_TEXT-self.size];self.parts.append(value);self.size+=len(value)
        else:self.fallback_truncated=True
        if self.main:
            if self.article_size<MAX_TEXT:
                self.article_truncated|=len(data)>MAX_TEXT-self.article_size
                value=data[:MAX_TEXT-self.article_size];self.article.append(value);self.article_size+=len(value)
            else:self.article_truncated=True
    def result(self):
        main=' '.join(self.article).strip()
        self.truncated=self.article_truncated if len(main)>=40 else self.fallback_truncated
        return (main if len(main)>=40 else ' '.join(self.parts)),''.join(self.title).strip()[:200]

def page(result):
    data=result['data'];charset=result.get('charset')
    if not charset:
        meta=re.search(br'charset=[\"\']?([A-Za-z0-9_-]+)',data[:4096],re.I)
        charset='utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else meta[1].decode('ascii') if meta else 'utf-8-sig'
    try:raw=data.decode(charset,errors='replace')
    except (LookupError,UnicodeError):raw=data.decode('utf-8',errors='replace')
    if '\x00' in raw:raise ToolError('tool_format_denied')
    title=urlsplit(result['url']).hostname;truncated=result.get('download_truncated',False)
    if result['kind']=='text/html':
        parser=Text();parser.feed(raw);raw,heading=parser.result();title=heading or title;truncated|=parser.truncated
    text=re.sub(r'[ \t\r\f\v]+',' ',raw);text=re.sub(r'\n\s*\n+','\n',text).strip()
    if not text:raise ToolError('tool_page_unreadable')
    if len(text)<5000 and title.casefold().strip() in {'site unavailable','just a moment...','access denied','attention required! | cloudflare'}:raise ToolError('tool_remote_denied')
    truncated|=len(text)>MAX_TEXT;text=text[:MAX_TEXT]
    return {'url':result['url'],'title':title,'text':text[:1200],'document':text,'excerpt':text[:1200],
        'truncated':bool(truncated),'document_characters':len(text),'summary':False}

def search_sites(*texts):
    sites=[]
    for text in texts:
        for match in re.finditer(r'''(?<![\w:])(-?)site:([^\s<>"'()]+)''',text,re.I):
            try:
                domain=match[2].rstrip('.,;!')
                if any(c in domain for c in '/:@?#\\%'):raise ToolError('tool_url_invalid')
                url=canonical('https://'+domain+'/');parsed=urlsplit(url)
                if parsed.path!='/' or parsed.query:raise ToolError('tool_url_invalid')
            except ToolError:raise ToolError('tool_search_filter_invalid') from None
            sites.append((bool(match[1]),parsed.hostname))
    return sites

def search_host_allowed(host,sites):
    # Granica etykiety DNS: example.org nie dopuszcza example.org.evil ani notexample.org.
    return all((host==domain or host.endswith('.'+domain))!=excluded for excluded,domain in sites)

def python_documents(query,sites=None):
    # Indeks dostarcza prawdziwe linki; nie zgadujemy URL modułu z tekstu modelu.
    if not (re.search(r'\bpython\w*\b',query,re.I) and re.search(r'doc(?:ument)?|dokument',query,re.I)):return None
    sites=search_sites(query) if sites is None else sites
    if not search_host_allowed('docs.python.org',sites):return None
    version=re.search(r'\b3\.\d{1,2}\b',query)
    base='https://docs.python.org/'+(version[0] if version else '3')+'/'
    terms=re.sub(r'\bsite:\S+',' ',query,flags=re.I)
    result=fetch(base+'py-modindex.html')
    class Index(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.link=None;self.label=[];self.items=[];self.seen=set()
        def handle_starttag(self,tag,attrs):
            if tag=='a':self.link=dict(attrs).get('href');self.label=[]
        def handle_data(self,text):
            if self.link is not None:self.label.append(text)
        def handle_endtag(self,tag):
            if tag!='a':return
            link=self.link;label=''.join(self.label).strip();self.link=None
            if not link or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',label):return
            if not re.search(r'(?<![\w.])'+re.escape(label)+r'(?![\w.])',terms,re.I):return
            try:url=canonical(urljoin(base,link))
            except ToolError:return
            parsed=urlsplit(url)
            if parsed.hostname!='docs.python.org' or parsed.query or not re.fullmatch(re.escape(urlsplit(base).path)+r'library/[A-Za-z0-9_.-]+\.html',parsed.path):return
            if url in self.seen or len(self.items)>=5:return
            self.seen.add(url);self.items.append({'url':url,'title':label+' — Python documentation','text':'Link znaleziony w oficjalnym indeksie modułów Pythona. Treść dokumentacji wymaga osobnego odczytu.','truncated':True,'content_kind':'search_snippet'})
    parser=Index();parser.feed(result['data'].decode('utf-8',errors='replace'))
    if parser.items:return {'provider':'Python Docs module index','query':query,'items':parser.items}

def search(query,request=''):
    sites=search_sites(query,request)
    warning=None
    try:
        official=python_documents(query,sites)
        if official:return official
    except ToolError as exc:warning=exc.code
    # Publiczny kanał RSS Bing: bez konta, bez tokenów i bez cichej zmiany dostawcy.
    result=fetch('https://www.bing.com/search?'+urlencode({'format':'rss','q':query}))
    raw=result['data']
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ToolError('tool_search_invalid')
    try:root=ET.fromstring(raw)
    except ET.ParseError:raise ToolError('tool_search_unavailable') from None
    if root.tag!='rss':raise ToolError('tool_search_unavailable')
    items=[];seen=set();discarded=0
    for node in root.findall('./channel/item'):
        try:
            url=canonical((node.findtext('link') or '').strip());host=urlsplit(url).hostname
            try:
                if not public_ip(str(ipaddress.ip_address(host))):continue
            except ValueError:pass
        except ToolError:continue
        if not search_host_allowed(host,sites):discarded+=1;continue
        if url in seen:continue
        seen.add(url);parser=Text();parser.feed(node.findtext('description') or '');snippet,_=parser.result()
        items.append({'url':url,'title':(node.findtext('title') or host)[:200],'text':re.sub(r'\s+',' ',snippet).strip()[:500],'truncated':True,'content_kind':'search_snippet'})
        if len(items)>=5:break
    result={'provider':'Bing RSS','query':query,'items':items}
    if sites:result['site_filter']={'active':True,'discarded':discarded}
    if warning:result['warnings']=[{'provider':'Python Docs module index','error':warning}]
    return result

def policy(text,web=False,github=False,mcp=False):
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
    documents=re.findall(r'(?<![\w./-])([A-Za-z0-9_./-]+\.md)(?![\w./-])',text)
    local_documents=re.findall(r'(?<![\w./-])([\w./-]+\.(?:md|txt))(?![\w./-])',text,re.I)
    local_documents+=re.findall(r'["“]([^"”\r\n]{1,200}\.(?:md|txt))["”]',text,re.I)
    return {'web':bool(web),'github':bool(github),'mcp':bool(mcp),'documents':list(dict.fromkeys(documents)),'local_documents':list(dict.fromkeys(local_documents)),'urls':urls,'repositories':sorted(repos),'request':text}

def valid_repo(value):
    return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}',value)) and all(part not in {'.','..'} for part in value.split('/'))

def execute(name,args,scope):
    if not isinstance(args,dict):raise ToolError('tool_arguments_invalid')
    if name=='web_read':
        if not scope['web']:raise ToolError('tool_permission_denied')
        if set(args)!={'url'}:raise ToolError('tool_arguments_invalid')
        url=canonical(args['url'])
        if url not in scope['urls']:raise ToolError('tool_resource_not_authorized')
        sites=scope.get('search_sites',{}).get(url)
        return page(fetch(url,partial=True,sites=sites) if sites else fetch(url,partial=True))
    if name=='web_search':
        if not scope['web']:raise ToolError('tool_permission_denied')
        if set(args)!={'query'} or not isinstance(args['query'],str) or not 3<=len(args['query'])<=160:raise ToolError('tool_arguments_invalid')
        return search(args['query'],scope.get('request',''))
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
    if not {'repository','section'}<=set(args) or set(args)-{'repository','section','path','ref','number'} or not valid_repo(args['repository']) or args['section'] not in {'readme','issues','issue','file','tree','branches','pulls','pull','commits','commit'}:raise ToolError('tool_arguments_invalid')
    repo=args['repository']
    if repo.lower() not in scope['repositories']:raise ToolError('tool_resource_not_authorized')
    path=args.get('path','')
    if not isinstance(path,str) or len(path)>1024 or any(p in {'.','..'} for p in path.split('/')) or path.startswith('/') or any(ord(c)<32 for c in path) or '\\' in path:raise ToolError('tool_arguments_invalid')
    ref=args.get('ref','')
    if not isinstance(ref,str) or len(ref)>200 or any(c.isspace() or ord(c)<32 or ord(c)==127 or c in '~^:?*[\\' for c in ref) or '..' in ref or '@{' in ref or ref.startswith('/') or ref.endswith('/') or '//' in ref:raise ToolError('tool_arguments_invalid')
    if ref and args['section'] not in {'readme','file','tree','commits','commit'}:raise ToolError('tool_arguments_invalid')
    if args['section'] in {'branches','commits','commit'} and path:raise ToolError('tool_arguments_invalid')
    number=args.get('number',0)
    if type(number) is not int or not 0<=number<=2147483647 or (args['section'] in {'pull','issue'} and not number) or (args['section'] not in {'pull','issue'} and number):raise ToolError('tool_arguments_invalid')
    from .github_pulls import read as read_pull,sensitive_path
    if args['section']=='file' and sensitive_path(path):raise ToolError('github_sensitive_path_denied')
    if args['section'] in {'pulls','pull','issues','issue'} and path:raise ToolError('tool_arguments_invalid')
    if args['section']=='commit' and not re.fullmatch(r'(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})',ref):raise ToolError('github_commit_sha_required')
    from .integrations import ADAPTERS
    token=ADAPTERS['github'].token(repo)
    if args['section'] in {'commits','commit'}:
        from .github_commits import read as read_commit
        def request(suffix):
            url='https://api.github.com/repos/'+repo+'/'+suffix
            return fetch(url,token=token) if token else fetch(url)
        return read_commit(repo,args['section'],ref,request)
    if args['section'] in {'pulls','pull','issues','issue'}:
        def request(suffix):
            url='https://api.github.com/repos/'+repo+'/'+suffix
            return fetch(url,token=token) if token else fetch(url)
        if args['section'] in {'issues','issue'}:
            from .github_issues import read as read_issue
            return read_issue(repo,args['section'],number,request)
        return read_pull(repo,args['section'],number,request)
    suffix={'readme':'readme','issues':'issues?state=open&per_page=3','file':'contents/'+quote(path,safe='/'),'tree':'contents/'+quote(path,safe='/'),'branches':'branches?per_page=21'}[args['section']]
    if ref:suffix+='?'+urlencode({'ref':ref})
    url='https://api.github.com/repos/'+repo+'/'+suffix
    result=fetch(url,token=token) if token else fetch(url)
    data=json.loads(result['data'])
    if args['section']=='branches':
        if not isinstance(data,list):raise ToolError('tool_format_denied')
        rows=[]
        for row in data[:20]:
            if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not isinstance(row.get('commit'),dict) or not re.fullmatch(r'(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})',str(row['commit'].get('sha',''))):raise ToolError('tool_format_denied')
            rows.append(row['name'][:200]+' @ '+row['commit']['sha'])
        text='\n'.join(rows)
        return {'url':'https://github.com/'+repo+'/branches','title':repo+' · gałęzie','text':text,'excerpt':text[:1200],'content_kind':'branches','truncated':len(data)>20,'count':len(rows),'limit':20}
    if args['section']=='tree':
        if not isinstance(data,list):raise ToolError('tool_format_denied')
        # Lista katalogu jest wynikiem API, nie prozą do streszczenia przez LLM.
        text='\n'.join(r['type']+' '+r['path'] for r in data[:200])
        return {'url':'https://github.com/'+repo+'/tree/'+quote(ref or 'HEAD',safe='')+('/'+quote(path,safe='/') if path else ''),'title':repo+' · katalog '+(path or '/')+(' · '+ref if ref else ''),'text':text[:12000],'excerpt':text[:1200],'content_kind':'directory','truncated':len(data)>200 or len(text)>12000,'ref':ref}
    if args['section'] in {'readme','file'}:
        if data.get('encoding')!='base64':raise ToolError('tool_format_denied')
        raw=base64.b64decode(data['content'],validate=False)
        try:text=raw.decode('utf-8')
        except UnicodeError:raise ToolError('tool_format_denied') from None
        if '\x00' in text:raise ToolError('tool_format_denied')
    else:text=json.dumps([{'title':r['title'],'body':(r.get('body') or '')[:500],'url':r['html_url']} for r in data[:3]],ensure_ascii=False)
    source_path='/issues' if args['section']=='issues' else '/blob/'+quote(ref or 'HEAD',safe='')+'/'+quote(path,safe='/') if args['section']=='file' else '#readme'
    if ref and args['section']=='readme':
        name=data.get('path','README.md')
        if not isinstance(name,str):raise ToolError('tool_format_denied')
        source_path='/blob/'+quote(ref,safe='')+'/'+quote(name,safe='/')
    return {'url':'https://github.com/'+repo+source_path,'title':repo+' · '+args['section']+(' · '+path if path else '')+(' · '+ref if ref else ''),'text':text[:1200],'document':text[:MAX_TEXT],'excerpt':text[:1200],'truncated':len(text)>MAX_TEXT,'sha':data.get('sha') if isinstance(data,dict) else None,'ref':ref}

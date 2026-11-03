"""Jeden przypięty MCP czasu: odczyt zegara i konwersja dzisiejszej godziny."""
import base64,json,re,sys
from datetime import datetime,timezone
from urllib.parse import urlencode
from . import config
from .mcp_client import StdioClient
from .network import ToolError
from scripts import setup_mcp_time as setup

READ_TOOLS={'get_current_time','convert_time'}
UTC=timezone.utc


def zone(value):
    if not isinstance(value,str) or len(value)>80 or not re.fullmatch(r'[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+){0,3}',value):raise ToolError('mcp_time_timezone_invalid')
    return value


def stamp(value):
    if not isinstance(value,str) or len(value)>40:raise ToolError('mcp_protocol_invalid')
    try:result=datetime.fromisoformat(value)
    except ValueError:raise ToolError('mcp_protocol_invalid') from None
    if result.tzinfo is None:raise ToolError('mcp_protocol_invalid')
    return result


def record(value,expected=None):
    if not isinstance(value,dict) or set(value)!={'timezone','datetime','day_of_week','is_dst'}:raise ToolError('mcp_protocol_invalid')
    zone(value['timezone']);date=stamp(value['datetime'])
    if expected is not None and value['timezone']!=expected:raise ToolError('mcp_protocol_invalid')
    if type(value['is_dst']) is not bool or value['day_of_week']!=('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')[date.weekday()]:raise ToolError('mcp_protocol_invalid')
    return date


def validate(snapshot):
    if not isinstance(snapshot,dict) or set(snapshot)!={'action','captured_at','result'}:raise ToolError('mcp_protocol_invalid')
    stamp(snapshot['captured_at']);value=snapshot['result']
    if snapshot['action']=='now':record(value)
    elif snapshot['action']=='convert':
        if not isinstance(value,dict) or set(value)!={'source','target','time_difference'}:raise ToolError('mcp_protocol_invalid')
        source=record(value['source']);target=record(value['target'])
        difference=value['time_difference']
        if source!=target or not isinstance(difference,str) or not re.fullmatch(r'[+-]\d{1,2}(?:\.\d{1,4})?h',difference):raise ToolError('mcp_protocol_invalid')
        if abs(float(difference[:-1])-(target.utcoffset()-source.utcoffset()).total_seconds()/3600)>0.0001:raise ToolError('mcp_protocol_invalid')
    else:raise ToolError('mcp_protocol_invalid')
    return snapshot


def encode(snapshot):
    raw=json.dumps(validate(snapshot),ensure_ascii=True,separators=(',',':')).encode()
    value=base64.urlsafe_b64encode(raw).decode().rstrip('=')
    if len(value)>1800:raise ToolError('mcp_protocol_invalid')
    return value


def decode(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,1800}',value):raise ToolError('mcp_protocol_invalid')
    try:result=json.loads(base64.b64decode(value+'='*((-len(value))%4),altchars=b'-_',validate=True))
    except (ValueError,UnicodeError):raise ToolError('mcp_protocol_invalid') from None
    return validate(result)


def status():
    available=setup.installed() is not None
    return {'name':'mcp_time','configured':available,'available':available,'read_only':True,'provider':'Oficjalny MCP Time '+setup.VERSION,'default_timezone':'Europe/Warsaw'}


def execute(arguments,check=lambda:None):
    if not isinstance(arguments,dict) or set(arguments)-{'action','timezone','target_timezone','time'}:raise ToolError('tool_arguments_invalid')
    action=arguments.get('action','now');source=zone(arguments.get('timezone','Europe/Warsaw'))
    target=arguments.get('target_timezone','');wall_time=arguments.get('time','')
    if action=='now':
        if target or wall_time:raise ToolError('tool_arguments_invalid')
        name='get_current_time';params={'timezone':source}
    elif action=='convert':
        zone(target)
        if not isinstance(wall_time,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',wall_time):raise ToolError('mcp_time_arguments_invalid')
        name='convert_time';params={'source_timezone':source,'target_timezone':target,'time':wall_time}
    else:raise ToolError('tool_arguments_invalid')
    folder=setup.installed()
    if folder is None:raise ToolError('mcp_time_unavailable')
    check()
    command=[sys.executable,'-B',str(config.ROOT/'scripts/mcp_time_server.py'),str(folder)]
    client=StdioClient(check,command=command,timeout=15)
    try:
        catalog=client.initialize(required=READ_TOOLS)
        tools=catalog.get('tools')
        if not isinstance(tools,list) or len(tools)!=2 or {row.get('name') for row in tools if isinstance(row,dict)}!=READ_TOOLS or any(not isinstance(row.get('annotations'),dict) or row['annotations'].get('readOnlyHint') is not True for row in tools):raise ToolError('mcp_protocol_invalid')
        result=client.request('tools/call',{'name':name,'arguments':params});check()
        if result.get('isError'):raise ToolError('mcp_time_arguments_invalid')
        content=result.get('content');value=result.get('structuredContent')
        if not isinstance(content,list) or len(content)!=1 or not isinstance(content[0],dict) or content[0].get('type')!='text' or not isinstance(content[0].get('text'),str) or len(content[0]['text'])>8000:raise ToolError('mcp_protocol_invalid')
        try:plain=json.loads(content[0]['text'])
        except ValueError:raise ToolError('mcp_protocol_invalid') from None
        if plain!=value:raise ToolError('mcp_protocol_invalid')
        snapshot=validate({'action':action,'captured_at':datetime.now(UTC).isoformat(),'result':value})
        if action=='now':
            actual=record(value,source)
            if abs((actual-datetime.now(UTC)).total_seconds())>60:raise ToolError('mcp_protocol_invalid')
        else:
            actual=record(value['source'],source);record(value['target'],target)
            if actual.strftime('%H:%M')!=wall_time:raise ToolError('mcp_protocol_invalid')
        text=json.dumps(snapshot,ensure_ascii=False,indent=2)
        if action=='convert':text='Konwersja dotyczy dzisiejszej daty w strefie źródłowej, nie przyszłej daty spotkania.\n'+text
        url='/api/v1/integrations/mcp-time/result?'+urlencode({'data':encode(snapshot)})
        return {'url':url,'title':'MCP · czas '+source,'text':text,'excerpt':text[:1200],'content_kind':'time_snapshot','truncated':False,'scope_note':'Wynik zegara w chwili odczytu. Link zachowuje ten wynik, nie odczytuje bieżącego czasu ponownie.'}
    finally:client.close()

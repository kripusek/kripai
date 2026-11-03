"""Eksport jednej rozmowy; jawne pola, spójny odczyt SQLite, bez zapisu plików.

JSON v1: conversation + messages; wiadomość zawiera attachments oraz sources.
Źródła mają kind W (narzędzia) albo D (własne dokumenty) i label W1/D1.
Integracja uwierzytelnionego pobierania należy do warstwy HTTP.
"""
from datetime import datetime,timezone
import json
import math
from uuid import UUID
from .db import open_db

MAX_BYTES=8*1024*1024
MAX_MESSAGES=10000


class ExportError(Exception):
    def __init__(self,code,status):
        super().__init__(code)
        self.code=code
        self.status=status


def _too_large():
    raise ExportError('conversation_export_too_large',413)


def _date(value):
    if not isinstance(value,(int,float)) or not math.isfinite(value):raise ExportError('conversation_export_invalid_data',500)
    try:return datetime.fromtimestamp(value,timezone.utc).isoformat().replace('+00:00','Z')
    except (ValueError,OverflowError,OSError,TypeError):raise ExportError('conversation_export_invalid_data',500) from None


def _bounded_query(conn,table,fields,where,args,order=''):
    # CASE nie przenosi do Pythona ogromnego tekstu przed sprawdzeniem limitu.
    columns=','.join('CASE WHEN length(CAST('+field+' AS BLOB))<=? THEN '+field+' ELSE NULL END AS '+field.split('.')[-1] for field in fields)
    query='SELECT '+columns+' FROM '+table+' WHERE '+where+(' ORDER BY '+order if order else '')
    for row in conn.execute(query,(*([MAX_BYTES]*len(fields)),*args)):
        if any(value is None for value in row.values()):_too_large()
        for name,value in row.items():
            if name in ('created_at','updated_at'):_date(value)
            elif name in ('ordinal','page','pages'):
                if not isinstance(value,int) or value<1:raise ExportError('conversation_export_invalid_data',500)
            elif not isinstance(value,str):raise ExportError('conversation_export_invalid_data',500)
        yield row


def render(cid:str,uid:str,format:str):
    """Zwróć body/media_type/filename albo ExportError; żaden tekst nie jest obcinany."""
    if format not in ('md','json'):raise ExportError('conversation_export_format',422)
    try:identity=str(UUID(str(cid)))
    except (ValueError,TypeError,AttributeError):raise ExportError('conversation_not_found',404) from None
    output=bytearray()
    def write(value):
        if not isinstance(value,str):raise ExportError('conversation_export_invalid_data',500)
        try:encoded=value.encode('utf-8')
        except UnicodeError:raise ExportError('conversation_export_invalid_data',500) from None
        if len(output)+len(encoded)>MAX_BYTES:_too_large()
        output.extend(encoded)
    encoder=json.JSONEncoder(ensure_ascii=False,separators=(',',':'),allow_nan=False)
    def json_value(value):
        try:
            for part in encoder.iterencode(value):write(part)
        except (ValueError,TypeError,UnicodeError):raise ExportError('conversation_export_invalid_data',500) from None
    conn=open_db()
    try:
        # Odczyt ze spójnego snapshotu bez blokady rezerwującej zapis.
        conn.execute('BEGIN')
        conversation=next(_bounded_query(conn,'conversations',('id','title','created_at','updated_at'),'id=? AND owner_id=?',(identity,uid)),None)
        if conversation is None:raise ExportError('conversation_not_found',404)
        if format=='json':
            write('{"version":1,"conversation":');json_value(conversation);write(',"messages":[')
        else:
            write('# '+conversation['title']+'\n\nRozmowa: '+identity+'\nUtworzono: '+_date(conversation['created_at'])+'\nZaktualizowano: '+_date(conversation['updated_at'])+'\n')
        count=0
        for message in _bounded_query(conn,'messages',('id','role','content','created_at'),'conversation_id=?',(identity,),'seq'):
            count+=1
            if count>MAX_MESSAGES:_too_large()
            mid=message['id']
            if format=='json':
                if count>1:write(',')
                write('{')
                for index,(key,value) in enumerate(message.items()):
                    if index:write(',')
                    json_value(key);write(':');json_value(value)
                write(',"attachments":[')
            else:write('\n## '+('Użytkownik' if message['role']=='user' else 'Asystent')+' · '+_date(message['created_at'])+'\n\n'+message['content']+'\n')
            first=True
            for item in _bounded_query(conn,'message_images i JOIN attachments a ON a.id=i.attachment_id',('a.id','a.filename','a.media_type','a.pages'),'i.message_id=? AND a.owner_id=?',(mid,uid)):
                if format=='json':
                    if not first:write(',')
                    json_value(item)
                else:write('\nZałącznik: '+item['filename']+' ('+item['id']+'), '+item['media_type']+'\n')
                first=False
            if format=='json':write('],"sources":[')
            first=True
            groups=(('W','tool_sources',('ordinal','name','url','title','excerpt'),'message_id=?',(mid,)),
                    ('D','message_sources s JOIN attachments a ON a.id=s.attachment_id',('s.ordinal','s.attachment_id','a.filename','s.page','s.excerpt'),'s.message_id=? AND a.owner_id=?',(mid,uid)))
            for kind,table,fields,where,args in groups:
                for source in _bounded_query(conn,table,fields,where,args,fields[0]):
                    source={'kind':kind,'label':kind+str(source['ordinal']),**source}
                    if format=='json':
                        if not first:write(',')
                        json_value(source)
                    else:
                        if first:write('\n### Źródła\n')
                        if kind=='W':write('\n['+source['label']+'] '+source['title']+'\nNarzędzie: '+source['name']+'\nURL: '+source['url']+'\n'+source['excerpt']+'\n')
                        else:write('\n['+source['label']+'] '+source['filename']+' ('+source['attachment_id']+'), strona '+str(source['page'])+'\n'+source['excerpt']+'\n')
                    first=False
            if format=='json':write(']}')
        if format=='json':write(']}')
        return {'body':bytes(output),'media_type':'application/json' if format=='json' else 'text/markdown; charset=utf-8','filename':'kripai-'+identity+'.'+format}
    finally:
        conn.rollback()
        conn.close()

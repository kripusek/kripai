"""Samodzielny serwer MCP stdio: tylko list_documents/read_document."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mcp_documents import document,catalog
from app.network import ToolError

PROTOCOL='2025-11-25'
TOOLS=[{'name':'list_documents','description':'List bundled KripAI Markdown documents.','inputSchema':{'type':'object','properties':{},'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False}},
       {'name':'read_document','description':'Read one bundled KripAI Markdown document.','inputSchema':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False}}]

def serve(root):
    initialized=False;ready=False
    for _ in range(64):
        line=sys.stdin.buffer.readline(65537)
        if not line:return
        if len(line)>65536 or not line.endswith(b'\n'):return
        request={}
        try:
            request=json.loads(line.decode('utf-8'))
            if not isinstance(request,dict) or request.get('jsonrpc')!='2.0':raise ValueError()
            method=request.get('method');params=request.get('params',{})
            if method=='notifications/initialized' and initialized:
                ready=True;continue
            if 'id' not in request:continue
            if method=='initialize' and not initialized:
                initialized=True;result={'protocolVersion':PROTOCOL,'capabilities':{'tools':{}},'serverInfo':{'name':'kripai-docs','version':'1.0.0'}}
            elif method=='ping' and initialized:result={}
            elif not ready:raise ValueError()
            elif method=='tools/list':result={'tools':TOOLS}
            elif method=='tools/call':
                try:
                    name=params['name'];args=params.get('arguments',{})
                    if name=='list_documents' and args=={}:data=catalog(root)
                    elif name=='read_document' and isinstance(args,dict) and set(args)=={'path'}:data=document(root,args['path'])
                    else:raise ToolError('mcp_tool_denied')
                    result={'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'isError':False}
                except ToolError as exc:result={'content':[{'type':'text','text':exc.code}],'isError':True}
            else:
                response={'jsonrpc':'2.0','id':request['id'],'error':{'code':-32601,'message':'Method not supported'}}
                sys.stdout.buffer.write(json.dumps(response).encode()+b'\n');sys.stdout.buffer.flush();continue
            response={'jsonrpc':'2.0','id':request['id'],'result':result}
        except (ValueError,KeyError,TypeError,UnicodeError):response={'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,'error':{'code':-32602,'message':'Invalid request'}}
        encoded=json.dumps(response,ensure_ascii=False).encode('utf-8')+b'\n'
        if len(encoded)>65536:return
        sys.stdout.buffer.write(encoded);sys.stdout.buffer.flush()

if __name__=='__main__':
    # Root jest argumentem stałego klienta, nigdy parametrem narzędzia/modelu.
    try:serve(Path(sys.argv[1]).resolve() if len(sys.argv)==2 else Path(__file__).resolve().parents[1])
    except Exception:sys.exit(4)

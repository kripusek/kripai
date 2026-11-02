"""Proces odczytu sieci: dane tylko z prywatnego pliku, nigdy polecenia shell."""
from pathlib import Path
import json
import os
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.network import execute,ToolError
from app.integrations import read

def main():
    deadline=time.monotonic()+10
    while not Path('job.ready').exists():
        if time.monotonic()>deadline:raise ValueError('job')
        time.sleep(.02)
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(8,8))
    request=Path('request.json')
    if request.stat().st_size>128000:raise ValueError('request')
    data=json.loads(request.read_text(encoding='utf-8'))
    try:result={'result':read(data['name'],data['arguments'],data['scope'])}
    except ToolError as exc:result={'error':exc.code}
    except Exception:result={'error':'tool_read_failed'}
    Path('result.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':
    try:main()
    except Exception:sys.exit(4)

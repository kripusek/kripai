"""Szybka ścieżka START: tylko ta sama, już działająca paczka."""
import json
from pathlib import Path
import re
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config
from app.build import fingerprint
from app.processes import InstanceLock

def locked():
    try:
        with InstanceLock():return False
    except RuntimeError:return True

def alive():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(config.ORIGIN+'/api/v1/health/live',timeout=2) as response:
        raw=response.read(1025)
        if response.status!=200 or len(raw)>1024:return False
        data=json.loads(raw)
        return isinstance(data,dict) and data.get('app')=='KripAI-native'

def can_reuse(source):
    try:
        root=config.ROOT
        if not (root/'.kripai-native').is_file():return False
        marker=config.DATA/'active-build.sha256'
        if marker.is_symlink() or getattr(marker.lstat(),'st_file_attributes',0)&0x400:return False
        with marker.open('rb') as stream:raw=stream.read(66)
        if not re.fullmatch(rb'[0-9a-f]{64}',raw):return False
        expected=raw.decode('ascii')
        # Odcisk powstał na starcie backendu, nie z aktualnie edytowanych plików.
        return locked() and expected==fingerprint(root)==fingerprint(source) and alive()
    except (OSError,ValueError,RuntimeError,urllib.error.URLError):return False

if __name__=='__main__':
    sys.exit(0 if len(sys.argv)==2 and can_reuse(Path(sys.argv[1])) else 1)

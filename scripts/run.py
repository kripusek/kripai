"""Backend i model zamykane jednym znacznikiem, bez zabijania obcych PID."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import threading
import time
import uvicorn
from app import config
from app.db import migrate
from app.maintenance import backup
from app.processes import InstanceLock


def main():
    with InstanceLock():
        migrate();backup()
        flag=config.DATA/'stop.request'
        server=uvicorn.Server(uvicorn.Config('app.main:app',host='127.0.0.1',port=config.PORT,
            access_log=False,proxy_headers=False,log_level='error',timeout_graceful_shutdown=5))
        done=threading.Event()
        def watch():
            last_backup=time.monotonic()
            while not done.wait(.5):
                if flag.exists():server.should_exit=True;return
                if time.monotonic()-last_backup>86400:
                    try:
                        backup();(config.DATA/'backup.error').unlink(missing_ok=True)
                    except Exception:(config.DATA/'backup.error').touch()
                    last_backup=time.monotonic()
        thread=threading.Thread(target=watch,daemon=True);thread.start()
        try:server.run()
        finally:
            done.set();thread.join(timeout=2)
            backup();flag.unlink(missing_ok=True)

if __name__=='__main__':
    try:main()
    except Exception:
        # Bez traceback zawierającego ścieżki sekretów lub dane żądań.
        print('KripAI nie uruchomiło się poprawnie. Uruchom START.cmd w oknie terminala.',file=sys.stderr)
        sys.exit(1)

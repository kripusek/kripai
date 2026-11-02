"""Operacje lokalnego właściciela Windows; nie są dostępne przez API/model."""
import getpass
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config
from app.db import connect,migrate
from app.maintenance import backup,restore,set_password,ensure_key
from app.processes import InstanceLock


def running():
    try:
        with InstanceLock():return False
    except RuntimeError:return True


def stop():
    config.DATA.mkdir(parents=True,exist_ok=True)
    (config.DATA/'stop.request').touch()
    if not running():return
    for _ in range(90):
        if not running():print('KripAI i model wyłączone.');return
        time.sleep(1)
    raise RuntimeError('Zamykanie przekroczyło czas. Nie zabijam obcych procesów; sprawdź Menedżer zadań.')


def ask_password():
    while True:
        password=getpass.getpass('Nowe haslo owner (minimum 14 znakow): ')
        if 14<=len(password)<=1024 and password==getpass.getpass('Powtorz haslo: '):return password
        print('Hasla musza byc jednakowe i miec 14–1024 znaki.')


def main(action):
    if action=='stop':stop();return
    if action=='backup':
        print('Kopia: '+str(backup()));return
    if action=='start':
        if running():print('KripAI jest już uruchomione.');return
        with InstanceLock():
            migrate()
            with connect() as conn:owner=conn.execute("SELECT 1 FROM users WHERE username='owner'").fetchone()
            if not owner:set_password(ask_password())
            ensure_key()
            (config.DATA/'stop.request').unlink(missing_ok=True)
        python=Path(sys.executable)
        if os.name=='nt':python=python.with_name('pythonw.exe')
        with (config.DATA/'startup.log').open('w') as log:
            process=subprocess.Popen([str(python),str(config.ROOT/'scripts/run.py')],cwd=config.ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
        import httpx
        for _ in range(60):
            if process.poll() is not None:raise RuntimeError('Backend zakończył się podczas startu. Sprawdź startup.log.')
            try:
                with httpx.Client(trust_env=False,timeout=1) as client:
                    r=client.get(config.ORIGIN+'/api/v1/health/live')
                    if running() and r.status_code==200 and r.json().get('app')=='KripAI-native':
                        print('Gotowe: '+config.ORIGIN);return
            except (httpx.HTTPError,ValueError):pass
            time.sleep(1)
        raise RuntimeError('Backend nie odpowiedział. Sprawdź, czy port 8765 jest wolny.')
    stop()
    with InstanceLock():
        if action=='reset':
            backup();set_password(ask_password());print('Hasło zmienione, poprzednie sesje unieważnione.')
        elif action=='restore':
            copies=sorted(config.BACKUPS.glob('kripai-*.sqlite3'),reverse=True)
            if not copies:raise RuntimeError('Brak kopii.')
            for i,p in enumerate(copies,1):print(str(i)+'. '+p.name)
            index=int(input('Numer kopii do przywrocenia (0 = anuluj): '))
            if index==0:return
            if not 1<=index<=len(copies):raise ValueError('Nieprawidłowy numer')
            restore(copies[index-1]);print('Przywrócono kopię. Zaloguj się hasłem z chwili jej wykonania.')
        else:raise ValueError('Nieznana operacja')

if __name__=='__main__':
    try:main(sys.argv[1])
    except (Exception,KeyboardInterrupt) as exc:
        print('Operacja przerwana: '+str(exc),file=sys.stderr);sys.exit(1)

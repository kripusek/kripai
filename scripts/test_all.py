"""Jedno polecenie testuje wszystkie moduły bez używania prywatnej bazy/modelu."""
import os
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
import sys
import unittest
import sqlite3
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class Tee:
    def __init__(self,*streams):self.streams=streams
    def write(self,value):
        for stream in self.streams:stream.write(value);stream.flush()
    def isatty(self):return False
    def flush(self):
        for stream in self.streams:stream.flush()

if __name__=='__main__':
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    with (reports/'tests-latest.txt').open('w',encoding='utf-8') as log:
        stream=Tee(sys.stdout,log)
        stream.write('Python '+sys.version.split()[0]+' / '+sys.platform+' / SQLite '+sqlite3.sqlite_version+'\n')
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        with redirect_stdout(stream),redirect_stderr(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        stream.write('Modele HTTP/STT/TTS/VLM: atrapy w testach przenosnych; dekodery PNG/JPEG/PDF: prawdziwe; baza: prawdziwy SQLite; procesy: prawdziwe procesy potomne.\n')
        stream.write('NIE URUCHOMIONO w tym zestawie: prawdziwy llama-server CUDA, pobranie 5 GB, instalacja/odinstalowanie Windows, mikrofon i wizualny test przegladarki. Test System.Speech jest pomijany poza Windows lub przy braku glosow.\n')
    sys.exit(0 if result.wasSuccessful() else 1)

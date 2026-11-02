"""Sprawdzenia specyficzne dla Windows. Linux nie może ich zaliczyć."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.processes import ModelJob

@unittest.skipUnless(os.name=='nt','NIE URUCHOMIONO: wymaga natywnego Windows')
class WindowsTests(unittest.TestCase):
    def test_job_close_really_kills_child(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
        job=ModelJob()
        try:
            job.attach(child);job.close()
            child.wait(timeout=5)
            self.assertIsNotNone(child.poll())
        finally:
            job.close()
            if child.poll() is None:child.kill();child.wait()
    def test_decoder_job_enforces_memory_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            code="""from pathlib import Path
import time
while not Path('ready').exists():time.sleep(.01)
try:
    data=bytearray(512*1024**2)
except MemoryError:
    Path('limited').touch()
"""
            child=subprocess.Popen([sys.executable,'-c',code],cwd=folder)
            job=ModelJob(memory_limit=128*1024**2)
            try:
                job.attach(child);(folder/'ready').touch();child.wait(timeout=10)
                self.assertEqual(child.returncode,0)
                self.assertTrue((folder/'limited').exists())
            finally:
                job.close()
                if child.poll() is None:child.kill();child.wait()

    def test_powershell_scripts_parse(self):
        root=Path(__file__).resolve().parents[1]
        code="param($root); $failed=$false; Get-ChildItem -LiteralPath $root -Filter *.ps1 | ForEach-Object { $tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors) | Out-Null; if ($errors.Count) { $failed=$true; $errors | ForEach-Object { Write-Output $_.Message } } }; if ($failed) { exit 1 }"
        with tempfile.TemporaryDirectory() as temp:
            script=Path(temp)/'parse.ps1';script.write_text(code,encoding='utf-8-sig')
            result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(root/'scripts')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_system_speech_generates_local_wav_when_voice_installed(self):
        import json
        import wave
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for language,text in [('pl','To jest lokalny test głosu.'),('en','This is a local voice test.')]:
                (folder/'request.json').write_text(json.dumps({'language':language,'text':text}),encoding='utf-8')
                result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                    '-File',str(root/'scripts/speak.ps1'),'-InputFile',str(folder/'request.json'),
                    '-OutputFile',str(folder/'speech.wav')],capture_output=True,timeout=45)
                if result.returncode==3:continue
                self.assertEqual(result.returncode,0,'System.Speech nie wygenerował WAV')
                with wave.open(str(folder/'speech.wav'),'rb') as wav:self.assertGreater(wav.getnframes(),0)
                return
            self.skipTest('NIE URUCHOMIONO: brak zainstalowanego głosu System.Speech PL/EN')

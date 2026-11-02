"""API głosu: prawdziwy SQLite i procesy; sam STT/TTS zastępuje mały proces testowy."""
import concurrent.futures
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
from unittest.mock import patch
from uuid import uuid4
import wave

from fastapi.testclient import TestClient
from app import config, main, voice
from app.db import connect
from test_native import DataCase, PASSWORD


def wav(samples=8000):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as f:
        f.setparams((1, 2, 16000, samples, 'NONE', 'not compressed'))
        f.writeframes(b'\x01\x00'*samples)
    return buffer.getvalue()


class VoiceTests(DataCase):
    def test_small_model_selected_without_silent_base_fallback(self):
        root=config.DATA/'program'
        executable=root/'runtime/whisper'/voice.VOICE_RELEASE/'whisper-cli.exe'
        executable.parent.mkdir(parents=True);executable.write_bytes(b'test')
        models=config.DATA/'models';models.mkdir()
        (models/'ggml-base.bin').write_bytes(b'old model')
        with patch.object(config,'ROOT',root):
            with self.assertRaises(voice.VoiceError) as raised:
                voice.stt_command(config.DATA,'pl')
            self.assertEqual(raised.exception.code,'stt_not_installed')
            (models/voice.STT_MODEL).write_bytes(b'new model')
            command=voice.stt_command(config.DATA,'pl')
            self.assertEqual(command[command.index('--model')+1],str(models/'ggml-small.bin'))
            self.assertEqual(command[command.index('--language')+1],'pl')
            self.assertIn('--no-gpu',command)
        manifest=json.loads((config.ROOT/'scripts/voice-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['model']['name'],voice.STT_MODEL)

    def setUp(self):
        super().setUp()
        self.service = voice.VoiceService()
        self.stack.enter_context(patch.object(voice, 'service', self.service))
        self.addCleanup(self.service.shutdown)
        self.client = TestClient(main.app, base_url=config.ORIGIN)
        self.addCleanup(self.client.close)
        self.client.headers['Origin'] = config.ORIGIN
        self.client.post('/api/v1/auth/login', json={'username':'owner','password':PASSWORD})
        self.client.headers['X-CSRF-Token'] = self.client.cookies.get('assistant_csrf')
        with connect() as c:
            session = c.execute('SELECT id,user_id FROM sessions').fetchone()
        self.key = (session['id'], session['user_id'], str(uuid4()))

    def child(self, folder, delay=0, result='tekst rozpoznany', exit_code=0):
        # Zwykły proces Python potwierdza PID i wykonuje kontrolowane zakończenie.
        code = ("from pathlib import Path; import os,time; "
                "Path('pid').write_text(str(os.getpid())); "
                f"time.sleep({delay}); Path('result.txt').write_text({result!r},encoding='utf-8'); "
                f"raise SystemExit({exit_code})")
        return [sys.executable, '-c', code]

    def install_fake_stt(self, delay=0, exit_code=0):
        self.stack.enter_context(patch.object(voice, 'stt_command',
            lambda folder, language:self.child(folder, delay, 'Zażółć gęślą jaźń.', exit_code)))

    def post_audio(self, data=None, jid=None, **kwargs):
        return self.client.post('/api/v1/voice/jobs/'+(jid or str(uuid4()))+'/transcribe',
            content=wav() if data is None else data, headers={'Content-Type':'audio/wav'}, **kwargs)

    def started(self):
        for _ in range(200):
            paths = list((config.DATA/'voice-tmp').glob('job-*/pid'))
            if paths:
                return paths[0]
            time.sleep(.01)
        self.fail('Proces głosu nie wystartował')

    def test_pcm_accepts_boundary_and_rejects_truncation_format_and_duration(self):
        self.assertEqual(voice.validate_wav(wav(480000)), wav(480000))
        for data in (wav(3999), wav(480001), wav()[:-2], b'not wav'*2000,
                     wav()[:24]+struct.pack('<I',48000)+wav()[28:]):
            with self.assertRaises(voice.VoiceError): voice.validate_wav(data)

    def test_transcript_real_process_unicode_cleanup_and_no_auto_send(self):
        self.install_fake_stt()
        response=self.post_audio()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['text'],'Zażółć gęślą jaźń.')
        self.assertFalse(list((config.DATA/'voice-tmp').iterdir()))
        with connect() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],0)

    def test_upload_auth_csrf_origin_size_and_content_type(self):
        path='/api/v1/voice/jobs/'+str(uuid4())+'/transcribe'
        anonymous=TestClient(main.app,base_url=config.ORIGIN)
        try:
            self.assertEqual(anonymous.post(path,content=wav(),headers={'Origin':config.ORIGIN}).status_code,401)
        finally:anonymous.close()
        self.assertEqual(self.client.post(path,content=wav(),headers={'X-CSRF-Token':''}).status_code,403)
        self.assertEqual(self.client.post(path,content=wav(),headers={'Origin':'https://foreign.invalid'}).status_code,403)
        self.assertEqual(self.client.post(path,content=b'x'*(voice.MAX_AUDIO+1)).status_code,413)
        self.assertEqual(self.client.post(path,content=iter([b'x'*500000,b'y'*500000])).status_code,413)
        self.assertEqual(self.client.post(path,content=wav(),headers={'Content-Type':'audio/webm'}).status_code,415)
        self.assertEqual(self.client.post('/api/v1/conversations',content=b'x'*17000).status_code,413)

    def test_cancel_before_start_prevents_execution_and_retry(self):
        self.install_fake_stt()
        jid=str(uuid4());path='/api/v1/voice/jobs/'+jid
        self.assertEqual(self.client.post(path+'/cancel').status_code,204)
        self.assertEqual(self.post_audio(jid=jid).status_code,409)
        self.assertFalse((config.DATA/'voice-tmp').exists())

    def test_cancel_kills_real_child_cleans_files_and_recovers(self):
        self.install_fake_stt(delay=30)
        jid=str(uuid4())
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(self.post_audio,jid=jid)
            pid_file=self.started();pid=int(pid_file.read_text())
            self.assertEqual(self.client.post('/api/v1/voice/jobs/'+jid+'/cancel').status_code,204)
            self.assertEqual(pending.result(timeout=5).status_code,409)
        self.assertFalse(pid_file.exists())
        # wait() w serwisie nie wraca zanim proces potomny faktycznie się zakończy.
        self.assertIsNone(self.service.active)
        with patch.object(voice,'stt_command',lambda folder,language:self.child(folder)):
            self.assertEqual(self.post_audio().status_code,200)

    def test_busy_and_other_session_cannot_cancel_job(self):
        self.install_fake_stt(delay=.5)
        jid=str(uuid4())
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending=pool.submit(self.post_audio,jid=jid);self.started()
            self.assertEqual(self.post_audio().status_code,409)
            self.service.cancel(('foreign-session', self.key[1], jid))
            self.assertEqual(pending.result(timeout=5).status_code,200)

    def test_gaming_logout_and_shutdown_interrupt_real_process(self):
        self.install_fake_stt(delay=30)
        for cause in ('gaming','logout','shutdown'):
            with self.subTest(cause=cause), concurrent.futures.ThreadPoolExecutor() as pool:
                pending=pool.submit(self.post_audio);self.started()
                if cause=='gaming':
                    with connect() as c:c.execute("UPDATE system_mode SET requested_mode='gaming'")
                elif cause=='logout':
                    with connect() as c:c.execute('UPDATE sessions SET revoked_at=now()')
                else:self.service.shutdown()
                self.assertIn(pending.result(timeout=5).status_code,(401,409))
            with connect() as c:
                c.execute("UPDATE system_mode SET requested_mode='normal'")
                c.execute('UPDATE sessions SET revoked_at=NULL')
            self.assertFalse(list((config.DATA/'voice-tmp').iterdir()))

    def test_timeout_and_engine_failure_are_explicit(self):
        folder=config.DATA/'child';folder.mkdir()
        import threading
        with self.assertRaises(voice.VoiceError) as raised:
            self.service.process(self.child(folder,delay=30),folder,self.key,threading.Event(),.15)
        self.assertEqual(raised.exception.code,'voice_timeout')
        self.install_fake_stt(exit_code=4)
        response=self.post_audio()
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['error']['code'],'voice_engine_failed')
        self.assertFalse(list((config.DATA/'voice-tmp').iterdir()))

    def test_speech_wav_and_plain_text_not_shell(self):
        captured=[]
        def command(folder,language,text):
            captured.append((language,text))
            code="from pathlib import Path; Path('speech.wav').write_bytes("+repr(wav())+")"
            # Dane dźwięku zapisane w pliku skryptu, aby nie przekroczyć limitu argv Windows.
            script=folder/'fake.py';script.write_text(code)
            return [sys.executable,str(script)]
        with patch.object(voice,'tts_command',command):
            text='$(Remove-Item example) <speak>Zażółć</speak>'
            response=self.client.post('/api/v1/voice/jobs/'+str(uuid4())+'/speak',json={'text':text,'language':'pl'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.content,wav());self.assertEqual(captured,[('pl',text)])
        folder=config.DATA/'cmd';folder.mkdir()
        with patch.object(voice,'powershell',return_value='powershell.exe'):
            argv=voice.tts_command(folder,'pl',text)
        self.assertNotIn(text,argv)
        self.assertEqual(json.loads((folder/'request.json').read_text(encoding='utf-8'))['text'],text)

    def test_missing_voice_and_invalid_language_and_text(self):
        with patch.object(voice,'tts_command',lambda folder,lang,text:self.child(folder,exit_code=3)):
            response=self.client.post('/api/v1/voice/jobs/'+str(uuid4())+'/speak',json={'text':'test','language':'pl'})
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['error']['code'],'tts_voice_missing')
        for body in ({'text':'x'*1201,'language':'pl'}, {'text':'test','language':'../../evil'}):
            self.assertEqual(self.client.post('/api/v1/voice/jobs/'+str(uuid4())+'/speak',json=body).status_code,422)

    def test_restart_removes_orphaned_audio_without_touching_database(self):
        folder=config.DATA/'voice-tmp/job-orphan';folder.mkdir(parents=True)
        (folder/'input.wav').write_bytes(wav())
        self.service.reset()
        self.assertFalse(folder.exists())
        with connect() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM users').fetchone()['n'],1)

    def test_missing_engine_and_bad_output_do_not_look_like_success(self):
        with patch.object(config,'ROOT',config.DATA/'no-program'):
            response=self.post_audio()
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['error']['code'],'stt_not_installed')
        with patch.object(voice,'stt_command',lambda folder,lang:self.child(folder,result='')):
            self.assertEqual(self.post_audio().json()['error']['code'],'speech_not_detected')
        self.assertFalse(list((config.DATA/'voice-tmp').iterdir()))

    def test_download_installs_pinned_layout_and_rejects_missing_executable(self):
        import zipfile
        from scripts import downloads
        root=config.DATA/'package';(root/'scripts').mkdir(parents=True)
        (root/'runtime/cache').mkdir(parents=True)
        meta={'release':'test','binary':{'name':'voice.zip'},'model':{'name':'model.bin'}}
        (root/'scripts/voice-lock.json').write_text(json.dumps(meta))
        archive=root/'runtime/cache/voice.zip'
        with patch.object(downloads,'ROOT',root),patch.object(downloads,'download',side_effect=lambda item,target: archive):
            with zipfile.ZipFile(archive,'w') as z:z.writestr('Release/engine.dll',b'test')
            with self.assertRaises(RuntimeError):downloads.voice_files()
            self.assertFalse((root/'runtime/whisper/test/release.json').exists())
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('Release/whisper-cli.exe',b'test executable')
                z.writestr('Release/engine.dll',b'test library')
            downloads.voice_files()
            self.assertEqual((root/'runtime/whisper/test/whisper-cli.exe').read_bytes(),b'test executable')
            self.assertEqual((root/'runtime/whisper/test/engine.dll').read_bytes(),b'test library')

"""Szybki START sprawdza tę samą paczkę i działający backend; brak inference."""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
from app import build,config
from scripts import reuse_running

class ReuseRunningTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);base=Path(temp.name)
        self.root=base/'installed';self.root.mkdir()
        for name in build.FOLDERS:(self.root/name).mkdir()
        (self.root/'app/main.py').write_text('program')
        (self.root/'scripts/vendor-lock.json').write_text('[]')
        (self.root/'.kripai-native').touch()
        self.source=base/'source';shutil.copytree(self.root,self.source)
        self.data=base/'data';self.data.mkdir();self.stamp=self.data/'active-build.sha256'
        self.stamp.write_text(build.fingerprint(self.root),encoding='ascii')
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(config,'ROOT',self.root));stack.enter_context(patch.object(config,'DATA',self.data))
    def test_code_name_and_lock_changes_invalidate_but_private_data_do_not(self):
        before=build.fingerprint(self.root)
        (self.root/'runtime').mkdir();(self.root/'runtime/secret.key').write_text('fixture')
        (self.root/'app/__pycache__').mkdir();(self.root/'app/__pycache__/main.pyc').write_bytes(b'compiled')
        self.assertEqual(build.fingerprint(self.root),before)
        path=self.root/'app/main.py';path.rename(path.with_name('renamed.py'))
        self.assertNotEqual(build.fingerprint(self.root),before)
        path.with_name('renamed.py').rename(path)
        (self.root/'scripts/vendor-lock.json').write_text('[1]')
        self.assertNotEqual(build.fingerprint(self.root),before)
    def test_same_source_and_running_build_required_even_when_both_dirs_edited(self):
        with patch.object(reuse_running,'locked',return_value=True),patch.object(reuse_running,'alive',return_value=True):
            self.assertTrue(reuse_running.can_reuse(self.source))
            (self.source/'app/main.py').write_text('new program');self.assertFalse(reuse_running.can_reuse(self.source))
            (self.root/'app/main.py').write_text('new program');self.assertFalse(reuse_running.can_reuse(self.source))
    def test_missing_invalid_stamp_unlocked_or_dead_service_never_reuse(self):
        with patch.object(reuse_running,'locked',return_value=False),patch.object(reuse_running,'alive',side_effect=AssertionError('no request')):
            self.assertFalse(reuse_running.can_reuse(self.source))
        with patch.object(reuse_running,'locked',return_value=True),patch.object(reuse_running,'alive',return_value=False):
            self.assertFalse(reuse_running.can_reuse(self.source))
            for raw in [b'',b'0'*65,b'invalid']:
                self.stamp.write_bytes(raw);self.assertFalse(reuse_running.can_reuse(self.source))
            self.stamp.unlink();self.assertFalse(reuse_running.can_reuse(self.source))
    def test_missing_directory_and_oversized_program_fail_closed(self):
        (self.root/'web').rmdir()
        with self.assertRaises(OSError):build.fingerprint(self.root)
        (self.root/'web').mkdir();(self.root/'web/large.js').write_bytes(b'x'*(2*1024**2+1))
        with self.assertRaises(ValueError):build.fingerprint(self.root)
    def test_real_http_probe_rejects_wrong_app_oversize_arrays_and_redirect(self):
        class Handler(BaseHTTPRequestHandler):
            content=b'{"app":"KripAI-native"}';status=200;requests=0
            def log_message(self,*args):pass
            def do_GET(self):
                Handler.requests+=1;self.send_response(Handler.status)
                if Handler.status==302:self.send_header('Location','http://127.0.0.1:'+str(self.server.server_port)+'/unexpected')
                self.end_headers();self.wfile.write(Handler.content)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        with patch.object(config,'ORIGIN','http://127.0.0.1:'+str(server.server_port)),patch.object(reuse_running,'locked',return_value=True):
            self.assertTrue(reuse_running.can_reuse(self.source))
            for content in [b'{"app":"other"}',b'x'*1025,b'[]',b'not json']:
                Handler.content=content;self.assertFalse(reuse_running.can_reuse(self.source))
            Handler.status=302;before=Handler.requests
            self.assertFalse(reuse_running.can_reuse(self.source));self.assertEqual(Handler.requests,before+1)

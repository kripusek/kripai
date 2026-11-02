import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import downloads
from import_history import import_rows
from test_native import DataCase
from app import config
from app.db import connect
from app.model_process import ModelProcess

class ProcessTests(unittest.TestCase):
    def test_text_profile_uses_same_bounded_cache_after_vision_switch(self):
        manager=ModelProcess()
        try:
            self.assertEqual(manager.command,manager.command_for('text'))
            for option,value in [('--ctx-size','4096'),('--flash-attn','on'),('--cache-type-k','q8_0'),('--cache-type-v','q8_0')]:
                self.assertEqual(manager.command[manager.command.index(option)+1],value)
            self.assertNotIn('--cache-type-v',manager.command_for('vision'))
            self.assertEqual(manager.command[manager.command.index('--parallel')+1],'1')
        finally:manager.close()
    def test_real_child_stops_and_restarts_on_toggle(self):
        manager=ModelProcess(command=[sys.executable,'-c','import time;time.sleep(60)'],health=lambda:True)
        try:
            self.assertEqual(manager.step('normal'),'ready');first=manager.process
            self.assertIsNone(first.poll())
            self.assertEqual(manager.step('gaming'),'stopped');self.assertIsNotNone(first.poll())
            self.assertEqual(manager.step('normal'),'ready');self.assertNotEqual(first.pid,manager.process.pid)
        finally:manager.close()
    def test_missing_binary_reports_error_without_success(self):
        manager=ModelProcess(command=['/nonexistent/kripai-missing-program.exe'],health=lambda:True)
        try:self.assertEqual(manager.step('normal'),'error');self.assertIsNone(manager.process)
        finally:manager.close()
    def test_loading_timeout_kills_child_and_reports_error(self):
        clock=[0];manager=ModelProcess(command=[sys.executable,'-c','import time;time.sleep(60)'],health=lambda:False,clock=lambda:clock[0])
        try:
            self.assertEqual(manager.step('normal'),'starting');child=manager.process
            clock[0]=181;self.assertEqual(manager.step('normal'),'error');self.assertIsNotNone(child.poll())
        finally:manager.close()
    def test_crash_detected_and_backoff_applied(self):
        manager=ModelProcess(command=[sys.executable,'-c','raise SystemExit(3)'],health=lambda:False)
        try:
            manager.step('normal');manager.process.wait(timeout=5)
            self.assertEqual(manager.step('normal'),'error');self.assertEqual(manager.step('normal'),'error')
        finally:manager.close()
    def test_unknown_mode_cannot_become_shell_command(self):
        manager=ModelProcess()
        try:
            with self.assertRaises(ValueError):manager.step('normal & calc.exe')
            self.assertIsNone(manager.process)
        finally:manager.close()

class DownloadTests(unittest.TestCase):
    def test_extract_and_traversal_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'file.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('ok/file.txt','ok')
            downloads.extract(archive,root/'dest');self.assertEqual((root/'dest/ok/file.txt').read_text(),'ok')
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','bad')
            with self.assertRaises(ValueError):downloads.extract(archive,root/'dest')
            self.assertFalse((root/'escape').exists())
    def test_existing_verified_file_no_network_and_corrupt_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model';path.write_bytes(b'correct')
            meta={'url':'https://example.invalid/model','sha256':downloads.sha256(path)}
            with patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('network')):
                downloads.download(meta,path)
                path.write_bytes(b'broken')
                with self.assertRaises(RuntimeError):downloads.download(meta,path)
    def test_corrupt_download_never_renamed_to_model(self):
        class Response(io.BytesIO):
            status=200;headers={}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model'
            with patch.object(downloads.urllib.request,'urlopen',return_value=Response(b'wrong')):
                with self.assertRaises(RuntimeError):downloads.download({'url':'https://example.invalid/model','sha256':'0'*64},path)
            self.assertFalse(path.exists());self.assertFalse(path.with_suffix('.part').exists())
    def test_resumed_download_checks_content_range(self):
        class Response(io.BytesIO):
            status=206;headers={'Content-Range':'bytes 0-5/6'}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model';path.with_suffix('.part').write_bytes(b'ab')
            with patch.object(downloads.urllib.request,'urlopen',return_value=Response(b'cdef')):
                with self.assertRaises(RuntimeError):downloads.download({'url':'https://example.invalid/model','sha256':'0'*64},path)
            self.assertFalse(path.exists())

class ImportTests(DataCase):
    def rows(self):
        from uuid import uuid4
        return [({'id':str(uuid4()),'title':'stara rozmowa','created_at':'2026-10-01T10:00:00Z'},[{'id':str(uuid4()),'role':'user','content':'stara wiadomość','created_at':'2026-10-01T10:00:01Z'}])]
    def test_import_and_retry_preserve_history(self):
        rows=self.rows();import_rows(rows);import_rows(rows)
        with connect() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],1)
            self.assertEqual(c.execute('SELECT content FROM messages').fetchone()['content'],'stara wiadomość')
    def test_conflict_rolls_back_all_changes(self):
        rows=self.rows();import_rows(rows)
        rows[0][1][0]['content']='zmiana'
        with self.assertRaises(ValueError):import_rows(self.rows()+rows)
        with connect() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM conversations').fetchone()['n'],1)
    def test_invalid_role_not_imported(self):
        rows=self.rows();rows[0][1][0]['role']='system'
        with self.assertRaises(ValueError):import_rows(rows)
        with connect() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM messages').fetchone()['n'],0)

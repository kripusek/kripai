"""Granice IPC i rzeczywiste kończenie procesu; inference tutaj jest atrapą."""
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from app import config,visual_encoder as encoder


class EncoderTests(unittest.TestCase):
    def test_vectors_are_finite_normalized_and_keep_dimensions(self):
        packed=encoder.encode([1.]*768)
        values=struct.unpack('<768f',packed)
        self.assertEqual(len(packed),3072)
        self.assertAlmostEqual(sum(value*value for value in values),1.,places=6)
        for values in [None,[1.]*767,[0.]*768,[math.nan]*768,[math.inf]*768,[True]*768,['1']*768]:
            with self.subTest(kind=str(type(values))),self.assertRaises(encoder.VisualError):encoder.encode(values)

    def test_bad_inputs_do_not_write_ipc_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);model=encoder.Encoder(folder,None,lambda:None)
            for text in ['', ' '*10, 'x'*501, None]:
                with self.assertRaises(encoder.VisualError):model.embed_text(text)
            for image in [b'',b'not PNG',b'\x89PNG\r\n\x1a\n'+b'x'*(4*1024**2),None]:
                with self.assertRaises(encoder.VisualError):model.embed_image(image)
            self.assertEqual(list(folder.iterdir()),[])

    def test_bounded_response_corruption_and_worker_exit_are_errors(self):
        class Process:
            def poll(self):return None
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);model=encoder.Encoder(folder,Process(),lambda:None)
            for content in [b'{',b'x'*65537]:
                (folder/'response.json').write_bytes(content)
                with self.assertRaises(encoder.VisualError):model.wait('response.json',.1)
            (folder/'response.json').unlink()
            with self.assertRaises(encoder.VisualError) as error:model.wait('response.json',0)
            self.assertEqual(error.exception.code,'visual_encoder_timeout')
            with patch.object(Process,'poll',return_value=4),self.assertRaises(encoder.VisualError) as error:model.wait('response.json',1)
            self.assertEqual(error.exception.code,'visual_encoder_failed')

    def test_worker_error_is_allowlisted_and_vector_is_validated(self):
        class Process:
            def poll(self):return None
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);model=encoder.Encoder(folder,Process(),lambda:None)
            for response,expected in [({'error':'visual_query_too_large'},'visual_query_too_large'),({'embedding':[0.]*768},'visual_vector_invalid'),({'error':'private path or token'},'visual_vector_invalid')]:
                with patch.object(model,'wait',return_value=response):
                    (folder/'response.json').write_bytes(b'{}')
                    with self.assertRaises(encoder.VisualError) as error:model.embed_text('test')
                    self.assertEqual(error.exception.code,expected)

    def test_real_child_waits_for_job_and_is_killed_on_cancel_without_env_secrets(self):
        from scripts import setup_visual
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts').mkdir();data=root/'data'
            script='''import json,os,time
from pathlib import Path
while not Path('job.ready').exists():time.sleep(.01)
Path('environment.json').write_text(json.dumps(dict(os.environ)))
Path('ready.json').write_text('{"ready":true}')
while True:time.sleep(.05)
'''
            (root/'scripts/visual_worker.py').write_bytes(script.encode())
            children=[];original=subprocess.Popen
            def launch(*args,**kwargs):
                process=original(*args,**kwargs);children.append(process);return process
            with patch.object(config,'ROOT',root),patch.object(config,'DATA',data),patch.object(setup_visual,'installed',return_value=root/'runtime'),patch.object(encoder.subprocess,'Popen',side_effect=launch),patch.dict(os.environ,{'GITHUB_TOKEN':'test-secret-not-in-child','OPENAI_API_KEY':'another-test-secret'}):
                with self.assertRaises(encoder.VisualError) as error:
                    with encoder.session(lambda:None) as model:
                        environment=json.loads((model.folder/'environment.json').read_text())
                        self.assertNotIn('GITHUB_TOKEN',environment);self.assertNotIn('OPENAI_API_KEY',environment)
                        self.assertTrue(model.process.poll() is None)
                        raise encoder.VisualError('visual_paused')
                self.assertEqual(error.exception.code,'visual_paused')
            self.assertTrue(children and all(child.poll() is not None for child in children))
            self.assertEqual(list((data/'visual-tmp').iterdir()),[])

    def test_missing_installation_never_launches_process(self):
        from scripts import setup_visual
        with patch.object(setup_visual,'installed',return_value=None),patch.object(encoder.subprocess,'Popen',side_effect=AssertionError('No process')):
            with self.assertRaises(encoder.VisualError) as error:
                with encoder.session(lambda:None):pass
            self.assertEqual(error.exception.code,'visual_not_installed')

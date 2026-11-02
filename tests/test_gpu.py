import os,subprocess,sys,unittest
from unittest.mock import patch
from app import gpu
import test_native

class GpuTests(unittest.TestCase):
    def setUp(self):gpu.reset();self.addCleanup(gpu.reset)
    def test_csv_realistic_reserved_memory_and_validation(self):
        result=gpu.parse(b'0, NVIDIA RTX fixture, 7123, 8192, 902\n')
        self.assertEqual(result['devices'][0]['free_mib'],902)
        for raw in [b'',b'0, GPU, N/A, 8192, 0',b'0, GPU, 9000, 8192, 0',b'0, GPU, 1, 8192, -1',b'0, GPU, 1, 8192',b'x'*16385,b'0, GPU, 1, 8192, 8000\n0, Other, 1, 8192, 8000']:
            with self.subTest(raw=raw[:30]),self.assertRaises(ValueError):gpu.parse(raw)
    def test_real_probe_child_and_failure_timeout_are_explicit(self):
        commands=[[sys.executable,'-c',"print('0, GPU fixture, 100, 8192, 8092')"],[sys.executable,'-c','raise SystemExit(3)'],[sys.executable,'-c','import time;time.sleep(30)']]
        original=subprocess.Popen;children=[]
        def launch(*args,**kwargs):
            child=original(*args,**kwargs);children.append(child);return child
        with patch.object(gpu.subprocess,'Popen',side_effect=launch):
            for command,error in zip(commands,[None,'gpu_driver_unavailable','gpu_probe_timeout']):
                with patch.object(gpu,'command',return_value=command):result=gpu.probe()
                if error:self.assertFalse(result['available']);self.assertEqual(result['error'],error)
                else:self.assertTrue(result['available'])
        self.assertTrue(all(child.poll() is not None for child in children))
    def test_missing_provider_and_cached_copy_never_fake_free_memory(self):
        with patch.object(gpu,'command',return_value=None),patch.object(gpu.subprocess,'run',side_effect=AssertionError('no subprocess')):
            self.assertFalse(gpu.probe()['available'])
        clock=[0];fixture=gpu.parse(b'0, GPU fixture, 100, 8192, 8092')
        with patch.object(gpu,'probe',return_value=fixture) as probe,patch.object(gpu.time,'monotonic',side_effect=lambda:clock[0]):
            first=gpu.snapshot();first['devices'][0]['name']='modified'
            self.assertEqual(gpu.snapshot()['devices'][0]['name'],'GPU fixture');self.assertEqual(probe.call_count,1)
            clock[0]=6;gpu.snapshot();self.assertEqual(probe.call_count,2)
    def test_api_requires_session_and_returns_unavailable_without_driver(self):
        base=test_native.APITests('runTest');self.addCleanup(base.doCleanups);base.setUp()
        with patch.object(gpu,'probe',return_value={'available':False,'error':'gpu_probe_unavailable'}) as probe:
            response=base.client.get('/api/v1/system/gpu');self.assertEqual(response.status_code,200)
            self.assertFalse(response.json()['available']);self.assertEqual(response.json()['context_tokens'],4096)
            self.assertEqual(response.json()['output_tokens_per_segment'],2048)
            self.assertEqual(base.client.get('/api/v1/system/gpu',headers={'Host':'evil.example'}).status_code,400)
            base.client.cookies.clear();self.assertEqual(base.client.get('/api/v1/system/gpu').status_code,401)
            self.assertEqual(probe.call_count,1)

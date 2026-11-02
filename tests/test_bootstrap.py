"""Instalacja z repo bez binarnego vendor: prawdziwe pliki, kontrolowane HTTP."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import downloads

class Response(io.BytesIO):
    status=200
    headers={}

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'scripts').mkdir()
        content=io.BytesIO()
        with zipfile.ZipFile(content,'w') as archive:archive.writestr('fake/__init__.py','VALUE = 42')
        self.wheel=content.getvalue()
        self.item={'name':'fake-1.0-py3-none-any.whl','sha256':hashlib.sha256(self.wheel).hexdigest()}
        (self.root/'scripts/vendor-lock.json').write_text(json.dumps([self.item]))
        self.meta={'filename':self.item['name'],'digests':{'sha256':self.item['sha256']},'url':'https://files.pythonhosted.org/packages/test/'+self.item['name']}
    def http(self,request,timeout):
        url=request if isinstance(request,str) else request.full_url
        if url=='https://pypi.org/pypi/fake/1.0/json':return Response(json.dumps({'urls':[self.meta]}).encode())
        if url==self.meta['url']:return Response(self.wheel)
        self.fail('Niespodziewane żądanie: '+url)
    def test_source_install_downloads_exact_wheel_and_next_start_is_offline(self):
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=self.http) as http:
            downloads.dependencies();self.assertEqual(http.call_count,2)
            self.assertEqual((self.root/'runtime/deps/fake/__init__.py').read_text(),'VALUE = 42')
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('network')):
            downloads.dependencies()
    def test_hash_mismatch_metadata_and_untrusted_host_never_install(self):
        for field,value in [('digests',{'sha256':'0'*64}),('url','http://files.pythonhosted.org/packages/x'),('url','https://evil.example/packages/x'),('url','https://files.pythonhosted.org@evil.example/packages/x')]:
            with self.subTest(field=field,value=value):
                asset=dict(self.meta);asset[field]=value
                with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',return_value=Response(json.dumps({'urls':[asset]}).encode())):
                    with self.assertRaises(RuntimeError):downloads.dependencies()
                self.assertFalse((self.root/'runtime/deps/fake/__init__.py').exists())
    def test_failed_or_corrupt_transfer_can_retry_without_installing_partial_wheel(self):
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=OSError('offline')):
            with self.assertRaises(OSError):downloads.dependencies()
        good=self.wheel;self.wheel=b'broken'
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=self.http):
            with self.assertRaises(RuntimeError):downloads.dependencies()
        self.assertFalse((self.root/'vendor'/self.item['name']).exists())
        self.assertFalse(list((self.root/'vendor').glob('*.part')))
        self.wheel=good
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=self.http):downloads.dependencies()
        self.assertTrue((self.root/'runtime/deps/fake/__init__.py').exists())
    def test_corrupt_existing_vendor_is_preserved_and_rejected_without_network(self):
        (self.root/'vendor').mkdir();path=self.root/'vendor'/self.item['name'];path.write_bytes(b'broken')
        with patch.object(downloads,'ROOT',self.root),patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('network')):
            with self.assertRaises(RuntimeError):downloads.dependencies()
        self.assertEqual(path.read_bytes(),b'broken')
    def test_invalid_lock_filename_rejected_before_network(self):
        with patch.object(downloads.urllib.request,'urlopen',side_effect=AssertionError('network')):
            with self.assertRaises(ValueError):downloads.wheel_metadata(dict(self.item,name='../fake-1.0-py3-none-any.whl'))

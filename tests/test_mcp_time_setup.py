"""Instalator opcjonalnego SDK: kontrolowane wheel, prawdziwy NTFS i rollback."""
import hashlib,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from app import config
from app.network import ToolError
from scripts import setup_mcp_time as setup


@unittest.skipUnless(sys.platform=='win32' and sys.version_info[:2]==(3,13),'Native installer requires Windows CPython3.13')
class TimeSetupTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.context=patch.object(config,'ROOT',self.root);self.context.start();self.addCleanup(self.context.stop)
        self.wheels={};self.items=[]
        for filename,module in [('mcp_server_time-'+setup.VERSION+'-py3-none-any.whl','mcp_server_time'),('mcp-2.3.0-py3-none-any.whl','mcp')]:
            raw=io.BytesIO()
            with zipfile.ZipFile(raw,'w') as archive:archive.writestr(module+'/__init__.py','# controlled fixture, never executed')
            value=raw.getvalue();url='https://files.pythonhosted.org/packages/fixture/'+filename;self.wheels[url]=value
            self.items.append({'name':filename,'url':url,'size':len(value),'sha256':hashlib.sha256(value).hexdigest()})
        self.lock={'server_version':setup.VERSION,'sdk_version':'2.3.0','python':'3.13','wheels':self.items}
        self.lock_patch=patch.object(setup,'lock_bytes',side_effect=lambda:json.dumps(self.lock).encode());self.lock_patch.start();self.addCleanup(self.lock_patch.stop)
        owner=self
        class Opener:
            def open(opener,url,timeout):
                value=io.BytesIO(owner.wheels[url]);value.geturl=lambda:url;return value
        self.opener=patch.object(setup.urllib.request,'build_opener',return_value=Opener());self.mock=self.opener.start();self.addCleanup(self.opener.stop)
    def target(self):return self.root/'runtime'/setup.DIRECTORY

    def test_prepared_inventory_is_verified_and_second_prepare_does_not_download(self):
        target=setup.prepare();self.assertEqual(target,self.target());self.assertTrue(setup.verify(target));calls=self.mock.call_count
        self.assertEqual(setup.prepare(),target);self.assertEqual(self.mock.call_count,calls)
        self.assertEqual(list((self.root/'runtime').glob('mcp-time-stage-*')),[])

    def test_digest_mismatch_leaves_no_target_or_partial_stage(self):
        self.items[0]['sha256']='0'*64
        with self.assertRaises(ValueError):setup.prepare()
        self.assertFalse(self.target().exists());self.assertEqual(list((self.root/'runtime').iterdir()),[])

    def test_unknown_runtime_is_preserved_without_network(self):
        target=self.target();target.mkdir(parents=True);(target/'OWNER.txt').write_text('KEEP',encoding='utf-8')
        with self.assertRaises(ValueError) as error:setup.prepare()
        self.assertEqual(str(error.exception),'mcp_time_installation_conflict');self.assertEqual((target/'OWNER.txt').read_text(encoding='utf-8'),'KEEP');self.mock.assert_not_called()

    def test_repair_preserves_known_modified_runtime_as_previous(self):
        target=setup.prepare();file=target/'deps/mcp/__init__.py';file.write_text('OWNER_CHANGE',encoding='utf-8');self.assertFalse(setup.verify(target))
        setup.prepare();self.assertTrue(setup.verify(target));previous=list((self.root/'runtime').glob(setup.DIRECTORY+'-previous-*'));self.assertEqual(len(previous),1);self.assertEqual((previous[0]/'deps/mcp/__init__.py').read_text(encoding='utf-8'),'OWNER_CHANGE')

    def test_failed_promotion_restores_previous_runtime(self):
        target=setup.prepare();file=target/'deps/mcp/__init__.py';file.write_text('KEEP_ON_FAILURE',encoding='utf-8');rename=Path.rename
        def fail_stage(path,destination):
            if path.name.startswith('mcp-time-stage-'):raise OSError('controlled promotion failure')
            return rename(path,destination)
        with patch.object(Path,'rename',fail_stage),self.assertRaises(OSError):setup.prepare()
        self.assertEqual(file.read_text(encoding='utf-8'),'KEEP_ON_FAILURE');self.assertEqual(list((self.root/'runtime').glob('mcp-time-stage-*')),[])

    def test_cancel_and_unsafe_archive_do_not_promote_or_escape(self):
        calls=[0]
        def check():
            calls[0]+=1
            if calls[0]>=3:raise ToolError('login_required')
        with self.assertRaises(ToolError):setup.prepare(check)
        self.assertFalse(self.target().exists())
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as archive:archive.writestr('../escape.py','BAD')
        value=raw.getvalue();item=self.items[0];self.wheels[item['url']]=value;item.update(size=len(value),sha256=hashlib.sha256(value).hexdigest())
        with self.assertRaises(ValueError):setup.prepare()
        self.assertFalse((self.root/'escape.py').exists());self.assertFalse(self.target().exists())

    def test_bad_host_platform_and_corrupt_marker_fail_closed(self):
        self.items[0]['url']='https://outside.invalid/library.whl'
        with self.assertRaises(ValueError):setup.prepare()
        self.items[0]['url']=next(iter(self.wheels));target=setup.prepare();(target/setup.MARKER).write_text('['*1100,encoding='ascii');self.assertFalse(setup.verify(target))
        with patch.object(setup.sys,'platform','linux'),self.assertRaises(ValueError) as error:setup.prepare()
        self.assertEqual(str(error.exception),'mcp_time_python_unavailable')

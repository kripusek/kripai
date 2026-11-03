"""Prawdziwe pliki NTFS; kontrolowane pobrania, fixture wheel nie są uruchamiane."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from app import config
from scripts import setup_visual as setup


@unittest.skipUnless(sys.platform == 'win32' and sys.version_info[:2] == (3, 13),
                     'Native installer requires Windows CPython 3.13')
class VisualSetupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.context = patch.object(config, 'ROOT', self.root)
        self.context.start()
        self.addCleanup(self.context.stop)
        self.downloads = {}
        self.wheels = []
        for name, module in [('onnxruntime-1.31.1-cp313-cp313-win_amd64.whl', 'onnxruntime'),
                             ('tokenizers-0.23.3-cp310-abi3-win_amd64.whl', 'tokenizers'),
                             ('numpy-2.5.4-cp313-cp313-win_amd64.whl', 'numpy')]:
            value = self.archive({module+'/__init__.py': b'# controlled fixture, never executed'})
            self.wheels.append(self.item(name, 'https://files.pythonhosted.org/packages/fixture/'+name, value))
        self.assets = []
        for name in sorted(setup.ASSETS):
            path = ('onnx/' if name.endswith('.onnx') else '')+name
            self.assets.append(self.item(name, f'https://huggingface.co/{setup.REPOSITORY}/resolve/{setup.REVISION}/{path}',
                                         b'controlled synthetic model asset '+name.encode()))
        self.manifest = {'format': 1, 'python': '3.13', 'platform': 'win_amd64',
                         'provider': 'CPUExecutionProvider', 'repository': setup.REPOSITORY,
                         'revision': setup.REVISION, 'dimensions': 768, 'space': setup.SPACE,
                         'processor_version': 1, 'onnxruntime': '1.31.1', 'tokenizers': '0.23.3',
                         'numpy': '2.5.4', 'assets': self.assets, 'wheels': self.wheels}
        self.lock = patch.object(setup, 'lock_bytes', side_effect=lambda: json.dumps(self.manifest).encode())
        self.lock.start()
        self.addCleanup(self.lock.stop)
        owner = self

        class Opener:
            def open(opener, url, timeout):
                value = io.BytesIO(owner.downloads[url])
                value.geturl = lambda: url
                return value

        self.network = patch.object(setup.urllib.request, 'build_opener', return_value=Opener())
        self.mock = self.network.start()
        self.addCleanup(self.network.stop)

    @staticmethod
    def archive(files):
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return result.getvalue()

    def item(self, name, url, value):
        self.downloads[url] = value
        return {'name': name, 'url': url, 'size': len(value), 'sha256': hashlib.sha256(value).hexdigest()}

    def target(self):
        return self.root/'runtime'/setup.DIRECTORY

    def assert_no_stage(self):
        self.assertEqual(list((self.root/'runtime').glob('visual-stage-*')), [])

    def test_inventory_and_idempotent_prepare_with_separate_deps_assets(self):
        target = setup.prepare()
        self.assertEqual(target, self.target())
        self.assertTrue(setup.verify(target))
        self.assertEqual({path.name for path in (target/'assets').iterdir()}, setup.ASSETS)
        self.assertTrue((target/'deps/onnxruntime/__init__.py').is_file())
        calls = self.mock.call_count
        self.assertEqual(setup.prepare(), target)
        self.assertEqual(calls, self.mock.call_count)
        self.assert_no_stage()

    def test_bad_digest_or_short_long_download_cleans_stage(self):
        item = self.wheels[0]
        original = self.downloads[item['url']]
        for value in (original+b'EXTRA', original[:-1], b'X'*len(original)):
            self.downloads[item['url']] = value
            with self.assertRaises(ValueError):
                setup.prepare()
            self.assertFalse(self.target().exists())
            self.assert_no_stage()

    def test_unknown_target_and_corrupt_receipt_are_preserved_without_network(self):
        target = self.target()
        target.mkdir(parents=True)
        (target/'OWNER.txt').write_text('KEEP', encoding='utf-8')
        for receipt in (None, '['*1100, '{}'):
            if receipt is not None:
                (target/setup.MARKER).write_text(receipt, encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'visual_installation_conflict'):
                setup.prepare()
            self.assertEqual((target/'OWNER.txt').read_text(), 'KEEP')
            self.mock.assert_not_called()

    def test_known_modified_install_is_retained_as_previous(self):
        target = setup.prepare()
        file = target/'assets/tokenizer.json'
        file.write_text('OWNER_CHANGE', encoding='utf-8')
        self.assertFalse(setup.verify(target))
        setup.prepare()
        self.assertTrue(setup.verify(target))
        previous = list(target.parent.glob(setup.DIRECTORY+'-previous-*'))
        self.assertEqual(len(previous), 1)
        self.assertEqual((previous[0]/'assets/tokenizer.json').read_text(), 'OWNER_CHANGE')
        self.assert_no_stage()

    def test_promotion_error_rolls_back_to_previous_bytes(self):
        target = setup.prepare()
        file = target/'assets/config.json'
        file.write_text('RESTORE', encoding='utf-8')
        original = Path.rename

        def fail_stage(path, destination):
            if path.name.startswith('visual-stage-'):
                raise OSError('controlled promotion failure')
            return original(path, destination)

        with patch.object(Path, 'rename', fail_stage), self.assertRaises(OSError):
            setup.prepare()
        self.assertEqual(file.read_text(), 'RESTORE')
        self.assert_no_stage()

    def test_cancel_during_chunk_read_keeps_old_runtime_and_cleans_stage(self):
        target = setup.prepare()
        file = target/'assets/config.json'
        file.write_text('KEEP', encoding='utf-8')
        calls = [0]

        def check():
            calls[0] += 1
            if calls[0] >= 5:
                raise RuntimeError('controlled cancellation')

        with self.assertRaisesRegex(RuntimeError, 'controlled cancellation'):
            setup.prepare(check)
        self.assertEqual(file.read_text(), 'KEEP')
        self.assert_no_stage()

    def test_unsafe_zip_paths_symlinks_and_duplicate_case_are_denied(self):
        for filenames in ({'../escape.py': b'BAD'}, {'C:/escape.py': b'BAD'},
                          {'numpy/x.py': b'a', 'numpy/X.py': b'b'}, {'numpy/space. /x': b'BAD'}):
            value = self.archive(filenames)
            item = self.wheels[0]
            self.downloads[item['url']] = value
            item.update(size=len(value), sha256=hashlib.sha256(value).hexdigest())
            with self.assertRaises(ValueError):
                setup.prepare()
            self.assertFalse((self.root/'escape.py').exists())
            self.assertFalse(self.target().exists())
            self.assert_no_stage()
        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as archive:
            row = zipfile.ZipInfo('link')
            row.create_system = 3
            row.external_attr = 0o120777 << 16
            archive.writestr(row, '../outside')
        value = result.getvalue()
        self.downloads[item['url']] = value
        item.update(size=len(value), sha256=hashlib.sha256(value).hexdigest())
        with self.assertRaises(ValueError):
            setup.prepare()
        self.assert_no_stage()

    def test_manifest_rejects_foreign_url_gpu_provider_or_incompatible_model(self):
        values = [('provider', 'CUDAExecutionProvider'), ('dimensions', 384), ('space', 'old-space'),
                  ('revision', '0'*40), ('platform', 'linux')]
        for key, value in values:
            previous = self.manifest[key]
            self.manifest[key] = value
            with self.assertRaisesRegex(ValueError, 'visual_lock_invalid'):
                setup.prepare()
            self.manifest[key] = previous
        item = self.assets[0]
        previous = item['url']
        for value in ('https://evil.invalid/model', previous.replace(setup.REVISION, 'main'),
                      previous+'?token=never', previous.replace('https:', 'http:')):
            item['url'] = value
            with self.assertRaisesRegex(ValueError, 'visual_lock_invalid'):
                setup.prepare()
        self.mock.assert_not_called()

    def test_size_bounds_and_disk_check_precede_network(self):
        self.wheels[0]['size'] = setup.MAX_FILE+1
        with self.assertRaisesRegex(ValueError, 'visual_lock_invalid'):
            setup.prepare()
        self.wheels[0]['size'] = len(self.downloads[self.wheels[0]['url']])
        with patch.object(setup.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 0})()):
            with self.assertRaisesRegex(ValueError, 'visual_disk_space'):
                setup.prepare()
        self.mock.assert_not_called()

    def test_expired_deadline_and_replaced_model_receipt_fail_closed(self):
        with patch.object(setup, 'TIMEOUT', -1), self.assertRaisesRegex(ValueError, 'visual_prepare_timeout'):
            setup.prepare()
        self.assert_no_stage()
        target = setup.prepare()
        (target/'assets/config.json').write_bytes(b'CHANGED')
        receipt = json.loads((target/setup.MARKER).read_text())
        receipt['inventory'] = setup.inventory(target)
        (target/setup.MARKER).write_text(json.dumps(receipt), encoding='utf-8')
        self.assertFalse(setup.verify(target))

    def test_redirects_are_https_allowlisted_and_wheels_never_redirect(self):
        handler = setup.TrustedRedirect()
        req = setup.urllib.request.Request(self.assets[0]['url'])
        allowed = handler.redirect_request(req, None, 302, 'Found', {}, 'https://us.aws.cdn.hf.co/public?signature=fixture')
        self.assertEqual(allowed.host, 'us.aws.cdn.hf.co')
        for url in ('http://us.aws.cdn.hf.co/model', 'https://127.0.0.1/model',
                    'https://us.aws.cdn.hf.co.evil.invalid/model', 'https://owner:secret@huggingface.co/model'):
            with self.assertRaisesRegex(ValueError, 'visual_download_denied'):
                handler.redirect_request(req, None, 302, 'Found', {}, url)
        req = setup.urllib.request.Request(self.wheels[0]['url'])
        with self.assertRaisesRegex(ValueError, 'visual_download_denied'):
            handler.redirect_request(req, None, 302, 'Found', {}, self.wheels[0]['url'])

    def test_platform_marker_and_extra_files_change_availability(self):
        with patch.object(setup.sys, 'platform', 'linux'):
            self.assertFalse(setup.verify(self.target()))
            with self.assertRaisesRegex(ValueError, 'visual_python_unavailable'):
                setup.prepare()
        target = setup.prepare()
        self.assertEqual(setup.installed(), target)
        (target/'unexpected.txt').write_text('unexpected', encoding='utf-8')
        self.assertFalse(setup.verify(target))
        (target/setup.MARKER).write_text('['*1100, encoding='ascii')
        self.assertFalse(setup.verify(target))

    def test_waiting_for_another_prepare_still_checks_cancellation(self):
        calls = [0]

        def check():
            calls[0] += 1
            if calls[0] >= 2:
                raise RuntimeError('cancel waiting installer')

        setup._lock.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError, 'cancel waiting installer'):
                setup.prepare(check)
        finally:
            setup._lock.release()
        self.mock.assert_not_called()

    def test_expanded_zip_limit_and_final_foreign_redirect_are_denied(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('onnxruntime/huge.bin', b'X'*(100*1024))
        value = raw.getvalue()
        item = self.wheels[0]
        self.downloads[item['url']] = value
        item.update(size=len(value), sha256=hashlib.sha256(value).hexdigest())
        with patch.object(setup, 'MAX_TOTAL', 10*1024), self.assertRaisesRegex(ValueError, 'visual_archive_invalid'):
            setup.prepare()
        self.assert_no_stage()

        class ForeignOpener:
            def open(opener, url, timeout):
                response = io.BytesIO(b'')
                response.geturl = lambda: 'https://evil.invalid/model'
                return response

        with patch.object(setup.urllib.request, 'build_opener', return_value=ForeignOpener()):
            with self.assertRaisesRegex(ValueError, 'visual_download_denied'):
                setup.prepare()
        self.assertFalse(self.target().exists())
        self.assert_no_stage()

"""Opcjonalny koder wizualny CPU: prywatne wheels i modele, bez pip i kont."""
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit
from uuid import uuid4
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config

REVISION = 'ba1f3b0843f24bc5417d38e19c37b287d719b2f4'
REPOSITORY = 'onnx-community/siglip2-base-patch16-224-ONNX'
DIRECTORY = 'visual-siglip2-ba1f3b0843f2-py313'
MARKER = '.kripai-visual.json'
SPACE = 'siglip2-base-p16-224-int8-ba1f3b0843f2-v1-768'
MAX_TOTAL = 1024**3
MAX_FILE = 300*1024**2
TIMEOUT = 600
ASSETS = {'text_model_quantized.onnx', 'vision_model_quantized.onnx',
          'tokenizer.json', 'preprocessor_config.json', 'config.json',
          'tokenizer_config.json'}
_lock = threading.Lock()


def _linked(path):
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)


def _allowed_url(value):
    url = urlsplit(value)
    return (url.scheme == 'https' and url.hostname in {
        'huggingface.co', 'us.aws.cdn.hf.co', 'files.pythonhosted.org'}
        and url.port in (None, 443) and not url.username and not url.password
        and not url.fragment)


class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 4
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # CDN otrzymuje tylko publiczne żądanie pobrania; żadnych tokenów konta.
        if urlsplit(req.full_url).hostname == 'files.pythonhosted.org' or not _allowed_url(newurl):
            raise ValueError('visual_download_denied')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def lock_bytes():
    return (config.ROOT/'scripts/visual-lock.json').read_bytes()


def _manifest(raw):
    try:
        if len(raw) > 256*1024:
            raise ValueError
        data = json.loads(raw)
        if (data.get('format') != 1 or data.get('python') != '3.13'
                or data.get('platform') != 'win_amd64'
                or data.get('provider') != 'CPUExecutionProvider'
                or data.get('repository') != REPOSITORY or data.get('revision') != REVISION
                or data.get('dimensions') != 768 or data.get('space') != SPACE or data.get('processor_version') != 1
                or data.get('onnxruntime') != '1.31.1' or data.get('tokenizers') != '0.23.3'
                or data.get('numpy') != '2.5.4'):
            raise ValueError
        assets, wheels = data['assets'], data['wheels']
        if (not isinstance(assets, list) or not isinstance(wheels, list)
                or len(assets) != len(ASSETS) or not 1 <= len(wheels) <= 50
                or {item['name'] for item in assets} != ASSETS):
            raise ValueError
        names = set()
        for item in assets+wheels:
            name, value = item['name'], item['url']
            url = urlsplit(value)
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', name)
                    or name in names or type(item['size']) is not int or not 0 < item['size'] <= MAX_FILE
                    or not re.fullmatch(r'[a-f0-9]{64}', item['sha256'])
                    or not _allowed_url(value) or url.query):
                raise ValueError
            names.add(name)
            if item in assets:
                path = ('onnx/' if name.endswith('.onnx') else '')+name
                if value != f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{path}':
                    raise ValueError
            elif (not name.endswith('.whl') or url.netloc != 'files.pythonhosted.org'
                  or not url.path.startswith('/packages/') or url.path.rsplit('/', 1)[-1] != name):
                raise ValueError
        required = {'onnxruntime-1.31.1-cp313-cp313-win_amd64.whl',
                    'tokenizers-0.23.3-cp310-abi3-win_amd64.whl',
                    'numpy-2.5.4-cp313-cp313-win_amd64.whl'}
        if not required <= {item['name'] for item in wheels} or sum(item['size'] for item in assets+wheels) > MAX_TOTAL:
            raise ValueError
        return data
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
        raise ValueError('visual_lock_invalid') from None


def inventory(folder, check=lambda: None):
    result = {}
    total = 0

    def visit(path, depth=0):
        nonlocal total
        check()
        details = path.lstat()
        if _linked(path) or depth > 20:
            raise ValueError('visual_installation_invalid')
        if path.is_dir():
            for child in path.iterdir():
                if child != folder/MARKER:
                    visit(child, depth+1)
        elif stat.S_ISREG(details.st_mode):
            total += details.st_size
            if len(result) >= 10000 or total > MAX_TOTAL:
                raise ValueError('visual_installation_invalid')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    check()
                    digest.update(block)
            result[path.relative_to(folder).as_posix()] = digest.hexdigest()
        else:
            raise ValueError('visual_installation_invalid')

    visit(folder)
    return result


def _receipt(folder):
    marker = folder/MARKER
    if _linked(folder) or _linked(marker) or marker.stat().st_size > 2*1024**2:
        raise ValueError('visual_installation_invalid')
    data = json.loads(marker.read_text(encoding='utf-8'))
    if (data['format'] != 1 or data['owner'] != 'KripAI.visual'
            or data['revision'] != REVISION or not isinstance(data['inventory'], dict)
            or not re.fullmatch(r'[a-f0-9]{64}', data['lock_sha256'])):
        raise ValueError('visual_installation_invalid')
    return data


def verify(folder):
    try:
        if sys.platform != 'win32' or sys.version_info[:2] != (3, 13):
            return False
        if _linked(folder.parent):
            return False
        raw = lock_bytes()
        manifest = _manifest(raw)
        receipt = _receipt(folder)
        if receipt['lock_sha256'] != hashlib.sha256(raw).hexdigest():
            return False
        if not all((folder/'deps'/name/'__init__.py').is_file()
                   for name in ('onnxruntime', 'tokenizers', 'numpy')):
            return False
        files = inventory(folder)
        return (files == receipt['inventory'] and all(
            files.get('assets/'+item['name']) == item['sha256'] for item in manifest['assets']))
    except (OSError, ValueError, KeyError, TypeError, RecursionError, AttributeError):
        return False


def installed():
    for base in (config.ROOT, config.LOCAL/'KripAI'):
        folder = base/'runtime'/DIRECTORY
        if verify(folder):
            return folder
    return None


def _extract(file, destination, check, budget):
    with zipfile.ZipFile(file) as archive:
        rows = archive.infolist()
        if len(rows) > 6000:
            raise ValueError('visual_archive_invalid')
        names = set()
        for row in rows:
            path = Path(row.filename.replace('\\', '/'))
            parts = path.parts
            if (path.is_absolute() or not parts or '..' in parts or ':' in row.filename
                    or any(part.endswith(('.', ' ')) for part in parts)
                    or stat.S_ISLNK(row.external_attr >> 16)):
                raise ValueError('visual_archive_invalid')
            normalized = path.as_posix().casefold()
            if normalized in names:
                raise ValueError('visual_archive_invalid')
            names.add(normalized)
            budget[0] += row.file_size
            budget[1] += 1
            if row.file_size > MAX_FILE or budget[0] > MAX_TOTAL or budget[1] > 10000:
                raise ValueError('visual_archive_invalid')
        for row in rows:
            check()
            target = destination/Path(row.filename.replace('\\', '/'))
            if row.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(row) as source, target.open('xb') as output:
                while block := source.read(1024*1024):
                    check()
                    output.write(block)


@contextmanager
def _exclusive(check):
    deadline = time.monotonic()+TIMEOUT
    while True:
        check()
        if time.monotonic() > deadline:
            raise ValueError('visual_prepare_timeout')
        if _lock.acquire(timeout=0.2):
            break
    try:
        yield deadline
    finally:
        _lock.release()


def _download(opener, item, target, check):
    size = 0
    digest = hashlib.sha256()
    with opener.open(item['url'], timeout=20) as response, target.open('xb') as output:
        final = response.geturl()
        if (not _allowed_url(final) or (urlsplit(item['url']).hostname == 'files.pythonhosted.org'
                                      and final != item['url'])):
            raise ValueError('visual_download_denied')
        while True:
            check()
            block = response.read(1024*1024)
            if not block:
                break
            size += len(block)
            if size > item['size']:
                raise ValueError('visual_download_denied')
            digest.update(block)
            output.write(block)
    if size != item['size'] or digest.hexdigest() != item['sha256']:
        raise ValueError('visual_download_denied')


def prepare(check=lambda: None):
    with _exclusive(check) as deadline:
        check()
        if sys.platform != 'win32' or sys.version_info[:2] != (3, 13):
            raise ValueError('visual_python_unavailable')
        raw = lock_bytes()
        manifest = _manifest(raw)
        runtime = config.ROOT/'runtime'
        runtime.mkdir(exist_ok=True)
        if _linked(runtime):
            raise ValueError('visual_installation_conflict')
        runtime = runtime.resolve()
        target = runtime/DIRECTORY
        if verify(target):
            check()
            return target
        if target.exists() or target.is_symlink():
            try:
                _receipt(target)
            except (OSError, ValueError, KeyError, TypeError, RecursionError, AttributeError):
                raise ValueError('visual_installation_conflict') from None
        if shutil.disk_usage(runtime).free < 2*MAX_TOTAL:
            raise ValueError('visual_disk_space')
        stage = Path(tempfile.mkdtemp(prefix='visual-stage-', dir=runtime))
        def permitted():
            check()
            if time.monotonic() > deadline:
                raise ValueError('visual_prepare_timeout')

        try:
            deps, assets = stage/'deps', stage/'assets'
            deps.mkdir()
            assets.mkdir()
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), TrustedRedirect())
            budget = [sum(item['size'] for item in manifest['assets']), len(manifest['assets'])]
            for item in manifest['wheels']:
                permitted()
                file = stage/item['name']
                _download(opener, item, file, permitted)
                _extract(file, deps, permitted, budget)
                file.unlink()
            for item in manifest['assets']:
                permitted()
                _download(opener, item, assets/item['name'], permitted)
            receipt = {'format': 1, 'owner': 'KripAI.visual', 'revision': REVISION,
                       'lock_sha256': hashlib.sha256(raw).hexdigest(),
                       'inventory': inventory(stage, permitted)}
            (stage/MARKER).write_bytes(json.dumps(receipt, sort_keys=True).encode())
            if not verify(stage):
                raise ValueError('visual_installation_invalid')
            permitted()
            previous = None
            # Tylko własne katalogi we wskazanym runtime; poprzedni pozostaje jako kopia.
            if target.resolve().parent != runtime or stage.resolve().parent != runtime:
                raise ValueError('visual_installation_conflict')
            if target.exists():
                previous = runtime/(DIRECTORY+'-previous-'+str(uuid4()))
                if previous.resolve().parent != runtime:
                    raise ValueError('visual_installation_conflict')
                target.rename(previous)
            try:
                stage.rename(target)
            except OSError:
                if previous is not None and not target.exists():
                    previous.rename(target)
                raise
            return target
        finally:
            if stage.exists() and stage.resolve().parent == runtime and stage.name.startswith('visual-stage-'):
                shutil.rmtree(stage)


if __name__ == '__main__':
    try:
        prepare()
        print('Visual CPU encoder prepared.')
    except Exception:
        print('Visual CPU encoder preparation failed.', file=sys.stderr)
        sys.exit(1)

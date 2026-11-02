"""Lokalny głos: ograniczony WAV, jeden proces CPU, anulowanie i sprzątanie."""
from collections import OrderedDict
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import wave

from . import config
from .db import connect
from .processes import ModelJob

MAX_SECONDS = 30
MAX_AUDIO = 44 + 16000 * 2 * MAX_SECONDS
MAX_SPEECH = 1200
VOICE_RELEASE = 'b5454'
STT_MODEL = 'ggml-small.bin'


class VoiceError(Exception):
    def __init__(self, code, status=422):
        self.code, self.status = code, status
        super().__init__(code)


def validate_wav(data):
    # Tylko prosty PCM z naszego rejestratora. Brak ogólnego dekodera mediów,
    # dodatkowych chunków, kompresji, ścieżek ani deklarowanych ogromnych buforów.
    if not 44 + 8000 <= len(data) <= MAX_AUDIO:
        raise VoiceError('audio_length')
    try:
        fields = struct.unpack('<4sI4s4sIHHIIHH4sI', data[:44])
        riff, size, kind, fmt, fsize, codec, channels, rate, byte_rate, align, bits, tag, count = fields
        if (riff, kind, fmt, fsize, codec, channels, rate, byte_rate, align, bits, tag) != (
                b'RIFF', b'WAVE', b'fmt ', 16, 1, 1, 16000, 32000, 2, 16, b'data'):
            raise ValueError()
        if size != len(data)-8 or count != len(data)-44 or count % 2:
            raise ValueError()
    except (ValueError, struct.error):
        raise VoiceError('audio_format') from None
    return data


def powershell():
    if os.name != 'nt':
        raise VoiceError('tts_windows_required', 503)
    return str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')


def stt_command(folder, language):
    if language not in {'pl', 'en'}:
        raise VoiceError('voice_language')
    executable = config.ROOT/'runtime/whisper'/VOICE_RELEASE/'whisper-cli.exe'
    model = config.DATA/'models'/STT_MODEL
    if not executable.is_file() or not model.is_file():
        raise VoiceError('stt_not_installed', 503)
    return [str(executable), '--model', str(model), '--file', str(folder/'input.wav'),
            '--language', language, '--threads', '4', '--no-gpu', '--output-txt',
            '--output-file', str(folder/'result')]


def tts_command(folder, language, text):
    if language not in {'pl', 'en'}:
        raise VoiceError('voice_language')
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_SPEECH:
        raise VoiceError('speech_length')
    # Tekst jest danymi JSON w prywatnym pliku, nigdy poleceniem PowerShell/SSML.
    request = folder/'request.json'
    request.write_text(json.dumps({'language': language, 'text': text}, ensure_ascii=False), encoding='utf-8')
    return [powershell(), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(config.ROOT/'scripts/speak.ps1'), '-InputFile', str(request),
            '-OutputFile', str(folder/'speech.wav')]


class VoiceService:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = None
        self.recent = OrderedDict()
        self.stopping = threading.Event()

    def reset(self):
        self.stopping.clear()
        # Uruchamiane przed przyjmowaniem żądań, przy blokadzie jednej instancji.
        folder = config.DATA/'voice-tmp'
        if folder.exists():
            shutil.rmtree(folder)

    def shutdown(self):
        self.stopping.set()
        with self.lock:
            if self.active:
                self.active[1].set()

    def _prune(self):
        now = time.monotonic()
        while self.recent and next(iter(self.recent.values())) < now-600:
            self.recent.popitem(last=False)
        # Nie wyrzucamy świeżych anulowań, bo stare żądanie mogłoby się uruchomić.
        if len(self.recent) >= 256:
            raise VoiceError('voice_rate_limited', 429)

    def cancel(self, key):
        with self.lock:
            if self.active and self.active[0] == key:
                self.active[1].set()
            if key not in self.recent:
                self._prune()
                self.recent[key] = time.monotonic()

    @contextmanager
    def claim(self, key):
        with self.lock:
            self._prune()
            if self.stopping.is_set() or key in self.recent:
                raise VoiceError('voice_cancelled', 409)
            if self.active:
                raise VoiceError('voice_busy', 409)
            cancelled = threading.Event()
            self.active = (key, cancelled)
            self.recent[key] = time.monotonic()
        try:
            yield cancelled
        finally:
            with self.lock:
                self.active = None

    def permitted(self, key, cancelled):
        if cancelled.is_set() or self.stopping.is_set():
            raise VoiceError('voice_cancelled', 409)
        with connect() as conn:
            session = conn.execute('SELECT 1 FROM sessions WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>now()', key[:2]).fetchone()
            mode = conn.execute('SELECT requested_mode FROM system_mode').fetchone()
        if not session:
            raise VoiceError('login_required', 401)
        if mode['requested_mode'] != 'normal':
            raise VoiceError('gaming_mode', 409)

    def process(self, argv, folder, key, cancelled, timeout, memory_limit=None):
        self.permitted(key, cancelled)
        job = ModelJob(memory_limit=memory_limit)
        process = None
        try:
            process = subprocess.Popen(argv, cwd=folder, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            job.attach(process)
            if memory_limit:(folder/'job.ready').touch()
            deadline = time.monotonic()+timeout
            while process.poll() is None:
                self.permitted(key, cancelled)
                if time.monotonic() >= deadline:
                    raise VoiceError('voice_timeout', 504)
                cancelled.wait(.1)
            self.permitted(key, cancelled)
            if process.returncode == 3:
                raise VoiceError('tts_voice_missing', 503)
            if process.returncode:
                raise VoiceError('voice_engine_failed', 503)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            job.close()

    def execute(self, kind, key, language, value):
        with self.claim(key) as cancelled:
            self.permitted(key, cancelled)
            root = config.DATA/'voice-tmp'
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='job-', dir=root) as directory:
                folder = Path(directory)
                if kind == 'transcribe':
                    (folder/'input.wav').write_bytes(validate_wav(value))
                    argv = stt_command(folder, language)
                    self.process(argv, folder, key, cancelled, 90)
                    path = folder/'result.txt'
                    if not path.is_file() or path.stat().st_size > 32000:
                        raise VoiceError('voice_result_invalid', 503)
                    text = path.read_text(encoding='utf-8-sig').strip()
                    if not text:
                        raise VoiceError('speech_not_detected')
                    if len(text) > 4000:
                        raise VoiceError('transcript_too_long')
                    result = {'text': text, 'language': language}
                elif kind == 'speak':
                    argv = tts_command(folder, language, value)
                    self.process(argv, folder, key, cancelled, 45)
                    path = folder/'speech.wav'
                    if not path.is_file() or not 44 < path.stat().st_size <= 20*1024*1024:
                        raise VoiceError('voice_result_invalid', 503)
                    result = path.read_bytes()
                    try:
                        with wave.open(io.BytesIO(result), 'rb') as wav:
                            if wav.getcomptype() != 'NONE' or wav.getnframes() == 0:
                                raise ValueError()
                    except (ValueError, wave.Error, EOFError):
                        raise VoiceError('voice_result_invalid', 503) from None
                else:
                    raise VoiceError('voice_operation')
                self.permitted(key, cancelled)
                return result


service = VoiceService()

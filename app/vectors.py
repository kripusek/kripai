"""Wyłącznie przypięte rozszerzenie: żadnych ścieżek/SQL dostarczanych przez LLM."""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from . import config

EXTENSION_ROOT=Path(__file__).resolve().parents[1]
LOCK=json.loads((config.ROOT/'scripts/rag-lock.json').read_text(encoding='utf-8'))
SPACE=LOCK['space']
DIMENSIONS=LOCK['dimensions']

def load(conn):
    meta=LOCK['extensions'].get(sys.platform)
    if not meta:raise RuntimeError('sqlite_vec_platform')
    path=EXTENSION_ROOT/meta['path']
    if not path.is_file():raise RuntimeError('sqlite_vec_not_installed')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise RuntimeError('sqlite_vec_checksum')
    try:
        conn.enable_load_extension(True)
        conn.load_extension(str(path.resolve()))
    finally:conn.enable_load_extension(False)
    if conn.execute('SELECT vec_version()').fetchone()[0]!='v'+LOCK['sqlite_vec']:raise RuntimeError('sqlite_vec_version')

def encode(values):
    if not isinstance(values,list) or len(values)!=DIMENSIONS or any(type(x) not in (float,int) or not math.isfinite(x) for x in values):raise ValueError('embedding_invalid')
    norm=math.sqrt(sum(x*x for x in values))
    if not math.isfinite(norm) or norm<1e-12:raise ValueError('embedding_invalid')
    return struct.pack('<'+str(DIMENSIONS)+'f',*(x/norm for x in values))

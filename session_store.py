"""Versioned, atomic, local-only session persistence for DocMatch."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, tempfile

SCHEMA_VERSION = 1

def fingerprint(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dokumen sesi tidak ditemukan: {path}")
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'bytes': stat.st_size, 'sha256': digest.hexdigest()}

def validate_documents(session):
    for name in ('reference', 'examined'):
        saved = session['documents'][name]
        current = fingerprint(saved['path'])
        if current['sha256'] != saved['sha256']:
            raise ValueError(f"Dokumen {name} berubah sejak sesi disimpan. Pemulihan dibatalkan agar koordinat tidak salah.")

def save_session(path, payload):
    dest = Path(path).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = {'schema_version': SCHEMA_VERSION, 'saved_at': datetime.now(timezone.utc).isoformat(), **payload}
    text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dest.parent, prefix='.docmatch-', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, dest)
    finally:
        if temp is not None and temp.exists(): temp.unlink()
    return dest

def load_session(path, check_files=True):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Versi format sesi tidak didukung')
    if not all(key in payload for key in ('documents', 'comparison', 'stage2')):
        raise ValueError('Sesi tidak lengkap')
    if check_files: validate_documents(payload)
    return payload

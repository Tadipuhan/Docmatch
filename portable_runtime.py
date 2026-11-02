"""Find a bundled LibreOffice runtime before falling back to a system install."""
import os
import sys
import shutil
from pathlib import Path


def find_soffice():
    roots = [Path(sys.executable).resolve().parent, Path(__file__).resolve().parent]
    if getattr(sys, '_MEIPASS', None):
        roots.append(Path(sys._MEIPASS))
    candidates = []
    custom = os.environ.get('DOCMATCH_SOFFICE')
    if custom:
        candidates.append(Path(custom))
    for root in roots:
        candidates.extend([root / 'runtime' / 'libreoffice' / 'program' / 'soffice.exe',
                           root / 'runtime' / 'libreoffice' / 'program' / 'soffice.bin',
                           root / 'runtime' / 'libreoffice' / 'program' / 'soffice'])
    for base in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')):
        if base:
            candidates.append(Path(base) / 'LibreOffice' / 'program' / 'soffice.exe')
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which('soffice') or shutil.which('libreoffice')

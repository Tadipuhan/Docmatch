"""Offline dependency audit: run with `py preflight.py` on Windows."""
from pathlib import Path
import importlib.util, platform, sys
HERE = Path(__file__).resolve().parent
required = ['docmatch.py','legacy_v01.py','rules.py','editor.py','waybill_rules.py','hybrid_validation.py','session_store.py','template_manager.py']
print('DocMatch preflight / Python:',sys.version.split()[0],'/ OS:',platform.system())
failed=[]
for item in required:
    good=(HERE/item).is_file()
    print(('OK' if good else 'MISSING'), item)
    if not good:failed.append(item)
for module in ['PySide6','pymupdf','docx']:
    good=importlib.util.find_spec(module) is not None
    print(('OK' if good else 'MISSING'),module)
    if not good:failed.append(module)
print('OCR Tesseract portable:', 'OK' if (HERE/'tesseract'/'tesseract.exe').is_file() else 'OPTIONAL/NOT BUNDLED')
if failed:
    print('Tidak dapat dinyatakan siap startup. Lengkapi:', ', '.join(failed))
    sys.exit(1)
print('Dependency statis tersedia; tetap jalankan uji GUI & ekspor Windows.')

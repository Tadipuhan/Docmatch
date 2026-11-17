"""Offline, selection-only OCR candidates for the hybrid validation inspector.

No silent replacement of native text. OCR is explicitly requested by the user.
"""
from __future__ import annotations
import csv
import io
import os
import subprocess
from pathlib import Path
import pymupdf as fitz
from gsl_ocr import tesseract_path, OCRError


def text_quality(text):
    """Flags obvious corruption; this is not an OCR confidence score."""
    text = text or ''
    bad = text.count('\ufffd') + text.count('\x00')
    control = sum(1 for c in text if ord(c) < 32 and c not in '\n\t\r')
    return {'suspicious': bad > 0 or control > 0 or not text.strip(),
            'replacement_chars': text.count('\ufffd'), 'control_chars': control,
            'empty': not text.strip()}


def _ocr_one(exe, image, mode):
    env = os.environ.copy()
    tessdata = Path(exe).resolve().parent / 'tessdata'
    if tessdata.is_dir():
        env['TESSDATA_PREFIX'] = str(tessdata)
    try:
        proc = subprocess.run([exe, 'stdin', 'stdout', '-l', 'eng', '--psm', str(mode), 'tsv'],
                              input=image, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=45, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OCRError(f'OCR region gagal (PSM {mode}): {exc}') from exc
    if proc.returncode:
        raise OCRError(proc.stderr.decode('utf-8', errors='replace')[-500:])
    rows = []
    for row in csv.DictReader(io.StringIO(proc.stdout.decode('utf-8-sig', errors='replace')), delimiter='\t'):
        token = (row.get('text') or '').strip()
        if not token:
            continue
        try:
            conf = float(row.get('conf', -1))
            block, para, line = int(row['block_num']), int(row['par_num']), int(row['line_num'])
        except (ValueError, TypeError, KeyError):
            continue
        if conf >= 0:
            rows.append((block, para, line, token, conf))
    lines, scores = [], []
    for block, para, line, token, conf in rows:
        key = (block, para, line)
        if not lines or lines[-1][0] != key:
            lines.append((key, [token]))
        else:
            lines[-1][1].append(token)
        scores.append(conf)
    text = '\n'.join(' '.join(words) for _, words in lines)
    return {'text': text, 'confidence': round(sum(scores) / len(scores), 1) if scores else 0,
            'psm': mode, 'source': 'OCR region', 'words': len(scores)}


def read_region_candidates(page, rect, dpi=350, modes=(6, 7, 11), variants=('warna', 'grayscale')):
    """Rasterize the selected PDF rectangle at actual DPI; no synthetic interpolation."""
    clip = fitz.Rect(rect) & page.rect
    if clip.is_empty or clip.width < 2 or clip.height < 2:
        raise ValueError('Kotak seleksi terlalu kecil atau kosong.')
    # Prevent excessive memory usage for huge selections on 8 GB machines.
    if clip.width * clip.height * (dpi / 72) ** 2 > 16_000_000:
        dpi = min(dpi, int(72 * (16_000_000 / (clip.width * clip.height)) ** 0.5))
    if dpi < 100:
        raise ValueError('Area terlalu besar untuk OCR region aman. Pilih area lebih kecil.')
    exe = tesseract_path()
    candidates = []
    for variant, colorspace in [('warna', fitz.csRGB), ('grayscale', fitz.csGRAY)]:
        if variant not in variants:
            continue
        image = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72),
                                clip=clip, alpha=False, colorspace=colorspace).tobytes('png')
        for mode in modes:
            item = _ocr_one(exe, image, mode)
            if item['text'].strip():
                item['variant'] = variant
                item['dpi'] = dpi
                candidates.append(item)
    candidates.sort(key=lambda row: (row['confidence'], row['words']), reverse=True)
    unique = []
    for item in candidates:
        if not any(item['text'] == x['text'] for x in unique):
            unique.append(item)
    return unique[:6]

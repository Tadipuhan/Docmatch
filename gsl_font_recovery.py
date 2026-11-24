"""Pemulihan teks Type3 GSL secara OFFLINE, berbasis outline glyph (tanpa OCR).

v1.8.30 - perubahan dari v1.8.29:
  * Spasi ditentukan dari glyph KOSONG (.notdef / tanpa operator path), bukan dari
    nomor kode yang di-hardcode. Pada v1.8.29 kode 3 dipaksa menjadi spasi pada
    halaman 3, padahal pada GSL_SWB_26B92KR1C kode 3 adalah huruf "A".
  * Tabel hash glyph dipindah ke gsl_glyph_table.py (92 entri, termasuk "(", ")",
    ":", huruf kecil, dan font reguler yang dipakai Attached List).
  * Glyph yang tidak dikenal TIDAK ditebak: menjadi U+FFFD, dicatat di
    UNKNOWN_GLYPHS, dan field terkait gagal-aman (UnrecoverableGSLText).
  * Jika dua font Type3 pada satu halaman memberi karakter berbeda untuk kode yang
    sama, kode itu dianggap ambigu (U+FFFD), tidak ditimpa diam-diam.
  * Kotak kata memakai tinggi huruf nyata. FontBBox Type3 GSL ([0 0 1 -1]) membuat
    bbox bawaan ~2,6x terlalu tinggi dan titik tengahnya bergeser.

Fungsi murni (glyph_is_blank, build_charmap, merge_charmaps, parse_differences,
parse_charprocs, tight_char_rect) tidak memerlukan PyMuPDF dan diuji di tests/.
"""
from __future__ import annotations
import hashlib
import os
import re
try:
    import pymupdf as fitz
except ImportError:          # fungsi murni tetap dapat diuji tanpa PyMuPDF
    fitz = None

from gsl_glyph_table import GLYPHS

TRUSTED_GLYPHS = GLYPHS          # nama lama dipertahankan untuk kompatibilitas
REPLACEMENT = '\ufffd'
CAP_HEIGHT = 0.76                # tinggi huruf kapital relatif ukuran font
DESCENT = 0.22                   # turun di bawah baseline (g, p, y, koma)
UNKNOWN_GLYPHS = {}              # sha256 -> {'codes': set[int], 'count': int}
RUN_GAP_FACTOR = 0.9             # celah horizontal > 0,9 x ukuran font = rangkaian teks baru


class UnrecoverableGSLText(ValueError):
    pass


# ----------------------------------------------------------------------------
# Fungsi murni
# ----------------------------------------------------------------------------
_PATH_OPS = {'m', 'l', 'c', 'v', 'y', 're'}
_RASTER_OPS = {'BI', 'ID', 'Do', 'sh'}


def glyph_hash(stream: bytes) -> str:
    return hashlib.sha256(stream).hexdigest()


def glyph_is_blank(stream: bytes) -> bool:
    """True bila glyph tidak menggambar apa pun (spasi / .notdef).

    Glyph yang berisi gambar mentah (BI/Do/sh) BUKAN blank: ia tak dikenal.
    """
    tokens = stream.split()
    ops = {t.decode('latin-1') for t in tokens}
    if ops & _RASTER_OPS:
        return False
    return not (ops & _PATH_OPS)


def build_charmap(code_streams, table=None, report=None):
    """{kode: stream glyph} -> {kode: karakter}.

    report (dict) diisi {hash: {'codes': set, 'count': n}} untuk glyph tak dikenal.
    """
    table = GLYPHS if table is None else table
    charmap = {}
    for code, stream in code_streams.items():
        if glyph_is_blank(stream):
            charmap[code] = ' '
            continue
        digest = glyph_hash(stream)
        char = table.get(digest)
        if char is None:
            charmap[code] = REPLACEMENT
            if report is not None:
                entry = report.setdefault(digest, {'codes': set(), 'count': 0})
                entry['codes'].add(code)
                entry['count'] += 1
        else:
            charmap[code] = char
    return charmap


def merge_charmaps(maps):
    """Gabungkan peta beberapa font; kode yang bertentangan menjadi ambigu."""
    merged = {}
    for charmap in maps:
        for code, char in charmap.items():
            if code in merged and merged[code] != char:
                merged[code] = REPLACEMENT
            else:
                merged.setdefault(code, char)
    return merged


_NAME_OR_INT = re.compile(r'/[^\s/<>\[\]()]+|\d+')


def parse_differences(text):
    """'[0 /0 /1 /.notdef 12 /g12]' -> {0:'0', 1:'1', 2:'.notdef', 12:'g12'}."""
    mapping, code = {}, None
    inner = text[text.find('[') + 1: text.rfind(']')] if '[' in text else text
    for token in _NAME_OR_INT.findall(inner):
        if token.startswith('/'):
            if code is not None:
                mapping[code] = token[1:]
                code += 1
        else:
            code = int(token)
    return mapping


_CHARPROC_ENTRY = re.compile(r'/([^\s/<>\[\]()]+)\s+(\d+)\s+0\s+R')


def parse_charprocs(text):
    """'<</47 12 0 R/.notdef 9 0 R>>' -> {'47': 12, '.notdef': 9}."""
    return {name: int(xref) for name, xref in _CHARPROC_ENTRY.findall(text)}


def tight_char_rect(bbox, origin, size, force=False):
    """Kotak karakter yang menempel pada tinggi huruf nyata.

    Font Type3 GSL memakai FontBBox [0 0 1 -1], sehingga PyMuPDF menghasilkan kotak yang
    membentang dari baseline KE BAWAH sejauh satu em (tinggi = 1,0 x ukuran), bukan di
    atas huruf. Karena tingginya "tampak normal", kotak itu tidak bisa dikenali dari
    ukurannya; untuk teks Type3 pakai force=True agar y selalu dihitung dari baseline.
    Tanpa force, kotak yang wajar (<= 1,35 x ukuran) dikembalikan apa adanya.
    x0/x1 tetap dari bbox bawaan (lebar maju karakter).
    """
    x0, y0, x1, y1 = bbox
    if not size or size <= 0 or origin is None:
        return (x0, y0, x1, y1)
    if not force and (y1 - y0) <= 1.35 * size:
        return (x0, y0, x1, y1)
    baseline = origin[1]
    return (x0, baseline - CAP_HEIGHT * size, x1, baseline + DESCENT * size)


def char_geometry_sample(doc, page_number, limit=40):
    """Diagnostik: bbox/origin/size mentah dari PyMuPDF dan kotak hasil koreksi.

    Dipakai dump_geometry.py bila kotak penanda masih meleset.
    """
    out = []
    for block in doc[page_number].get_text('rawdict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                for ch in span['chars']:
                    if len(out) >= limit:
                        return out
                    box = tight_char_rect(ch['bbox'], ch.get('origin'), span.get('size', 0), force=True)
                    out.append({'code': ord(ch['c']), 'font': span.get('font'), 'size': span.get('size'),
                                'origin': list(ch.get('origin') or []), 'bbox_pymupdf': [round(v, 2) for v in ch['bbox']],
                                'bbox_corrected': [round(v, 2) for v in box]})
    return out


def starts_new_run(prev_x1, next_x0, size, factor=RUN_GAP_FACTOR):
    """True bila celah horizontal antar-karakter cukup besar untuk dua rangkaian teks."""
    return bool(size) and (next_x0 - prev_x1) > factor * size


def assign_run_anchors(words, size, factor=RUN_GAP_FACTOR):
    """Beri tiap kata 'anchor' = titik tengah KATA PERTAMA dari rangkaian teksnya.

    Rangkaian teks (run) = kata-kata berurutan pada satu baris tanpa celah besar.
    Sebuah sel memiliki seluruh run bila anchor-nya berada di dalam sel. Pada PDF GSL,
    nilai panjang (mis. "CAT LAI TERMINAL - HO CHI MINH CITY") melewati garis kotak
    sedangkan tampilan visualnya dipotong gambar latar; kepemilikan per-titik-tengah-kata
    memecahnya ke kotak tetangga.
    words: daftar dict dengan 'rect' (iterable x0,y0,x1,y1), urutan baca satu baris.
    """
    anchor, prev_x1 = None, None
    for word in words:
        x0, y0, x1, y1 = tuple(word['rect'])
        if anchor is None or starts_new_run(prev_x1, x0, size, factor):
            anchor = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        word['anchor'] = anchor
        prev_x1 = x1
    return words


# ----------------------------------------------------------------------------
# Integrasi PyMuPDF (belum diuji di lingkungan audit: PyMuPDF tidak tersedia)
# ----------------------------------------------------------------------------
def read_type3_font(doc, font_xref):
    """Kembalikan {kode: stream outline} untuk satu font Type3."""
    code_to_name, procs = {}, {}
    try:
        kind, value = doc.xref_get_key(font_xref, 'Encoding')
        if kind == 'xref':
            enc = int(value.split()[0])
            _, diff = doc.xref_get_key(enc, 'Differences')
            code_to_name = parse_differences(diff)
        elif kind == 'dict':
            code_to_name = parse_differences(value)
    except (RuntimeError, ValueError, IndexError):
        code_to_name = {}
    try:
        kind, value = doc.xref_get_key(font_xref, 'CharProcs')
        if kind == 'xref':
            procs = parse_charprocs(doc.xref_object(int(value.split()[0])))
        elif kind == 'dict':
            procs = parse_charprocs(value)
    except (RuntimeError, ValueError, IndexError):
        procs = {}
    if not procs:                       # cadangan: perilaku v1.8.29 (nama == kode)
        procs = parse_charprocs(doc.xref_object(font_xref))
    if not code_to_name:
        code_to_name = {int(n): n for n in procs if n.isdigit()}
    streams = {}
    for code, name in code_to_name.items():
        if name in procs:
            try:
                streams[code] = doc.xref_stream(procs[name]) or b''
            except (RuntimeError, ValueError):
                continue
    return streams


_PAGE_CACHE = {}


def _cache_key(doc, page_number):
    name = getattr(doc, 'name', '') or ''
    if not name or not os.path.isfile(name):
        return None
    stat = os.stat(name)
    return (name, stat.st_mtime_ns, stat.st_size, page_number)


def page_charmap(doc, page_number):
    page = doc[page_number]
    maps = []
    for font in page.get_fonts():
        if font[2] != 'Type3':
            continue
        maps.append(build_charmap(read_type3_font(doc, font[0]), report=UNKNOWN_GLYPHS))
    return merge_charmaps(maps)


def recover_page_words(doc, page_number):
    key = _cache_key(doc, page_number)
    if key is not None and key in _PAGE_CACHE:
        return [dict(w) for w in _PAGE_CACHE[key]]
    page = doc[page_number]
    if not any(f[2] == 'Type3' for f in page.get_fonts()):
        return []
    charmap = page_charmap(doc, page_number)
    if not any(ch not in (' ', REPLACEMENT) for ch in charmap.values()):
        raise UnrecoverableGSLText(
            'Tidak ada pemetaan glyph Type3 yang tervalidasi pada halaman ' + str(page_number + 1))
    output = []
    for block in page.get_text('rawdict')['blocks']:
        if 'lines' not in block:
            continue
        for line in block['lines']:
            pending = []
            line_start = len(output)
            line_size = 0

            def flush():
                if not pending:
                    return
                rect = fitz.Rect(pending[0][1])
                for _, box in pending[1:]:
                    rect |= fitz.Rect(box)
                output.append({'word': ''.join(t for t, _ in pending), 'rect': rect,
                               'page': page_number})
                pending.clear()

            for span in line['spans']:
                size = span.get('size', 0)
                line_size = max(line_size, size)
                for ch in span['chars']:
                    code = ord(ch['c'])
                    decoded = charmap.get(code, REPLACEMENT if code < 256 else ch['c'])
                    if decoded.isspace():
                        flush()
                    else:
                        box = tight_char_rect(ch['bbox'], ch.get('origin'), size, force=True)
                        if pending and starts_new_run(pending[-1][1][2], box[0], size):
                            flush()          # dua rangkaian teks tanpa spasi di antaranya
                        pending.append((decoded, box))
            flush()
            assign_run_anchors(output[line_start:], line_size)
    if key is not None:
        if len(_PAGE_CACHE) >= 32:
            _PAGE_CACHE.clear()
        _PAGE_CACHE[key] = [dict(w) for w in output]
    return output


def word_anchor(word):
    """Titik penentu kepemilikan sel: anchor rangkaian teks (bila ada), jika tidak titik tengah kata."""
    anchor = word.get('anchor')
    if anchor is not None:
        return fitz.Point(anchor[0], anchor[1])
    r = fitz.Rect(word['rect'])
    return (r.tl + r.br) * 0.5


def unknown_glyph_report():
    """Daftar glyph tak dikenal sejak aplikasi dibuka (untuk diberi label)."""
    return {h: {'codes': sorted(v['codes']), 'count': v['count']}
            for h, v in UNKNOWN_GLYPHS.items()}


def recover_gsl_field(doc, name, regions, rect_function):
    words = []
    for page_number, *bounds in regions:
        if page_number >= len(doc):
            raise UnrecoverableGSLText('Field ' + name + ': halaman PDF ' + str(page_number + 1) + ' tidak tersedia')
        clip = rect_function(doc[page_number], bounds)
        for w in recover_page_words(doc, page_number):
            if clip.contains(word_anchor(w)):
                words.append(w)
    if not words:
        raise UnrecoverableGSLText('Field ' + name + ': tidak ada teks terverifikasi pada area halaman '
                                   + ', '.join(str(r[0] + 1) for r in regions))
    if any(REPLACEMENT in w['word'] for w in words):
        raise UnrecoverableGSLText('Field ' + name + ': terdapat glyph yang belum dapat dipulihkan secara pasti. '
                                   'Tidak dilakukan perbandingan otomatis.')
    return {'text': ' '.join(w['word'] for w in words), 'words': words}

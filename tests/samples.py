"""Lokasi PDF sampel + pembaca glyph Type3 independen (pypdf) untuk tes.

Letakkan PDF sampel di ../samples/ atau set DOCMATCH_SAMPLES. Tes dilewati bila
sampel/pypdf tidak ada, bukan gagal.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [os.environ.get('DOCMATCH_SAMPLES', ''), str(ROOT / 'samples')]

NAMES = {
    'gsl_a': 'GSL_SWB_26B92KR1C__FINAL_.pdf',
    'gsl_b': 'GSL_SWB_26BX2VN1B__FINAL_.pdf',
    'anl': 'ANL_SWB_26B63EM4__DRAFT_.pdf',
    'cnc': 'CNC_SWB_26B92HK1__FINAL_.pdf',
    'anl3': 'ANL_DRAFT_SWB_26BX3AL1A.pdf',
}


def sample(key):
    for base in CANDIDATES:
        if base and (Path(base) / NAMES[key]).is_file():
            return str(Path(base) / NAMES[key])
    return None


def pypdf_page_text(path, page_index):
    """Dekode teks Type3 satu halaman memakai pypdf + modul glyph produksi.

    Mengembalikan daftar baris (urutan stream). Hanya untuk tes.
    """
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    import gsl_font_recovery as gfr

    reader = PdfReader(path)
    page = reader.pages[page_index]
    fonts = [f.get_object() for f in page['/Resources']['/Font'].values()
             if f.get_object().get('/Subtype') == '/Type3']
    maps = []
    for font in fonts:
        diffs = gfr.parse_differences(' '.join(
            str(x) for x in font['/Encoding'].get_object()['/Differences']))
        procs = font['/CharProcs']
        streams = {}
        for code, name in diffs.items():
            key = '/' + name
            if key in procs:
                streams[code] = procs[key].get_object().get_data()
        maps.append(gfr.build_charmap(streams))
    charmap = gfr.merge_charmaps(maps)
    lines, buf = [], ''
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        if op in (b'Tm', b'Td', b'T*'):
            if buf:
                lines.append(buf)
                buf = ''
        elif op == b'TJ':
            for item in operands[0]:
                if hasattr(item, 'original_bytes'):
                    buf += ''.join(charmap.get(b, gfr.REPLACEMENT) for b in item.original_bytes)
        elif op == b'Tj':
            buf += ''.join(charmap.get(b, gfr.REPLACEMENT) for b in operands[0].original_bytes)
    if buf:
        lines.append(buf)
    return [' '.join(line.split()) for line in lines]


def render_gray(path, page_index=0, dpi=100):
    """(bytes, width, height) grayscale. PyMuPDF bila ada, jika tidak pdftoppm+PIL."""
    try:
        import pymupdf as fitz
        with fitz.open(path) as doc:
            zoom = dpi / 72
            pix = doc[page_index].get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                             colorspace=fitz.csGRAY, alpha=False)
            data = bytes(pix.samples)
            if pix.stride != pix.width:
                data = b''.join(data[r * pix.stride: r * pix.stride + pix.width]
                                for r in range(pix.height))
            return data, pix.width, pix.height
    except ImportError:
        pass
    import shutil, subprocess, tempfile
    if not shutil.which('pdftoppm'):
        return None
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['pdftoppm', '-r', str(dpi), '-f', str(page_index + 1), '-l',
                        str(page_index + 1), '-gray', path, tmp + '/p'],
                       capture_output=True, check=False)
        files = sorted(Path(tmp).glob('p*.pgm'))
        if not files:
            return None
        img = Image.open(files[0])
        return img.tobytes(), img.width, img.height


def pypdf_lines_xy(path, page_index):
    """[(x_norm, y_norm_dari_atas, teks)] awal tiap baris teks (posisi Tm)."""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    import gsl_font_recovery as gfr
    reader = PdfReader(path)
    page = reader.pages[page_index]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    # reuse decoding by monkey-free approach: decode text per line using same charmap
    fonts = [f.get_object() for f in page['/Resources']['/Font'].values()
             if f.get_object().get('/Subtype') == '/Type3']
    maps = []
    for font in fonts:
        diffs = gfr.parse_differences(' '.join(str(x) for x in font['/Encoding'].get_object()['/Differences']))
        procs = font['/CharProcs']
        maps.append(gfr.build_charmap({c: procs['/' + n].get_object().get_data()
                                       for c, n in diffs.items() if '/' + n in procs}))
    charmap = gfr.merge_charmaps(maps)
    out, buf, pos = [], '', None
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        if op == b'Tm':
            if buf.strip():
                out.append((pos[0], pos[1], ' '.join(buf.split())))
            buf = ''
            pos = (float(operands[4]) / width, 1 - float(operands[5]) / height)
        elif op == b'TJ':
            for item in operands[0]:
                if hasattr(item, 'original_bytes'):
                    buf += ''.join(charmap.get(b, gfr.REPLACEMENT) for b in item.original_bytes)
    if buf.strip():
        out.append((pos[0], pos[1], ' '.join(buf.split())))
    return out


def page_words(path, page_index=0):
    """(lebar, tinggi, [(x0,y0,x1,y1,teks)]) untuk PDF bertext-layer normal (ANL/CNC).

    PyMuPDF bila ada; jika tidak, pdftotext -bbox (hanya untuk lingkungan audit).
    """
    try:
        import pymupdf as fitz
        with fitz.open(path) as doc:
            page = doc[page_index]
            return page.rect.width, page.rect.height, [
                (w[0], w[1], w[2], w[3], w[4]) for w in page.get_text('words')]
    except ImportError:
        pass
    import html, re, shutil, subprocess
    if not shutil.which('pdftotext'):
        return None
    out = subprocess.run(['pdftotext', '-f', str(page_index + 1), '-l', str(page_index + 1),
                          '-bbox', path, '-'], capture_output=True, text=True).stdout
    width, height = map(float, re.search(r'<page width="([\d.]+)" height="([\d.]+)"', out).groups())
    words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in re.findall(
        r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', out)]
    return width, height, words

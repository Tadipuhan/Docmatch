"""Ekstraksi nilai field formulir Sea Waybill ANL / CNC / CMA CGM (satu keluarga layout).

Dibuat dari audit v1.8.33.1 pada tiga formulir nyata (ANL 26BX3AL1A, ANL 26B63EM4,
CNC 26B92HK1) yang tata letaknya identik. Masalah yang diperbaiki:

  * Caption cetak ikut masuk ke nilai ("PORT OF LOADING JAKARTA, INDONESIA",
    "VOYAGE NUMBER 0SQ5AN", "KGS KGS CBM 8455.454 ..."), sehingga nilai yang sama
    dilaporkan BERBEDA dan kotak penanda menutupi caption.
  * Place & Date of Issue: caption berada di BARIS YANG SAMA dengan nilainya, dan baris
    klausa di dekatnya ("and") ikut terbaca.
  * Kolom Container, No & Kind, Cargo dan Weight ikut membaca baris "Shipped on Board ...",
    "... As agents for the Carrier" dan baris footer "Weight in Kgs Total: N CONTAINER(S)".
  * Tinggi badan tabel berubah menurut jumlah kontainer (footer di y .649 pada 1 kontainer,
    .658 pada 2-3 kontainer); batas bawah kini mengikuti baris footer, bukan angka tetap.
  * Additional Clauses menyertakan syarat cetak di bawah kotak (y > .823) dan membaca dua
    kolom secara berselang-seling per baris.

Metode: kotak nilai terukur (di antara caption dan nilai, bukan di caption) + pembuangan
baris caption berdasarkan teksnya + jangkar baris footer. Tidak ada OCR, tidak ada tebakan.
Hanya teks dari PDF; field yang kosong tetap kosong.
"""
from __future__ import annotations
import re
import pymupdf as fitz

# (nama, (x0, y0, x1, y1)) dinormalisasi terhadap halaman. Urutan = urutan di UI.
# y0 ditaruh DI ANTARA pusat caption dan pusat nilai agar caption tidak ikut.
ANL_FIELDS = [
    ('Shipper', (.005, .028, .470, .104)),
    ('Consignee', (.005, .112, .470, .187)),
    ('Notify Party', (.005, .200, .470, .279)),
    ('Voyage Number', (.800, .027, .995, .047)),
    ('Waybill Number', (.800, .064, .995, .090)),
    ('Pre-Carriage', (.005, .291, .224, .304)),
    ('Place of Receipt', (.224, .291, .474, .304)),
    ('Freight To Be Paid At', (.474, .291, .728, .304)),
    ('Number of Original Waybills', (.728, .291, .995, .304)),
    ('Vessel', (.005, .316, .224, .337)),
    ('Port of Loading', (.224, .316, .474, .337)),
    ('Port of Discharge', (.474, .316, .728, .337)),
    ('Final Place of Delivery', (.728, .316, .995, .337)),
    ('Container & Seal', (.005, .381, .158, .645)),
    ('No & Kind of Packages', (.158, .381, .272, .645)),
    ('Cargo Description', (.272, .381, .703, .645)),
    ('Weight & Measurement', (.703, .381, .995, .662)),
    ('Place & Date of Issue', (.190, .941, .520, .958)),
    ('Additional Clauses', (.005, .695, .995, .823)),
]
BODY_FIELDS = {'Container & Seal', 'No & Kind of Packages', 'Cargo Description', 'Weight & Measurement'}
BODY_BOTTOM_FALLBACK = .645
CLAUSE_BOTTOM_FIRST_PAGE = .823     # di bawahnya: syarat cetak "RECEIVED by the Carrier ..."
CLAUSE_BOTTOM_OTHER_PAGES = .940
CLAUSE_COLUMN_SPLIT = .484
LINE_TOLERANCE = .0042              # selisih pusat-y (fraksi tinggi halaman) satu baris
RUN_GAP = .020                      # celah-x (fraksi lebar) yang memisahkan dua rangkaian teks

# Caption cetak (dinormalisasi: huruf kecil, tanpa tanda baca) yang tidak pernah menjadi nilai.
_CAPTIONS = {
    'shipper', 'consignee', 'notify party carrier not to be responsible for failure to notify',
    'voyage number', 'waybill number', 'pre carriage by', 'place of receipt',
    'freight to be paid at', 'number of original waybills', 'vessel', 'port of loading',
    'port of discharge', 'final place of delivery', 'marks and nos container and seals',
    'no and kind of packages', 'gross weight cargo', 'tare', 'measurement', 'kgs', 'cbm',
    'kgs kgs cbm', 'place and date of issue', 'export references', 'additional clauses',
    'signed for the shipper',
}
_SHIPPED = re.compile(r'^shipped\s+on\s+board\b', re.I)
_AGENTS = re.compile(r'\bas\s+agents\s+for\s+the\s+carrier\b', re.I)
_FOOTER = re.compile(r'^weight\s+in\s+kgs\b', re.I)
_NUMBER = re.compile(r'^[\d][\d.,]*$')


def _norm_caption(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', text.casefold())).strip()


def is_caption_text(text):
    return _norm_caption(text) in _CAPTIONS


def _rect(page, bounds):
    r = page.rect
    return fitz.Rect(r.x0 + bounds[0] * r.width, r.y0 + bounds[1] * r.height,
                     r.x0 + bounds[2] * r.width, r.y0 + bounds[3] * r.height)


def page_words(page):
    """Kata halaman -> dict {word, rect, cx, cy}. Satu kali per halaman."""
    out = []
    for w in page.get_text('words', sort=True):
        token = str(w[4]).strip()
        if not token:
            continue
        r = fitz.Rect(w[:4])
        out.append({'word': token, 'rect': r, 'cx': (r.x0 + r.x1) / 2.0, 'cy': (r.y0 + r.y1) / 2.0})
    return out


def group_lines(words, page_height):
    """Kelompokkan kata ke baris berdasarkan pusat-y. Mengembalikan list baris (kata terurut-x)."""
    tol = LINE_TOLERANCE * page_height
    lines = []
    for w in sorted(words, key=lambda v: (v['cy'], v['cx'])):
        if lines and abs(w['cy'] - lines[-1]['cy']) <= tol:
            lines[-1]['words'].append(w)
            lines[-1]['cy'] = sum(v['cy'] for v in lines[-1]['words']) / len(lines[-1]['words'])
        else:
            lines.append({'cy': w['cy'], 'words': [w]})
    for line in lines:
        line['words'].sort(key=lambda v: v['cx'])
    return lines


def reading_order(words, page_height):
    """Urutan baca deterministik: baris atas->bawah, di dalam baris kiri->kanan."""
    return [w for line in group_lines(words, page_height) for w in line['words']]


def split_runs(line_words, page_width):
    """Pecah satu baris menjadi rangkaian teks terpisah bila ada celah-x besar."""
    runs, gap = [], RUN_GAP * page_width
    for w in line_words:
        if runs and w['rect'].x0 - runs[-1][-1]['rect'].x1 <= gap:
            runs[-1].append(w)
        else:
            runs.append([w])
    return runs


def _run_text(run):
    return ' '.join(w['word'] for w in run)


def find_footer(lines, page):
    """Baris footer 'Weight in Kgs Total: N CONTAINER(S)' -> pusat-y, atau None."""
    for line in lines:
        if line['cy'] < page.rect.y0 + .45 * page.rect.height:
            continue
        for run in split_runs(line['words'], page.rect.width):
            if run[0]['cx'] < page.rect.x0 + .25 * page.rect.width and _FOOTER.match(_run_text(run)):
                return line['cy']
    return None


def junk_word_ids(lines, page):
    """id() kata pada baris 'Shipped on Board', 'As agents for the Carrier' dan footer."""
    junk = set()
    width = page.rect.width
    for idx, line in enumerate(lines):
        for run in split_runs(line['words'], width):
            text = _run_text(run)
            if _SHIPPED.match(text) or _AGENTS.search(text) or _FOOTER.match(text):
                junk.update(id(w) for w in run)
    return junk


def _tag_caption_words(words, page):
    """id() kata yang berada pada rangkaian teks yang seluruhnya adalah caption."""
    lines = group_lines(words, page.rect.height)
    marked = set()
    for line in lines:
        for run in split_runs(line['words'], page.rect.width):
            if is_caption_text(_run_text(run)):
                marked.update(id(w) for w in run)
    return marked


def _public(w, page_no, **extra):
    d = {'word': w['word'], 'rect': w['rect'], 'page': page_no}
    d.update(extra)
    return d


def extract_anl_form(doc, chosen=None):
    """{field: {'text', 'words', ['semantic_text', 'semantic_words']}} untuk halaman pertama (+klausa)."""
    chosen = {n for n, _ in ANL_FIELDS} if chosen is None else set(chosen)
    if len(doc) == 0:
        raise ValueError('PDF kosong')
    page = doc[0]
    words = page_words(page)
    lines = group_lines(words, page.rect.height)
    junk = junk_word_ids(lines, page)
    footer_cy = find_footer(lines, page)
    bottom = (footer_cy - .005 * page.rect.height) if footer_cy is not None else \
        page.rect.y0 + BODY_BOTTOM_FALLBACK * page.rect.height
    result = {}
    for name, bounds in ANL_FIELDS:
        if name not in chosen:
            continue
        if name == 'Additional Clauses':
            result[name] = _extract_clauses(doc)
            continue
        region = _rect(page, bounds)
        if name in BODY_FIELDS:
            region.y1 = min(region.y1, bottom)
        inside = [w for w in words if region.contains((w['rect'].tl + w['rect'].br) * .5)]
        caption_ids = _tag_caption_words(inside, page)
        kept = reading_order([w for w in inside if id(w) not in junk and id(w) not in caption_ids],
                             page.rect.height)
        entry = {'text': ' '.join(w['word'] for w in kept),
                 'words': [_public(w, 0) for w in kept]}
        if name == 'Weight & Measurement':
            total_words = _totals_words(words, footer_cy, page, bounds)
            entry['words'] = entry['words'] + [_public(w, 0, role='total') for w in total_words]
            entry['text'] = ' '.join(w['word'] for w in kept + total_words)
            if total_words:
                entry['semantic_words'] = [_public(w, 0, role='total') for w in total_words]
                entry['semantic_text'] = ' '.join(w['word'] for w in total_words)
        result[name] = entry
    return result


def _totals_words(words, footer_cy, page, bounds):
    """Angka total (gross, tare, measurement) pada baris footer, di kolom berat."""
    if footer_cy is None:
        return []
    tol = LINE_TOLERANCE * page.rect.height
    x0 = page.rect.x0 + bounds[0] * page.rect.width
    found = [w for w in words if abs(w['cy'] - footer_cy) <= tol and w['rect'].x0 >= x0 - 2
             and _NUMBER.match(w['word'])]
    return sorted(found, key=lambda w: w['cx'])


def _extract_clauses(doc):
    """Additional Clauses: kolom kiri lalu kolom kanan, per halaman; tanpa syarat cetak."""
    collected = []
    for page_no, page in enumerate(doc):
        top = .695 * page.rect.height + page.rect.y0
        bottom_frac = CLAUSE_BOTTOM_FIRST_PAGE if page_no == 0 else CLAUSE_BOTTOM_OTHER_PAGES
        bottom = bottom_frac * page.rect.height + page.rect.y0
        split = CLAUSE_COLUMN_SPLIT * page.rect.width + page.rect.x0
        ws = [w for w in page_words(page) if top <= w['cy'] < bottom]
        for column in ([w for w in ws if w['cx'] < split], [w for w in ws if w['cx'] >= split]):
            for line in group_lines(column, page.rect.height):
                collected.extend(_public(w, page_no) for w in line['words'])
    return {'text': ' '.join(w['word'] for w in collected), 'words': collected}

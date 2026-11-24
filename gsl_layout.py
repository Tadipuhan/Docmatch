"""Tata letak halaman 1 GSL: kotak terukur + penyesuaian ke garis formulir.

Kenapa modul ini ada (audit v1.8.29)
  * Sel Initial Carriage / Place of Receipt / Vessel / Port of Loading / Port of
    Discharge / Final Destination bergeser SATU BARIS. Nilai Vessel dan Port of
    Loading (y ~ .358) jatuh ke sel Initial Carriage / Place of Receipt, sedangkan
    sel Vessel / Port of Loading hanya memuat caption "PORT OF DESTINATION".
  * Notify Party (.237-.341) menjangkau baris Initial Carriage.
  * Tepi kanan formulir adalah x = .906, bukan .98.

BOX_* di bawah diukur dari garis formulir pada kedua PDF GSL sampel (raster 100 dpi,
koordinat dinormalisasi terhadap halaman). Lalu detect_rules() membaca garis
horizontal/vertikal dari halaman yang sedang dibuka dan snap_box() menggeser tepi
kotak ke garis terdekat (<= SNAP_TOLERANCE). Jika tidak ada garis di dekatnya, nilai
terukur dipakai apa adanya dan diberi catatan; tidak ada tebakan.

Caption formulir pada PDF GSL berupa gambar latar, bukan teks Type3, jadi sel boleh
mencakup seluruh kotak termasuk area caption saat membaca teks Type3. Untuk OCR,
gunakan inset_for_ocr() agar caption tidak ikut terbaca.
"""
from __future__ import annotations

SNAP_TOLERANCE = 0.008          # 0,8% tinggi/lebar halaman (~6 pt)
RULE_DPI = 100
DARK_LEVEL = 215                # piksel < ini dianggap bagian dari garis
MIN_RULE_FRACTION = 0.12        # garis horizontal minimal 12% lebar halaman

X_LEFT, X_MID, X_RIGHT = 0.062, 0.485, 0.906

# (x0, y0, x1, y1) dinormalisasi terhadap halaman 1
GSL_BOXES = {
    'Shipper': (X_LEFT, .059, X_MID, .146),
    'Booking Number': (X_MID, .059, .695, .089),
    'Waybill Number': (.695, .059, X_RIGHT, .089),
    'Consignee': (X_LEFT, .146, X_MID, .233),
    'Forwarding Agent': (X_MID, .146, X_RIGHT, .204),
    'Notify Party': (X_LEFT, .233, X_MID, .319),
    'Point and Country of Origin': (X_MID, .204, X_RIGHT, .233),
    'Remarks': (X_MID, .233, X_RIGHT, .376),
    'Initial Carriage': (X_LEFT, .319, .274, .347),
    'Place of Receipt': (.274, .319, X_MID, .347),
    'Vessel': (X_LEFT, .347, .274, .376),
    'Port of Loading': (.274, .347, X_MID, .376),
    'Port of Discharge': (X_LEFT, .376, .274, .405),
    'Final Destination': (.274, .376, X_MID, .405),
    'Further Routing': (X_MID, .376, X_RIGHT, .405),
    'Main - Container & Seal': (X_LEFT, .434, .274, .673),
    'Main - Cargo Description': (.274, .434, X_RIGHT, .673),
    'Main - Clauses': (X_LEFT, .687, X_RIGHT, .801),
    'Freight Payable At': (.591, .863, X_RIGHT, .892),
    'Place & Date of Issue': (.591, .892, X_RIGHT, .920),
}

# Tinggi caption cetak (fraksi halaman) pada bagian atas tiap kotak, untuk OCR.
CAPTION_HEIGHT = {
    'Shipper': .014, 'Booking Number': .014, 'Waybill Number': .014, 'Consignee': .014,
    'Forwarding Agent': .014, 'Notify Party': .014, 'Point and Country of Origin': .014,
    'Remarks': .014, 'Initial Carriage': .012, 'Place of Receipt': .012, 'Vessel': .012,
    'Port of Loading': .012, 'Port of Discharge': .012, 'Final Destination': .012,
    'Further Routing': .012, 'Main - Container & Seal': 0, 'Main - Cargo Description': 0,
    'Main - Clauses': 0, 'Freight Payable At': .012, 'Place & Date of Issue': .012,
}


# ----------------------------------------------------------------------------
# Deteksi garis (fungsi murni di atas buffer grayscale)
# ----------------------------------------------------------------------------
def _runs(flags, min_len):
    out, start = [], None
    for index, value in enumerate(flags):
        if value:
            if start is None:
                start = index
        elif start is not None:
            if index - start >= min_len:
                out.append((start, index))
            start = None
    if start is not None and len(flags) - start >= min_len:
        out.append((start, len(flags)))
    return out


def _merge(lines, gap):
    """Gabungkan garis tebal (beberapa piksel) menjadi satu koordinat."""
    merged = []
    for pos, a, b in sorted(lines):
        if merged and pos - merged[-1][-1] <= gap and a < merged[-1][2] and b > merged[-1][1]:
            last = merged[-1]
            merged[-1] = [(last[0] + pos) / 2, min(last[1], a), max(last[2], b), pos]
        else:
            merged.append([pos, a, b, pos])
    return [(m[0], m[1], m[2]) for m in merged]


def detect_rules(gray: bytes, width: int, height: int):
    """Kembalikan (horizontal, vertikal).

    horizontal: [(y, x0, x1)] ; vertikal: [(x, y0, y1)] semuanya 0..1.
    """
    dark = [v < DARK_LEVEL for v in gray]
    horizontal = []
    min_h = max(2, int(width * MIN_RULE_FRACTION))
    for y in range(height):
        row = dark[y * width:(y + 1) * width]
        for a, b in _runs(row, min_h):
            horizontal.append((y, a, b))
    vertical = []
    min_v = max(2, int(height * 0.025))
    for x in range(width):
        col = dark[x::width]
        for a, b in _runs(col, min_v):
            vertical.append((x, a, b))
    h = [(y / height, a / width, b / width) for y, a, b in _merge(horizontal, 2)]
    v = [(x / width, a / height, b / height) for x, a, b in _merge(vertical, 2)]
    return h, v


def snap_box(box, horizontal, vertical, tolerance=SNAP_TOLERANCE):
    """Geser tiap tepi kotak ke garis terdekat yang melintasi kotak itu.

    Kembalikan (kotak_baru, catatan). catatan berisi tepi yang tidak ditemukan
    garisnya (nilai terukur dipertahankan).
    """
    x0, y0, x1, y1 = box
    notes = []

    def pick(candidates, target):
        best = None
        for pos in candidates:
            gap = abs(pos - target)
            if gap <= tolerance and (best is None or gap < best[0]):
                best = (gap, pos)
        return None if best is None else best[1]

    def overlaps(a, b, lo, hi):
        return min(b, hi) - max(a, lo) >= 0.5 * (hi - lo)

    h_rows = [y for y, a, b in horizontal if overlaps(a, b, x0, x1)]
    v_cols = [x for x, a, b in vertical if overlaps(a, b, y0, y1)]
    new = []
    for name, value, pool in (('kiri', x0, v_cols), ('atas', y0, h_rows),
                              ('kanan', x1, v_cols), ('bawah', y1, h_rows)):
        found = pick(pool, value)
        if found is None:
            notes.append(name)
            new.append(value)
        else:
            new.append(found)
    return tuple(new), notes


def inset_for_ocr(name, box, margin=0.002):
    """Kotak OCR: lewati caption cetak di bagian atas dan sedikit tepi garis."""
    x0, y0, x1, y1 = box
    caption = CAPTION_HEIGHT.get(name, 0)
    return (x0 + margin, y0 + caption + margin, x1 - margin, y1 - margin)


# ----------------------------------------------------------------------------
# Integrasi PyMuPDF (belum diuji di lingkungan audit)
# ----------------------------------------------------------------------------
_RULE_CACHE = {}


def rules_for_page(page):
    """Render halaman ke grayscale dan deteksi garis. None bila gagal."""
    try:
        import pymupdf as fitz
        key = (getattr(page.parent, 'name', ''), page.number)
        if key in _RULE_CACHE:
            return _RULE_CACHE[key]
        zoom = RULE_DPI / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
        samples = bytes(pix.samples)
        if pix.stride != pix.width:       # buang padding baris bila ada
            samples = b''.join(samples[r * pix.stride: r * pix.stride + pix.width]
                               for r in range(pix.height))
        result = detect_rules(samples, pix.width, pix.height)
        if len(_RULE_CACHE) > 16:
            _RULE_CACHE.clear()
        _RULE_CACHE[key] = result
        return result
    except Exception:
        return None


def boxes_for_page(page, boxes=None):
    """Kotak GSL untuk halaman ini: terukur lalu disesuaikan ke garis bila terdeteksi.

    Kembalikan (dict nama -> kotak, dict nama -> catatan tepi tak terdeteksi).
    """
    boxes = GSL_BOXES if boxes is None else boxes
    rules = rules_for_page(page)
    if rules is None:
        return dict(boxes), {name: ['tanpa deteksi garis'] for name in boxes}
    horizontal, vertical = rules
    out, notes = {}, {}
    for name, box in boxes.items():
        out[name], notes[name] = snap_box(box, horizontal, vertical)
    return out, notes

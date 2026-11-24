"""Pengganti PyMuPDF TIPIS berbasis pdfplumber, HANYA untuk lingkungan tanpa PyMuPDF.

Tujuan: menjalankan kode ekstraksi asli (waybill_rules / flexible_reference) pada PDF
berlapis teks (ANL/CNC/surat rujukan) untuk menguji nilai field dan koordinat.
Hanya API yang dipakai jalur ANL + flexible yang diimplementasikan. Geometri kata dari
pdfplumber mendekati, tetapi tidak identik dengan MuPDF (tinggi kotak sedikit berbeda).

Pemakaian:  import pdf_shim; pdf_shim.install()   # tidak berbuat apa-apa jika PyMuPDF ada.
"""
from __future__ import annotations
import sys
import types


class Point:
    def __init__(self, x, y=None):
        if y is None:
            x, y = x
        self.x, self.y = float(x), float(y)

    def __add__(self, o):
        return Point(self.x + o.x, self.y + o.y)

    def __sub__(self, o):
        return Point(self.x - o.x, self.y - o.y)

    def __mul__(self, k):
        return Point(self.x * k, self.y * k)

    def __iter__(self):
        return iter((self.x, self.y))


class Rect:
    def __init__(self, *a):
        if len(a) == 1:
            a = tuple(a[0])
        if len(a) == 2:
            a = (*tuple(a[0]), *tuple(a[1]))
        self.x0, self.y0, self.x1, self.y1 = (float(v) for v in a)

    def __iter__(self):
        return iter((self.x0, self.y0, self.x1, self.y1))

    def __getitem__(self, i):
        return (self.x0, self.y0, self.x1, self.y1)[i]

    def __repr__(self):
        return 'Rect(%.2f, %.2f, %.2f, %.2f)' % tuple(self)

    tl = property(lambda s: Point(s.x0, s.y0))
    br = property(lambda s: Point(s.x1, s.y1))
    width = property(lambda s: s.x1 - s.x0)
    height = property(lambda s: s.y1 - s.y0)
    is_empty = property(lambda s: s.x1 <= s.x0 or s.y1 <= s.y0)

    def contains(self, o):
        if isinstance(o, Rect):
            return self.x0 <= o.x0 and self.y0 <= o.y0 and o.x1 <= self.x1 and o.y1 <= self.y1
        x, y = (o.x, o.y) if isinstance(o, Point) else tuple(o)[:2]
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def intersects(self, o):
        o = Rect(o)
        return min(self.x1, o.x1) > max(self.x0, o.x0) and min(self.y1, o.y1) > max(self.y0, o.y0)

    def __and__(self, o):
        o = Rect(o)
        return Rect(max(self.x0, o.x0), max(self.y0, o.y0), min(self.x1, o.x1), min(self.y1, o.y1))

    def __or__(self, o):
        o = Rect(o)
        return Rect(min(self.x0, o.x0), min(self.y0, o.y0), max(self.x1, o.x1), max(self.y1, o.y1))


class _Page:
    def __init__(self, doc, index, plumber_page):
        self.parent, self.number, self._p = doc, index, plumber_page
        self.rect = Rect(0, 0, float(plumber_page.width), float(plumber_page.height))
        self._words = None
        self._lines = None

    def _all_words(self):
        if self._words is None:
            ws = self._p.extract_words(x_tolerance=1.2, y_tolerance=2, keep_blank_chars=False,
                                       use_text_flow=False)
            ordered = sorted(ws, key=lambda w: (round(w['top'] / 3), w['x0']))
            self._words = [(w['x0'], w['top'], w['x1'], w['bottom'], w['text'], 0, i, j)
                           for j, (i, w) in enumerate(((k, w) for k, w in enumerate(ordered)))]
        return self._words

    def get_text(self, kind='text', clip=None, sort=False, **kw):
        if kind == 'words':
            words = self._all_words()
            if clip is not None:
                c = Rect(clip)
                words = [w for w in words if c.intersects(Rect(w[:4]))]
            return list(words)
        if kind == 'dict':
            if self._lines is None:
                # MuPDF memecah baris bila celah horizontal > ~0,8 em (mis. kolom tabel).
                words = sorted(self._all_words(), key=lambda w: (round(w[1] / 3), w[0]))
                rows, current = [], []
                for w in words:
                    if current:
                        prev = current[-1]
                        same_row = abs((w[1] + w[3]) / 2 - (prev[1] + prev[3]) / 2) < 0.5 * (prev[3] - prev[1])
                        gap = w[0] - prev[2]
                        if same_row and gap <= 0.8 * (prev[3] - prev[1]):
                            current.append(w)
                            continue
                        rows.append(current)
                        current = []
                    current.append(w)
                if current:
                    rows.append(current)
                blocks = []
                for line in rows:
                    box = (min(w[0] for w in line), min(w[1] for w in line),
                           max(w[2] for w in line), max(w[3] for w in line))
                    text = ' '.join(w[4] for w in line)
                    blocks.append({'type': 0, 'bbox': box, 'lines': [{'bbox': box, 'spans': [
                        {'text': text, 'bbox': box}]}]})
                self._lines = blocks
            return {'blocks': list(self._lines)}
        raise NotImplementedError(kind)

    def search_for(self, text, **kw):
        out = []
        for m in self._p.search(text, regex=False, case=True):
            out.append(Rect(m['x0'], m['top'], m['x1'], m['bottom']))
        return out


class _Doc:
    def __init__(self, path):
        import pdfplumber
        self.name = str(path)
        self._pdf = pdfplumber.open(str(path))
        self._pages = [_Page(self, i, p) for i, p in enumerate(self._pdf.pages)]

    def __len__(self):
        return len(self._pages)

    def __getitem__(self, i):
        return self._pages[i]

    def __iter__(self):
        return iter(self._pages)

    def __bool__(self):
        return True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self):
        self._pdf.close()


def install():
    try:
        import pymupdf  # noqa: F401
        return False
    except ImportError:
        pass
    mod = types.ModuleType('pymupdf')
    mod.Rect, mod.Point, mod.open = Rect, Point, _Doc
    sys.modules['pymupdf'] = mod
    sys.modules.setdefault('fitz', mod)
    return True

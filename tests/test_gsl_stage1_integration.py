"""Tahap 1 GSL end-to-end: semua field Waybill terbaca dan perbedaan yang benar muncul.

* Dengan PyMuPDF terpasang: menjalankan jalur produksi sungguhan (tanpa stub).
* Tanpa PyMuPDF (lingkungan audit): PyMuPDF diganti stub tipis dan
  recover_page_words diganti hasil dekode pypdf. Yang diuji tetap kode asli
  waybill_rules.extract / compare_waybills, bukan PyMuPDF.
"""
import sys
import types
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytest.importorskip('pypdf')
import samples  # noqa: E402

try:
    import pymupdf  # noqa: F401
    REAL_FITZ = True
except ImportError:
    REAL_FITZ = False

# Perbedaan yang BENAR antara GSL_SWB_26B92KR1C (A) dan GSL_SWB_26BX2VN1B (B), halaman 1.
EXPECTED_DIFFS = {
    'Booking Number': 'Perubahan', 'Waybill Number': 'Perubahan', 'Consignee': 'Perubahan',
    'Notify Party': 'Perubahan', 'Remarks': 'Perubahan', 'Vessel': 'Perubahan',
    'Port of Discharge': 'Perubahan', 'Final Destination': 'Berlebih',
    'Main - Cargo Description': 'Perubahan', 'Place & Date of Issue': 'Perubahan',
}
EXPECTED_SAME = ['Shipper', 'Port of Loading', 'Main - Clauses', 'Freight Payable At',
                 'Initial Carriage', 'Place of Receipt', 'Forwarding Agent',
                 'Point and Country of Origin', 'Further Routing']


class _Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, o):
        return _Point(self.x + o.x, self.y + o.y)

    def __mul__(self, k):
        return _Point(self.x * k, self.y * k)


class _Rect:
    def __init__(self, *a):
        if len(a) == 1:
            a = tuple(a[0])
        self.x0, self.y0, self.x1, self.y1 = [float(v) for v in a]

    def __iter__(self):
        return iter((self.x0, self.y0, self.x1, self.y1))

    @property
    def tl(self):
        return _Point(self.x0, self.y0)

    @property
    def br(self):
        return _Point(self.x1, self.y1)

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    def contains(self, p):
        return self.x0 <= p.x <= self.x1 and self.y0 <= p.y <= self.y1


def _install_fake_fitz(monkeypatch):
    from pypdf import PdfReader
    fake = types.ModuleType('pymupdf')
    fake.Rect = _Rect
    fake.Point = _Point

    class Page:
        def __init__(self, index):
            self.number, self.rect = index, _Rect(0, 0, 612, 792)

        def get_text(self, kind='text', **kw):
            # Teks Type3 GSL tidak terdekode oleh lapisan teks biasa: kosong. Cukup untuk
            # detect_flexible_pdf (v1.8.33+) yang menyimpulkan 'bukan surat rujukan'.
            return {'blocks': []} if kind == 'dict' else []

        def search_for(self, *a, **k):
            return []

    class Doc:
        def __init__(self, path):
            self.path, self.n = path, len(PdfReader(path).pages)

        def __len__(self):
            return self.n

        def __getitem__(self, i):
            return Page(i)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def __bool__(self):
            return True

    fake.open = Doc
    monkeypatch.setitem(sys.modules, 'pymupdf', fake)
    for name in ('waybill_rules', 'gsl_font_recovery', 'gsl_layout'):
        sys.modules.pop(name, None)
    import waybill_rules as w
    import gsl_layout

    def recover(doc, page_no):
        import gsl_font_recovery as gfr
        out = []
        for x, y, text in samples.pypdf_lines_xy(doc.path, page_no):
            px, py = x * 612, y * 792
            line = []
            for word in text.split():           # lebar kata ditaksir ~4,9 pt per karakter (huruf kapital tebal 7,5 pt)
                width = 4.9 * len(word)
                line.append({'word': word, 'rect': _Rect(px, py - 3, px + width, py + 3), 'page': page_no})
                px += width + 2.0
            out += gfr.assign_run_anchors(line, 7.48)
        return out

    import gsl_font_recovery as gfr
    monkeypatch.setattr(w, 'recover_page_words', recover)
    monkeypatch.setattr(w, 'word_anchor', gfr.word_anchor)
    monkeypatch.setattr(w, 'boxes_for_page', lambda page: (dict(gsl_layout.GSL_BOXES), {}))
    return w


def _compare(monkeypatch):
    a, b = samples.sample('gsl_a'), samples.sample('gsl_b')
    if not (a and b):
        pytest.skip('PDF sampel tidak tersedia')
    if REAL_FITZ:
        import waybill_rules as w
    else:
        w = _install_fake_fitz(monkeypatch)
    diffs, locs = w.compare_waybills(a, b, selected=list(w.GSL_PAGE1_FIELDS), profile='waybill_gsl')
    return w, diffs, locs


def test_all_page1_fields_are_readable(monkeypatch):
    w, diffs, locs = _compare(monkeypatch)
    assert w.GSL_SKIPPED_FIELDS == [], 'Field belum terbaca: %s' % w.GSL_SKIPPED_FIELDS


def test_expected_differences_only(monkeypatch):
    w, diffs, locs = _compare(monkeypatch)
    got = {d.field: d.kind for d in diffs}
    assert got == EXPECTED_DIFFS, (sorted(set(EXPECTED_DIFFS) ^ set(got)), got)
    assert len(diffs) == len(locs)


def test_identical_fields_not_reported(monkeypatch):
    w, diffs, locs = _compare(monkeypatch)
    reported = {d.field for d in diffs}
    assert not (reported & set(EXPECTED_SAME))


def test_highlights_only_changed_words(monkeypatch):
    w, diffs, locs = _compare(monkeypatch)
    by_field = {d.field: loc for d, loc in zip(diffs, locs)}
    ref_hits = by_field['Consignee'][0]['hits']
    words_marked = len(ref_hits)
    # "BRIDGESTONE TIRE SALES" sama pada kedua dokumen, jadi tidak ikut ditandai.
    ref = w.extract(samples.sample('gsl_a'), ['Consignee'], 'waybill_gsl')['Consignee']['words']
    assert 0 < words_marked < len(ref)


EXPECTED_TEXT = {
    'gsl_a': {
        'Booking Number': 'GOSUJKT8132504', 'Waybill Number': 'GOSUJKT8132504',
        'Shipper': 'PT. BRIDGESTONE TIRE INDONESIA KAWASAN INDUSTRI SURYACIPTA, JL. SURYA UTAMA KAV. 8-13, KEL. KUTAMEKAR, KEC. CIAMPEL, KAB. KARAWANG,*',
        'Notify Party': 'HANEXPRESS CO.,LTD (BUSAN) RM503, EUNSANBAY B/D,88, JUNGANG-DAERO, JUNG-GU, BUSAN, KOREA***',
        'Vessel': 'INTERASIA ENGAGE N044', 'Port of Loading': 'JAKARTA, INDONESIA',
        'Port of Discharge': 'BUSAN, KOREA', 'Final Destination': '',
        'Freight Payable At': 'SINGAPORE', 'Place & Date of Issue': 'JAKARTA on 24/09/2026',
    },
    'gsl_b': {
        'Notify Party': 'YUSEN LOGISTICS (VIETNAM) CO., LTD. HOCHIMINH BRANCH 2A-4A TON DUC THANG ST, Sai Gon Ward, HOCHIMINH CITY***',
        'Vessel': 'MTT SENARI 046W', 'Port of Discharge': 'TAN CANG HIEP PHUOC PORT',
        'Final Destination': 'CAT LAI TERMINAL - HO CHI MINH CITY',
        'Place & Date of Issue': 'JAKARTA on 16/10/2026',
    },
}


def test_field_texts_are_complete_and_exact(monkeypatch):
    a, b = samples.sample('gsl_a'), samples.sample('gsl_b')
    if not (a and b):
        pytest.skip('PDF sampel tidak tersedia')
    w = None
    if REAL_FITZ:
        import waybill_rules as w
    else:
        w = _install_fake_fitz(monkeypatch)
    for key, path in (('gsl_a', a), ('gsl_b', b)):
        got = w.extract(path, list(w.GSL_PAGE1_FIELDS), 'waybill_gsl')
        for name, expected in EXPECTED_TEXT[key].items():
            text = ' '.join(x['word'] for x in got[name]['words'])
            assert text == expected, (key, name, text)

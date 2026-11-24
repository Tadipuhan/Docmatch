"""Kotak GSL harus menangkap isi yang benar dan menempel pada garis formulir."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytest.importorskip('pypdf')
import samples  # noqa: E402
import gsl_layout as L  # noqa: E402

# nama kotak -> teks yang HARUS ada di dalamnya (awal baris, dari tampilan visual)
EXPECT = {
    'gsl_a': {
        'Shipper': ['PT. BRIDGESTONE TIRE INDONESIA'],
        'Booking Number': ['GOSUJKT8132504'],
        'Consignee': ['BRIDGESTONE TIRE SALES KOREA LTD.'],
        'Notify Party': ['HANEXPRESS CO.,LTD (BUSAN)', 'BUSAN, KOREA***'],
        'Vessel': ['INTERASIA ENGAGE N044'],
        'Port of Loading': ['JAKARTA, INDONESIA'],
        'Port of Discharge': ['BUSAN, KOREA'],
        'Freight Payable At': ['SINGAPORE'],
        'Place & Date of Issue': ['JAKARTA on 24/09/2026'],
        'Main - Clauses': ['CLAUSES AS PER ATT.LIST'],
    },
    'gsl_b': {
        'Vessel': ['MTT SENARI 046W'],
        'Port of Loading': ['JAKARTA, INDONESIA'],
        'Port of Discharge': ['TAN CANG HIEP PHUOC PORT'],
        'Final Destination': ['CAT LAI TERMINAL - HO CHI MINH CITY'],
        'Notify Party': ['YUSEN LOGISTICS (VIETNAM) CO., LTD.', 'Sai Gon Ward,'],
    },
}
MUST_BE_EMPTY = ['Initial Carriage', 'Place of Receipt']   # kosong pada kedua sampel


START_X_TOLERANCE = 0.004   # awal baris (Tm) bisa menyentuh garis kiri kotak


def _inside(box, x, y):
    # kedua tepi x digeser sama besar supaya kotak bertetangga tidak tumpang tindih
    return box[0] - START_X_TOLERANCE <= x < box[2] - START_X_TOLERANCE and box[1] <= y <= box[3]


def _contents(key):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    lines = samples.pypdf_lines_xy(path, 0)
    return {name: [t for x, y, t in lines if _inside(box, x, y)]
            for name, box in L.GSL_BOXES.items()}


@pytest.mark.parametrize('key', ['gsl_a', 'gsl_b'])
def test_boxes_capture_expected_text(key):
    got = _contents(key)
    for name, expected in EXPECT[key].items():
        for text in expected:
            assert any(text in line for line in got[name]), (name, text, got[name])


@pytest.mark.parametrize('key', ['gsl_a', 'gsl_b'])
def test_vessel_row_not_leaking_into_initial_carriage(key):
    got = _contents(key)
    for name in MUST_BE_EMPTY:
        assert got[name] == [], (name, got[name])


@pytest.mark.parametrize('key', ['gsl_a', 'gsl_b'])
def test_no_text_line_belongs_to_two_boxes(key):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    for x, y, t in samples.pypdf_lines_xy(path, 0):
        owners = [n for n, b in L.GSL_BOXES.items() if _inside(b, x, y)]
        assert len(owners) <= 1, (t, owners)


@pytest.mark.parametrize('key', ['gsl_a', 'gsl_b'])
def test_boxes_snap_to_real_form_rules(key):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    rendered = samples.render_gray(path, 0)
    if rendered is None:
        pytest.skip('Tidak ada renderer (PyMuPDF atau pdftoppm+PIL)')
    gray, w, h = rendered
    horizontal, vertical = L.detect_rules(gray, w, h)
    assert len(horizontal) >= 15 and len(vertical) >= 5
    for name, box in L.GSL_BOXES.items():
        snapped, notes = L.snap_box(box, horizontal, vertical)
        # Edge kiri/atas/kanan/bawah yang tidak punya garis hanya boleh sedikit.
        assert len(notes) <= 2, (name, notes)
        for a, b in zip(box, snapped):
            assert abs(a - b) <= L.SNAP_TOLERANCE + 1e-9, (name, box, snapped)


def test_inset_skips_caption():
    box = L.GSL_BOXES['Vessel']
    inner = L.inset_for_ocr('Vessel', box)
    assert inner[1] > box[1] + L.CAPTION_HEIGHT['Vessel'] - 1e-9
    assert inner[0] > box[0] and inner[2] < box[2] and inner[3] < box[3]

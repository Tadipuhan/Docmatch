"""Profil ANL/CNC: tiap parameter harus menangkap nilai yang benar dari sampel."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import samples  # noqa: E402

# Dibaca langsung dari definisi FIELDS tanpa mengimpor PyMuPDF.
import re  # noqa: E402
_src = (Path(__file__).resolve().parent.parent / 'waybill_rules.py').read_text(encoding='utf-8')
_ns = {}
exec(re.search(r'(?m)^FIELDS = \[.*?^\]\n', _src, re.S).group(0), _ns)
FIELDS = dict(_ns['FIELDS'])

EXPECT = {
    'anl': {
        'Shipper': ['PT. BRIDGESTONE TIRE INDONESIA'],
        'Consignee': ['BRIDGESTONE MINING SOLUTIONS'],
        'Notify Party': ['NORTH QUEENSLAND CUSTOMS SERVICES'],
        'Voyage Number': ['028N'],
        'Waybill Number': ['KTJ0314419'],
        'Freight To Be Paid At': ['TOKYO'],
        'Number of Original Waybills': ['ZERO (0)'],
        'Vessel': ['SINAR CARITA'],
        'Port of Loading': ['JAKARTA, INDONESIA'],
        'Port of Discharge': ['MELBOURNE, AUSTRALIA'],
        'Final Place of Delivery': ['BURNIE, AUSTRALIA'],
        'Container & Seal': ['CMAU2254992', 'SEAL CMACGMM2872147'],
        'No & Kind of Packages': ['1 x 20ST'],
        'Cargo Description': ['320 PACKAGE(S)', 'INVOICE NO. 26B63EM4', 'MADE IN INDONESIA'],
        'Weight & Measurement': ['4911.650', '17.800'],
        'Place & Date of Issue': ['JAKARTA', '28 SEP 2026'],
    },
    'cnc': {
        'Voyage Number': ['CS10H0N'],
        'Waybill Number': ['ARM0461957'],
        'Consignee': ['TONG SENG CO., LTD.'],
        'Freight To Be Paid At': ['SINGAPORE'],
        'Vessel': ['HG SKYLINE'],
        'Port of Loading': ['JAKARTA PORT, INDONESIA'],
        'Port of Discharge': ['HONG KONG PORT'],
        'Final Place of Delivery': ['***********************'],
        'Container & Seal': ['TGCU5588025', 'ECMU5426613'],
        'No & Kind of Packages': ['1 x 40HC'],
        'Cargo Description': ['768 PIECE(S)', '1,521 TIRES', 'REF NO. : 26B92HK1'],
        'Place & Date of Issue': ['JAKARTA', '18 OCT 2026'],
    },
}
# Isi yang tidak boleh bocor ke parameter lain
FORBIDDEN = {
    'Container & Seal': ['PACKAGE(S)', 'PIECE(S)', '20ST', '40HC'],
    'Cargo Description': ['CMAU2254992', 'TGCU5588025', '1 x 20ST', '1 x 40HC'],
    'Vessel': ['JAKARTA'],
    'Port of Loading': ['SINAR', 'HG'],
}


def _field_text(key):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    got = samples.page_words(path, 0)
    if got is None:
        pytest.skip('Tidak ada PyMuPDF/pdftotext')
    width, height, words = got
    out = {}
    for name, (x0, y0, x1, y1) in FIELDS.items():
        if name == 'Additional Clauses':
            continue
        inside = [w for w in words
                  if x0 <= (w[0] + w[2]) / 2 / width <= x1 and y0 <= (w[1] + w[3]) / 2 / height <= y1]
        inside.sort(key=lambda w: (round(w[1] / 3), w[0]))
        out[name] = ' '.join(w[4] for w in inside)
    return out


@pytest.mark.parametrize('key', ['anl', 'cnc'])
def test_fields_capture_expected_values(key):
    text = _field_text(key)
    for name, expected in EXPECT[key].items():
        for item in expected:
            assert item in text[name], (name, item, text[name][:160])


@pytest.mark.parametrize('key', ['anl', 'cnc'])
def test_no_cross_field_leakage(key):
    text = _field_text(key)
    for name, banned in FORBIDDEN.items():
        for item in banned:
            assert item not in text[name], (name, item, text[name][:160])

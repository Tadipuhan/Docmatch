"""ANL/CNC/CMA CGM: nilai field, batas kotak, dan keterpisahan antar-field pada 3 formulir nyata.

Dengan PyMuPDF terpasang: jalur produksi sungguhan. Tanpa PyMuPDF: pdf_shim (pdfplumber).
Teks dibandingkan sebagai multiset token supaya tidak bergantung pada urutan kata mentah mesin.
"""
import re
import sys
from collections import Counter
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdf_shim  # noqa: E402
pdf_shim.install()
import samples  # noqa: E402
import anl_form  # noqa: E402
import waybill_rules as wb  # noqa: E402

EXPECT = {
    'anl3': {
        'Shipper': 'PT. BRIDGESTONE TIRE INDONESIA KAWASAN INDUSTRI SURYACIPTA, JL. SURYA UTAMA KAV. 8-13, KEL. KUTAMEKAR, KEC. CIAMPEL, KAB. KARAWANG PROP. JAWA BARAT 41363*',
        'Consignee': 'BRIDGESTONE AUSTRALIA LIMITED. 210 GREENHILL ROAD, EASTWOOD SOUTH AUSTRALIA 5063 AUSTRALIA DELIVER TO BRIDGESTONE AUSTRALIA LTD. **',
        'Notify Party': 'MAINFREIGHT AIR & OCEAN, ADELAIDE 76-82 GALLIPOLI DRIVE REGENCY PARK SA 5010 PH: 08 8300 5555 EMAIL: BRIDGESTONEIMPORTS@MAINFREIGHT.COM',
        'Voyage Number': '0SQ5AN', 'Waybill Number': 'KTJ0315847', 'Pre-Carriage': '', 'Place of Receipt': '',
        'Freight To Be Paid At': 'SINGAPORE', 'Number of Original Waybills': 'ZERO (0)',
        'Vessel': 'BANGKOK', 'Port of Loading': 'JAKARTA, INDONESIA', 'Port of Discharge': 'FREMANTLE, AUSTRALIA',
        'Final Place of Delivery': '***********************',
        'Container & Seal': 'CAAU8541905 SEAL M2856222 ECMU5593288 SEAL M2853517 TXGU4183166 SEAL M2853599',
        'No & Kind of Packages': '1 x 40HC 1 x 40HC 1 x 40HC',
        'Weight & Measurement': '8455.454 3700 72.604 7495.639 3430 70.769 8258.375 3700 72.013 24209.468 10830 215.386',
        'Place & Date of Issue': 'JAKARTA 21 OCT 2026',
    },
    'anl': {
        'Voyage Number': '028N', 'Waybill Number': 'KTJ0314419', 'Freight To Be Paid At': 'TOKYO',
        'Number of Original Waybills': 'ZERO (0)', 'Vessel': 'SINAR CARITA', 'Port of Loading': 'JAKARTA, INDONESIA',
        'Port of Discharge': 'MELBOURNE, AUSTRALIA', 'Final Place of Delivery': 'BURNIE, AUSTRALIA',
        'Container & Seal': 'CMAU2254992 SEAL CMACGMM2872147', 'No & Kind of Packages': '1 x 20ST',
        'Weight & Measurement': '4911.650 2160 17.800 4911.650 2160 17.800',
        'Place & Date of Issue': 'JAKARTA 28 SEP 2026',
    },
    'cnc': {
        'Voyage Number': 'CS10H0N', 'Waybill Number': 'ARM0461957', 'Freight To Be Paid At': 'SINGAPORE',
        'Number of Original Waybills': 'ZERO (0)', 'Vessel': 'HG SKYLINE', 'Port of Loading': 'JAKARTA PORT, INDONESIA',
        'Port of Discharge': 'HONG KONG PORT', 'Final Place of Delivery': '***********************',
        'Consignee': "TONG SENG CO., LTD. FLAT 1106-7 NEW WORLD TOWER, 16-18 QUEEN'S ROAD CENTRAL, HONG KONG",
        'Notify Party': "TONG SENG CO., LTD. FLAT 1106-7 NEW WORLD TOWER, 16-18 QUEEN'S ROAD CENTRAL, HONG KONG",
        'Container & Seal': 'TGCU5588025 SEAL M2574640 N/M, N/N ECMU5426613 SEAL M2574639 N/M, N/N',
        'No & Kind of Packages': '1 x 40HC 1 x 40HC',
        'Weight & Measurement': '8299.236 3650 72.675 9451.868 3700 72.510 17751.104 7350 145.185',
        'Place & Date of Issue': 'JAKARTA 18 OCT 2026',
    },
}
SEMANTIC_TOTALS = {'anl3': '24209.468 10830 215.386', 'anl': '4911.650 2160 17.800', 'cnc': '17751.104 7350 145.185'}
CARGO_MUST = {
    'anl3': ['526 PACKAGE(S)', 'INVOICE NO. 26BX3AL1A', 'GEDSON@BRIDGESTONE.COM.AU', '727 PACKAGE(S)', '567 PACKAGE(S)'],
    'anl': ['320 PACKAGE(S)', 'INVOICE NO. 26B63EM4', 'MADE IN INDONESIA'],
    'cnc': ['768 PIECE(S)', '753 PIECE(S)', 'REF NO. : 26B92HK1', 'LC NO. 028-01-1601981'],
}
# teks cetak yang BUKAN nilai field mana pun (selain klausa)
PRINTED = ['voyage number', 'waybill number', 'port of loading', 'port of discharge', 'final place of delivery',
           'place and date of issue', 'pre carriage', 'place of receipt', 'freight to be paid at',
           'number of original waybills', 'notify party', 'weight in kgs', 'shipped on board',
           'as agents for the carrier', 'marks and nos', 'no and kind', 'signed for']


def _tokens(text):
    return Counter(text.split())


def _extract(key):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    return wb.extract(path, None, 'waybill_anl'), path


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_field_values_are_exact(key):
    result, _ = _extract(key)
    for name, expected in EXPECT[key].items():
        assert _tokens(result[name]['text']) == _tokens(expected), (name, result[name]['text'], expected)


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_no_printed_captions_or_footers_in_values(key):
    result, _ = _extract(key)
    for name, entry in result.items():
        if name == 'Additional Clauses':
            continue
        low = entry['text'].casefold()
        for phrase in PRINTED:
            assert phrase not in low, (name, phrase, entry['text'][:100])


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_cargo_description_complete_and_isolated(key):
    result, _ = _extract(key)
    text = result['Cargo Description']['text']
    for must in CARGO_MUST[key]:
        assert must in text, (must, text[:120])
    for banned in ('Shipped on Board', 'As agents for the Carrier', 'Weight in Kgs', 'CONTAINER(S)', 'GROSS WEIGHT'):
        assert banned.casefold() not in text.casefold(), banned


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_total_weight_line_is_separately_available(key):
    result, _ = _extract(key)
    entry = result['Weight & Measurement']
    assert entry['semantic_text'] == SEMANTIC_TOTALS[key]
    assert [w['word'] for w in entry['semantic_words']] == SEMANTIC_TOTALS[key].split()
    assert all(w.get('role') == 'total' for w in entry['semantic_words'])


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_every_word_box_lies_inside_its_field_box(key):
    result, path = _extract(key)
    import pymupdf as fitz
    with fitz.open(path) as doc:
        page = doc[0]
        W, H = page.rect.width, page.rect.height
    bounds = dict(anl_form.ANL_FIELDS)
    for name, entry in result.items():
        if name == 'Additional Clauses':
            continue
        x0, y0, x1, y1 = bounds[name]
        for w in entry['words']:
            r = w['rect']
            cx, cy = (r.x0 + r.x1) / 2 / W, (r.y0 + r.y1) / 2 / H
            assert x0 - 1e-6 <= cx <= x1 + 1e-6 and y0 - 1e-6 <= cy <= y1 + 1e-6, (name, w['word'], cx, cy)
            assert 3.0 <= (r.y1 - r.y0) <= 14.0, (name, w['word'], r.y1 - r.y0)


@pytest.mark.parametrize('key', ['anl3', 'anl', 'cnc'])
def test_no_word_belongs_to_two_fields(key):
    result, _ = _extract(key)
    seen = {}
    for name, entry in result.items():
        for w in entry['words']:
            if w.get('role') == 'total' and name == 'Weight & Measurement' and False:
                continue
            key_rect = tuple(round(v, 1) for v in w['rect']) + (w['page'],)
            assert key_rect not in seen or seen[key_rect] == name, (w['word'], name, seen.get(key_rect))
            seen[key_rect] = name


@pytest.mark.parametrize('key', ['anl3', 'cnc'])
def test_additional_clauses_two_columns_and_no_printed_terms(key):
    result, _ = _extract(key)
    text = result['Additional Clauses']['text']
    assert 'RECEIVED by the Carrier' not in text
    assert 'SIGNED FOR THE CARRIER' not in text
    assert 'last free day. without the need' not in text         # bug v1.8.33.1: dua kolom berselang-seling
    if key == 'anl3':
        left_end = text.index('available on the ANL website')
        right_start = text.index('(https://www.anl.com.au/products-services')
        assert left_end < right_start

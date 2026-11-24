"""Meratus Way Bill (logo GRAFIS) harus dikenali sebagai formulir carrier, bukan surat rujukan.

Gejala sebelum perbaikan: rujukan Meratus dibaca oleh pembaca label -> Consignee/Notify Party
diambil dari paragraf syarat di sisi kanan, caption terbaca sebagai nilai, status bar
"13 field perlu verifikasi". PDF di sini adalah REKONSTRUKSI sintetis dari tangkapan layar;
cek akhir tetap pada PDF Meratus asli.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdf_shim  # noqa: E402
pdf_shim.install()
import synthetic_forms as sf  # noqa: E402
import ref_letters  # noqa: E402
import flexible_reference as fr  # noqa: E402
import waybill_rules as wb  # noqa: E402

NAMES = list(wb.profile_field_names('waybill_meratus'))
PROFILE = 'waybill_meratus'


def _swb(tmp_path, name='swb.pdf', **kw):
    path = tmp_path / name
    sf.make_meratus_waybill(path, **kw)
    return str(path)


@pytest.mark.parametrize('logo_as_text', [False, True])
def test_meratus_waybill_is_a_carrier_form(logo_as_text, tmp_path):
    assert fr.detect_flexible_pdf(_swb(tmp_path, logo_as_text=logo_as_text), NAMES) is False


def test_values_come_from_calibrated_cells_not_labels_or_boilerplate(tmp_path):
    data = wb.extract(_swb(tmp_path), profile=PROFILE)
    assert data['Waybill Number']['text'] == 'JKT26104490'
    assert data['Shipper']['text'].startswith('PT. BRIDGESTONE TIRE INDONESIA')
    assert data['Consignee']['text'] == 'BRIDGESTONE TYRES (P.N.G) PTY. LTD. P.O. BOX 458 LAE'
    assert data['Notify Party']['text'] == 'BRIDGESTONE TYRES (P.N.G) PTY. LTD. P.O. BOX 458 LAE'
    assert data['Vessel']['text'] == 'MERATUS KARIMUN'
    assert data['Voyage Number']['text'] == 'GI058E'
    assert data['Port of Loading']['text'] == 'JAKARTA, INDONESIA'
    assert data['Port of Discharge']['text'] == 'LAE, PAPUA NEW GUINEA'
    assert data['Gross Weight']['text'] == '11,092.239 KGS'
    assert data['Gross Measurement']['text'] == '73.841 CBM'
    printed = ['voy. no.', 'port of loading', 'port of discharge', 'received by the carrier',
               'in accepting this bill', 'in witness whereof', 'reference no', 'measurement']
    for name in ('Shipper', 'Consignee', 'Notify Party', 'Vessel', 'Voyage Number', 'Port of Loading',
                 'Port of Discharge', 'Gross Weight'):
        low = data[name]['text'].casefold()
        assert not any(p in low for p in printed), (name, data[name]['text'])


def test_same_document_compares_clean_with_no_verification_status(tmp_path):
    a, b = _swb(tmp_path, 'a.pdf'), _swb(tmp_path, 'b.pdf')
    diffs, locations = wb.compare_waybills(a, b, selected=NAMES, profile=PROFILE)
    assert diffs == [] and locations == []
    assert wb.REFERENCE_NEEDS_REVIEW == []            # status itu hanya milik pembaca label


def test_changed_vessel_is_marked_only_inside_its_value_cell(tmp_path):
    a = _swb(tmp_path, 'a.pdf')
    b = _swb(tmp_path, 'b.pdf', replace={'MERATUS KARIMUN': 'MERATUS BATAM'})
    diffs, locations = wb.compare_waybills(a, b, selected=NAMES, profile=PROFILE)
    assert [d.field for d in diffs] == ['Vessel']
    import pymupdf as fitz
    with fitz.open(a) as doc:
        W, H = doc[0].rect.width, doc[0].rect.height
    x0, y0, x1, y1 = wb.MERATUS_SWB_CELLS['Vessel'][0][1:]
    for side in locations[0]:
        for hit in side['hits']:
            r = hit['rect']
            cx, cy = (r.x0 + r.x1) / 2 / W, (r.y0 + r.y1) / 2 / H
            assert x0 <= cx <= x1 and y0 <= cy <= y1, (cx, cy)


def test_letter_that_mentions_meratus_is_still_a_flexible_reference(tmp_path):
    values = {'Waybill Number': 'JKT26104490', 'Shipper': 'PT. BRIDGESTONE TIRE INDONESIA',
              'Consignee': 'BRIDGESTONE TYRES (P.N.G) PTY. LTD.', 'Vessel': 'MERATUS KARIMUN',
              'Port of Loading': 'JAKARTA, INDONESIA', 'Port of Discharge': 'LAE, PAPUA NEW GUINEA'}
    for layout in ('narrative', 'table'):
        letter = tmp_path / ('letter_%s.pdf' % layout)
        ref_letters.write_letter(letter, values, layout)
        assert fr.detect_flexible_pdf(str(letter), NAMES) is True
        data = fr.extract_flexible(str(letter), NAMES)
        assert data['Vessel']['text'] == 'MERATUS KARIMUN' and data['Port of Discharge']['valid']

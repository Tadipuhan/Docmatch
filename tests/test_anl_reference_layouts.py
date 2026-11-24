"""Rujukan berlayout berbeda (surat naratif / tabel) dibandingkan pada NILAI field yang sama."""
import re
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pdf_shim  # noqa: E402
pdf_shim.install()
import samples  # noqa: E402
import ref_letters  # noqa: E402
import waybill_rules as wb  # noqa: E402
import flexible_reference as fr  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
LAYOUTS = ['narrative', 'table']
FORMS = ['anl3', 'anl', 'cnc']
SEMANTIC = ['Container & Seal', 'Weight & Measurement', 'Place & Date of Issue', 'Number of Original Waybills']


def _letter_values(exam):
    """Nilai surat DITULIS BERBEDA dari formulir tetapi bermakna sama."""
    wm = exam['Weight & Measurement']['semantic_text'].split()
    gross, measurement = float(wm[0]), float(wm[2])
    containers = re.findall(r'([A-Z]{4}\d{7})\s+SEAL\s+(\S+)', exam['Container & Seal']['text'])
    day = exam['Place & Date of Issue']['text']
    m = re.match(r'(\S+)\s+(\d+)\s+([A-Z]{3})\s+(\d{4})', day)
    values = {
        'Shipper': exam['Shipper']['text'], 'Consignee': exam['Consignee']['text'],
        'Voyage Number': exam['Voyage Number']['text'], 'Waybill Number': exam['Waybill Number']['text'],
        'Vessel': exam['Vessel']['text'], 'Port of Loading': exam['Port of Loading']['text'],
        'Port of Discharge': exam['Port of Discharge']['text'],
        'Final Place of Delivery': exam['Final Place of Delivery']['text'],
        'Cargo Description': exam['Cargo Description']['text'],
        'Number of Original Waybills': '0',
        'Weight & Measurement': '{:,.3f} KGS / {:,.3f} CBM'.format(gross, measurement),
        'Container & Seal': '; '.join('{} / SEAL-{}'.format(c, s) for c, s in containers),
        'Place & Date of Issue': '{} / {} {} {}'.format(m.group(1), m.group(2), m.group(3), m.group(4)),
    }
    return values


def _prepare(key, layout, tmp_path):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    exam = wb.extract(path, None, 'waybill_anl')
    values = _letter_values(exam)
    letter = tmp_path / ('%s_%s.pdf' % (key, layout))
    ref_letters.write_letter(letter, values, layout)
    return str(letter), path, values


def _compare(letter, path, fields):
    return wb.compare_waybills(letter, path, selected=list(fields), profile='waybill_anl')


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('key', FORMS)
def test_same_values_different_layout_produce_no_differences(key, layout, tmp_path):
    letter, path, values = _prepare(key, layout, tmp_path)
    diffs, _ = _compare(letter, path, values)
    assert [(d.field, d.reference_text[:40], d.examined_text[:40]) for d in diffs] == []
    assert wb.REFERENCE_NEEDS_REVIEW == []


@pytest.mark.parametrize('layout', LAYOUTS)
def test_changed_values_are_reported_only_for_that_field(layout, tmp_path):
    letter_path, path, values = _prepare('anl3', layout, tmp_path)
    mutations = {
        'Port of Discharge': 'SYDNEY, AUSTRALIA',
        'Weight & Measurement': '24,209.469 KGS / 215.386 CBM',          # selisih 0,001
        'Container & Seal': 'CAAU8541905 / SEAL-M2856222; ECMU5593288 / SEAL-M2853517; TXGU4183166 / SEAL-X999',
        'Place & Date of Issue': 'JAKARTA / 22 OCT 2026',
        'Number of Original Waybills': '3',
        'Voyage Number': '0SQ5AX',
    }
    for field, new_value in mutations.items():
        changed = dict(values, **{field: new_value})
        letter = tmp_path / ('mut_%s_%s.pdf' % (layout, re.sub(r'\W', '', field)))
        ref_letters.write_letter(letter, changed, layout)
        diffs, _ = _compare(str(letter), path, changed)
        assert [d.field for d in diffs] == [field], (field, [(d.field, d.reference_text, d.examined_text) for d in diffs])


@pytest.mark.parametrize('layout', LAYOUTS)
def test_value_boxes_follow_only_the_changed_words(layout, tmp_path):
    letter_path, path, values = _prepare('anl3', layout, tmp_path)
    changed = dict(values, **{'Port of Discharge': 'SYDNEY, AUSTRALIA'})
    letter = tmp_path / 'box.pdf'
    ref_letters.write_letter(letter, changed, layout)
    diffs, locations = _compare(str(letter), path, changed)
    assert [d.field for d in diffs] == ['Port of Discharge']
    ref_hits, exam_hits = locations[0]
    # 'FREMANTLE,' <-> 'SYDNEY,' berubah; 'AUSTRALIA' sama pada kedua sisi: tidak ditandai.
    assert len(ref_hits['hits']) == 1 and len(exam_hits['hits']) == 1
    import pymupdf as fitz
    with fitz.open(path) as doc:
        W, H = doc[0].rect.width, doc[0].rect.height
    r = exam_hits['hits'][0]['rect']
    assert .474 <= (r.x0 + r.x1) / 2 / W <= .728 and .316 <= (r.y0 + r.y1) / 2 / H <= .337


def test_two_reference_layouts_extract_identical_values(tmp_path):
    """Layout A (label di atas nilai) dan B (label | nilai) menghasilkan nilai yang sama."""
    letter_a, path, values = _prepare('anl3', 'narrative', tmp_path)
    letter_b, _, _ = _prepare('anl3', 'table', tmp_path)
    a = fr.extract_flexible(letter_a, list(values), word_level=True)   # jalur ANL
    b = fr.extract_flexible(letter_b, list(values), word_level=True)
    for name in values:
        assert a[name]['valid'] and b[name]['valid'], name
        assert ''.join(a[name]['text'].split()) == ''.join(b[name]['text'].split()) == ''.join(values[name].split()), name


@pytest.mark.parametrize('fixture', ['ANL_CNC_CMA_A_Surat_Naratif.pdf', 'ANL_CNC_CMA_B_Tabel_Konfirmasi.pdf'])
def test_provided_synthetic_letters_against_real_anl_form(fixture):
    """Surat uji sintetis (13 dari 19 field) vs formulir ANL nyata: hanya selisih yang sah."""
    path = samples.sample('anl3')
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    selected = [n for n, _ in wb.FIELDS if n != 'Additional Clauses']
    diffs, _ = wb.compare_waybills(str(FIXTURES / fixture), path, selected=selected, profile='waybill_anl')
    reported = {d.field for d in diffs}
    # Port of Loading sama di kedua dokumen: dulu dilaporkan BERBEDA karena caption ikut terbaca.
    assert 'Port of Loading' not in reported
    assert reported == {'Shipper', 'Consignee', 'Notify Party', 'Voyage Number', 'Waybill Number', 'Vessel',
                        'Port of Discharge', 'Final Place of Delivery', 'Container & Seal',
                        'Cargo Description', 'Weight & Measurement', 'Place & Date of Issue'}
    assert set(wb.REFERENCE_NEEDS_REVIEW) == {'Pre-Carriage', 'Place of Receipt', 'Freight To Be Paid At',
                                               'Number of Original Waybills', 'No & Kind of Packages'}
    shown = {d.field: d.examined_text for d in diffs}
    assert shown['Voyage Number'] == '0SQ5AN'              # tanpa caption "VOYAGE NUMBER"
    assert shown['Weight & Measurement'] == '24209.468 10830 215.386'


@pytest.mark.parametrize('fixture', ['ANL_CNC_CMA_A_Surat_Naratif.pdf', 'ANL_CNC_CMA_B_Tabel_Konfirmasi.pdf'])
def test_provided_letters_are_flexible_references_with_13_valid_labels(fixture):
    names = [n for n, _ in wb.FIELDS]
    path = str(FIXTURES / fixture)
    assert fr.detect_flexible_pdf(path, names)
    for word_level in (False, True):
        data = fr.extract_flexible(path, names, word_level=word_level)
        assert sum(bool(data[f]['valid']) for f in names) == 13
        assert ''.join(data['Container & Seal']['text'].split()) == 'TCLU1234567/SEAL-ANL001'

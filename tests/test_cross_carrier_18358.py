"""Independent reference carrier extraction + cross-profile correspondence."""
from pathlib import Path
import sys
import pytest
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import waybill_rules as wb
from cross_carrier import (detect_reference_profile, reference_field_map,
                           measurement_signature, split_compound_record)
from reference_note_format import address_reference_values, structured_reference_values

SAMPLES = {
    'waybill_one': 'ONEYJKTG94494400_draft_20261109183141.pdf',
    'waybill_maersk': 'SWB_26B97CL1 (FINAL).pdf',
    'waybill_meratus': 'MERATUS_JKT26104490 SWB_with_TnC.pdf',
    'waybill_msc': 'MSC_SWB_26BX8ZA1 (DRAFT).pdf',
}


def _sample(profile):
    path = Path('/mnt/data') / SAMPLES[profile]
    if not path.is_file():
        pytest.skip('PDF carrier fixture is not shipped with source')
    return path


@pytest.mark.parametrize('profile', tuple(SAMPLES))
def test_detects_each_supported_sample_without_filename(profile):
    assert detect_reference_profile(_sample(profile)) == profile


def test_surat_is_not_mistaken_for_an_official_meratus_swb():
    path = Path('/mnt/data/ANL_CNC_CMA_A_Surat_Naratif.pdf')
    if not path.is_file():
        pytest.skip('letter sample absent')
    assert detect_reference_profile(path) == 'flexible'


def test_strict_field_correspondence_and_unmatched_fields():
    mp = reference_field_map({'Main - Container & Seal', 'Final Place of Delivery', 'Final Destination'},
                             {'Container & Seal', 'Place of Delivery', 'Port of Discharge'})
    assert mp['Main - Container & Seal'] == 'Container & Seal'
    assert mp['Final Place of Delivery'] == 'Place of Delivery'
    assert 'Final Destination' not in mp


def test_one_reference_meratus_exam_own_value_rectangles():
    ref = _sample('waybill_one')
    exam = _sample('waybill_meratus')
    fields = {'Shipper', 'Waybill Number', 'Port of Loading'}
    diffs, marks = wb.compare_waybills(ref, exam, fields,
                                      profile='waybill_meratus', reference_profile='auto')
    assert {d.field for d in diffs} == {'Shipper', 'Waybill Number'}
    assert wb.REFERENCE_NEEDS_REVIEW == []
    assert wb.REFERENCE_EXTRACTION_DIAGNOSTICS['reference_profile'] == 'waybill_one'
    assert len(marks) == len(diffs)
    # Word rectangles from both PDFs must be within their respective pages.
    with fitz.open(ref) as a, fitz.open(exam) as b:
        for a_side, b_side in marks:
            assert a_side['hits'] and b_side['hits']
            for hit in a_side['hits']:
                assert a[hit['page']].rect.intersects(hit['rect'])
            for hit in b_side['hits']:
                assert b[hit['page']].rect.intersects(hit['rect'])


def test_reverse_profile_resolves_vessel_voyage():
    ref = _sample('waybill_meratus')
    exam = _sample('waybill_one')
    diffs, _ = wb.compare_waybills(ref, exam, {'Vessel / Voyage'},
                                   profile='waybill_one', reference_profile='auto')
    assert len(diffs) == 1
    assert diffs[0].reference_text.startswith('MERATUS KARIMUN /')
    assert 'GI090E' in diffs[0].reference_text
    assert wb.REFERENCE_NEEDS_REVIEW == []


def test_split_one_vessel_for_separate_examined_fields():
    ref = _sample('waybill_one')
    exam = _sample('waybill_meratus')
    diffs, _ = wb.compare_waybills(ref, exam, {'Vessel', 'Voyage Number'},
                                   profile='waybill_meratus', reference_profile='auto')
    assert {d.field for d in diffs} == {'Vessel', 'Voyage Number'}
    assert {d.field: d.reference_text for d in diffs} == {
        'Vessel': 'NAGOYA TOWER', 'Voyage Number': '033N'}
    assert wb.REFERENCE_NEEDS_REVIEW == []


def test_unknown_fields_are_not_false_matches():
    ref = _sample('waybill_meratus')
    exam = _sample('waybill_one')
    diffs, _ = wb.compare_waybills(ref, exam, {'Attached List - Clauses'},
                                   profile='waybill_one', reference_profile='auto')
    assert diffs == []
    assert wb.REFERENCE_NEEDS_REVIEW == ['Attached List - Clauses']


def test_note_values_come_from_reference_profile_not_examined_profile():
    ref = _sample('waybill_one')
    source = wb.extract(ref, {'Shipper', 'Container & Seal'}, profile='waybill_one')
    assert source['Shipper']['words'] and source['Container & Seal']['words']
    shipper = address_reference_values(ref, 'waybill_one', {'Shipper'}, {'Shipper':'Shipper'})
    cargo = structured_reference_values(ref, 'waybill_one', {'Container & Seal'},
                                        {'Container & Seal':'Container & Seal'})
    assert 'BRIDGESTONE' in shipper['Shipper']
    assert '/' in cargo['Container & Seal']


def test_wrong_manual_profile_is_rejected():
    ref = _sample('waybill_one')
    exam = _sample('waybill_meratus')
    with pytest.raises(ValueError, match='tidak sesuai'):
        wb.compare_waybills(ref, exam, {'Shipper'}, profile='waybill_meratus',
                            reference_profile='waybill_msc')


def test_unit_alias_and_number_format_reconcile():
    assert measurement_signature('36,216.582 KGS / 284.086 CBM', 'Weight & Measurement') == (
        ('weight','36216.582','kgs'),('measurement','284.086','cbm'))
    assert split_compound_record({'text':'NAGOYA TOWER 033N','words':[1,2,3]},
                                 'Voyage Number')['text'] == '033N'
    assert not split_compound_record({'text':'SHIP WITHOUT VOYAGE','words':[1,2,3]},
                                    'Voyage Number')['valid']


def test_unknown_image_form_rejected_for_auto_reference(tmp_path):
    ref = tmp_path/'no_text.pdf'
    doc = fitz.open()
    doc.new_page()
    doc.save(ref)
    doc.close()
    exam = _sample('waybill_one')
    with pytest.raises(ValueError, match='tidak dapat dipastikan'):
        wb.compare_waybills(ref, exam, {'Shipper'}, profile='waybill_one',
                            reference_profile='auto')


def test_source_gui_and_build_register_cross_carrier_feature():
    docmatch = (ROOT/'docmatch.py').read_text(encoding='utf-8')
    build = (ROOT/'build_portable.bat').read_text(encoding='utf-8')
    assert 'reference_profile_combo' in docmatch
    assert "reference_profile=self.reference_profile_combo.currentData()" in docmatch
    assert 'cross_carrier.py' in build and '--hidden-import cross_carrier' in build

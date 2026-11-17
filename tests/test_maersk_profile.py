"""Regression tests using the two supplied Maersk sample documents."""
from pathlib import Path
import sys
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from waybill_rules import extract, compare_waybills, maersk_layout, profile_field_names

EXAMPLES = Path(__file__).resolve().parent / 'fixtures'


def test_maersk_fields_available():
    names=profile_field_names('waybill_maersk')
    assert {'Shipper','Waybill Number','Consignee','Notify Party','Vessel','Voyage Number','Gross Weight','Freight & Charges'} <= set(names)


def test_maersk_variants_when_examples_present():
    final=EXAMPLES/'maersk_final.pdf'
    draft=EXAMPLES/'maersk_draft.pdf'
    if not final.is_file() or not draft.is_file():
        import pytest
        pytest.skip('Contoh PDF tidak disertakan dalam ZIP agar data dokumen tidak ikut dibagikan')
    with fitz.open(final) as doc:assert maersk_layout(doc[0])=='final'
    with fitz.open(draft) as doc:assert maersk_layout(doc[0])=='draft'
    for file,expected_number,expected_vessel,expected_notify in (
        (final,'276284770','JOSEPHINE MAERSK','BRIDGESTONE CHILE'),
        (draft,'274164141','OEL VARUN','YUSEN LOGISTICS')):
        data=extract(file,profile='waybill_maersk')
        assert data['Waybill Number']['text']==expected_number
        assert data['Booking Number']['text']==expected_number
        assert data['Vessel']['text']==expected_vessel
        assert expected_notify in data['Notify Party']['text']
        assert 'CERTIFIED' not in data['Container & Seal']['text']
        diffs,_=compare_waybills(file,file,profile='waybill_maersk')
        assert not diffs

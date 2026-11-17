"""Regression checks for the ONE draft Sea Waybill/Bill of Lading preset."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waybill_rules import ONE_CELLS, ONE_FIELD_GROUPS, _profile_cells, profile_field_names, extract, compare_waybills
import pymupdf as fitz


def test_one_field_registry():
    assert _profile_cells('waybill_one') is ONE_CELLS
    assert len(profile_field_names('waybill_one')) == 27
    for fields in ONE_FIELD_GROUPS.values():
        assert set(fields).issubset(ONE_CELLS)
    for regions in ONE_CELLS.values():
        for page,x0,y0,x1,y1 in regions:
            assert page in (0,1)
            assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1


def test_one_native_text_and_self_compare(tmp_path):
    pdf=tmp_path/'one.pdf'
    with fitz.open() as doc:
        page=doc.new_page(width=595.44,height=841.68)
        page.insert_text((480,73),'ONEYJKTG1234567',fontsize=8)
        page.insert_text((345,73),'JKTG1234567',fontsize=8)
        page.insert_text((183,300),'JAKARTA, INDONESIA',fontsize=8)
        doc.new_page()
        doc.save(pdf)
    out=extract(str(pdf),profile='waybill_one')
    assert out['Waybill Number']['text']=='ONEYJKTG1234567'
    assert out['Booking Number']['text']=='JKTG1234567'
    assert out['Port of Loading']['text']=='JAKARTA, INDONESIA'
    differences,_=compare_waybills(str(pdf),str(pdf),profile='waybill_one')
    assert not differences

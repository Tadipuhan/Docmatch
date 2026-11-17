"""Regression coverage for MSC B/L and MSC SWB with optional Rider Page.
Real client documents are not bundled with the source distribution.
Provide anonymized PDFs as tests/fixtures/msc_bl.pdf and msc_swb.pdf to run integration checks.
"""
import sys
from pathlib import Path
import pytest
import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waybill_rules import (extract, compare_waybills, profile_field_names,
                           _profile_cells, msc_layout, msc_cells_for_doc)

SAMPLES=Path(__file__).resolve().parent/'fixtures'


def test_msc_preset_fields():
    fields=profile_field_names('waybill_msc')
    assert len(fields)==len(set(fields))>=24
    assert {'Waybill Number','Document Type','Shipper','Consignee','Notify Party',
            'Vessel / Voyage','Booking Number','Port of Loading','Port of Discharge',
            'Container & Seal','Quantity','Cargo Description','Invoice Number',
            'Gross Weight','Gross Measurement','Rider - Container Details'} <= set(fields)
    assert set(fields)==set(_profile_cells('waybill_msc'))


def test_msc_variants_with_optional_fixtures():
    cases=(('msc_bl.pdf','front','MEDUKU761202','BILL OF LADING','MSC DIEGO - FH633R','EBKG18462516','2026ATDP014','557'),
           ('msc_swb.pdf','rider','MEDUKU991874','SEA WAYBILL','MSC VIGOUR III - HU645R','EBKG19106955','26BX8ZA1','1743'))
    if any(not (SAMPLES/name).is_file() for name,*_ in cases):
        pytest.skip('Letakkan sampel MSC anonim di tests/fixtures untuk uji PDF nyata')
    for name,layout,number,kind,vessel,booking,invoice,quantity in cases:
        file=SAMPLES/name
        with fitz.open(file) as doc:
            assert msc_layout(doc)==layout
            assert msc_cells_for_doc(doc)
        fields=extract(str(file),profile='waybill_msc')
        assert fields['Waybill Number']['text']==number
        assert fields['Document Type']['text']==kind
        assert fields['Vessel / Voyage']['text']==vessel
        assert fields['Booking Number']['text']==booking
        assert fields['Invoice Number']['text']==invoice
        assert fields['Quantity']['text']==quantity
        assert fields['Port of Loading']['text']=='JAKARTA, INDONESIA'
        assert fields['Gross Weight']['text'] and fields['Gross Measurement']['text']
        assert bool(fields['Rider - Container Details']['text']) == (layout=='rider')
        differences,locations=compare_waybills(str(file),str(file),profile='waybill_msc')
        assert not differences and not locations


def test_msc_cross_comparison_with_optional_fixtures():
    bl,swb=SAMPLES/'msc_bl.pdf',SAMPLES/'msc_swb.pdf'
    if not bl.is_file() or not swb.is_file():
        pytest.skip('PDF contoh tidak dibundel')
    differences,marks=compare_waybills(str(bl),str(swb),profile='waybill_msc')
    assert len(differences)==len(marks)
    assert any(d.field=='Waybill Number' for d in differences)

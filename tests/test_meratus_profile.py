"""Regression checks for Meratus BL and Way Bill variants.

Real PDFs are intentionally not bundled. Put anonymized samples under
`tests/fixtures/meratus_bl.pdf` and `tests/fixtures/meratus_swb.pdf` to run
integration checks locally. The source-code metadata tests always run.
"""
import sys
from pathlib import Path

import pytest
import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waybill_rules import (extract, compare_waybills, meratus_layout,
                           meratus_cells_for_page, profile_field_names,
                           _profile_cells)

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_meratus_profile_fields():
    names = profile_field_names('waybill_meratus')
    assert len(names) == len(set(names)) >= 24
    assert {'Waybill Number', 'Shipper', 'Consignee', 'Notify Party',
            'Vessel', 'Voyage Number', 'Port of Loading', 'Port of Discharge',
            'Container & Seal', 'Quantity', 'Cargo Description',
            'Gross Weight', 'Gross Measurement'} <= set(names)
    assert len(_profile_cells('waybill_meratus')) == len(names)


def test_meratus_variants_when_fixtures_available():
    bl, swb = FIXTURES/'meratus_bl.pdf', FIXTURES/'meratus_swb.pdf'
    if not bl.is_file() or not swb.is_file():
        pytest.skip('Tambahkan contoh PDF anonim ke tests/fixtures untuk integration test')
    for file, layout, number, vessel, notify, destination, quantity in (
        (bl, 'bl', 'JKTCB25013311', 'MERATUS KARIMUN', 'SAME AS CONSIGNEE', 'DILI, EAST TIMOR', '904 PIECES'),
        (swb, 'swb', 'JKT26104490', 'MERATUS KARIMUN', 'BRIDGESTONE TYRES', 'LAE, PAPUA NEW GUINEA', '549 PIECES'),
    ):
        with fitz.open(file) as doc:
            assert meratus_layout(doc[0]) == layout
            assert meratus_cells_for_page(doc[0])
        data=extract(str(file),profile='waybill_meratus')
        assert data['Waybill Number']['text'] == number
        assert data['Vessel']['text'] == vessel
        assert notify in data['Notify Party']['text']
        assert data['Port of Discharge']['text'] == destination
        assert data['Quantity']['text'] == quantity
        assert data['Container & Seal']['text']
        assert data['Gross Weight']['text']
        for field in ('Shipper','Consignee','Cargo Description'):
            assert 'DRAFT' not in data[field]['text']
        differences,_ = compare_waybills(str(file),str(file),profile='waybill_meratus')
        assert not differences


def test_meratus_cross_document_comparison_when_fixtures_available():
    bl, swb = FIXTURES/'meratus_bl.pdf', FIXTURES/'meratus_swb.pdf'
    if not bl.is_file() or not swb.is_file():
        pytest.skip('PDF contoh tidak dibundel')
    differences, marks = compare_waybills(str(bl),str(swb),profile='waybill_meratus')
    assert differences and len(differences) == len(marks)
    assert any(d.field == 'Waybill Number' for d in differences)

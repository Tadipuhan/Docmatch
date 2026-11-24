"""Regression tests for mixed-layout GSL comparison (no carrier PDF needed)."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flexible_reference import detect_flexible_pdf, extract_flexible
from waybill_rules import GSL_CELLS,compare_waybills

FIXTURE=ROOT/'tests'/'fixtures'/'GSL_Test_Surat_A_Rujukan.pdf'
FIXTURE_B=ROOT/'tests'/'fixtures'/'GSL_Test_Surat_B_Pembanding.pdf'

@pytest.mark.skipif(not FIXTURE.exists(),reason='synthetic sample PDF not bundled')
def test_flexible_reference_all_26_fields():
    assert detect_flexible_pdf(FIXTURE)
    values=extract_flexible(FIXTURE,GSL_CELLS)
    assert len(values)==26
    assert all(v['valid'] for v in values.values())
    assert values['Waybill Number']['text']=='GOSUJKT8132504'
    assert values['Attached List - CONT & SEAL']['text'].startswith('2 X 40 HC')

@pytest.mark.skipif(not FIXTURE.exists(),reason='synthetic sample PDF not bundled')
def test_flexible_self_comparison_has_no_differences():
    diffs, marks=compare_waybills(FIXTURE,FIXTURE,profile='waybill_gsl')
    assert diffs==[] and marks==[]

@pytest.mark.skipif(not FIXTURE_B.exists(),reason='synthetic sample PDF not bundled')
def test_flexible_cross_layout_comparison_identifies_changed_fields():
    a=FIXTURE
    b=FIXTURE_B
    diffs,_=compare_waybills(a,b,profile='waybill_gsl')
    changed={d.field for d in diffs}
    assert len(changed)==14,changed
    assert 'Shipper' not in changed
    assert 'Waybill Number' in changed

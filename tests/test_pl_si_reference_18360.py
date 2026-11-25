"""DocMatch v1.8.36.0: independent PL+SI PDF reference regression checks."""
from pathlib import Path
import copy
import sys
import pytest
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pl_si_reference import (extract_pl_si, merge_pdf, verify_pdf,
                             ReferenceReadError, equivalent, additional_claims)
import waybill_rules as wb

SI=Path('/mnt/data/SI 26YA1A.pdf')
PL=Path('/mnt/data/PL 26YA1A.pdf')
SWB=Path('/mnt/data/SWB 26YA1A.pdf')
FIELDS={'Booking Number','Shipper','Consignee','Notify Party',
        'Port of Loading','Port of Discharge','Vessel / Voyage',
        'Container & Seal','Quantity','Cargo Description',
        'Gross Weight','Gross Measurement'}


@pytest.fixture
def case(tmp_path):
    if not all(p.is_file() for p in (SI,PL,SWB)):
        pytest.skip('Real 26YA1A PDFs are not distributed with source')
    records,meta=extract_pl_si(SI,PL)
    combined=tmp_path/'reference.pdf'
    offset=merge_pdf(SI,PL,combined)
    return records,meta,combined,offset


def test_requires_pdfs_and_rejects_missing_files():
    with pytest.raises(ReferenceReadError,match='PDF'):
        verify_pdf('not-a-pdf.docx','PL')
    with pytest.raises(ReferenceReadError,match='tidak ditemukan'):
        verify_pdf('/tmp/nonexistent-pl-si.pdf','SI')


def test_input_files_are_valid_native_text_pdf(case):
    records,meta,combined,offset=case
    assert offset==1
    with fitz.open(combined) as doc:
        assert len(doc)==2
        assert 'SHIPPING INSTRUCTION' in ' '.join(doc[0].get_text().split())
        assert 'PACKING LIST' in doc[1].get_text()


def test_si_party_addresses_are_complete_without_column_bleeding(case):
    records,*_=case
    assert records['Shipper']['text'].startswith('PT. BRIDGESTONE TIRE INDONESIA\n')
    assert 'Tax ID : 001.000.118.8-092.000' in records['Shipper']['text']
    assert 'SBS TIRE FRONTIER' not in records['Shipper']['text']
    assert 'jrep_tire_import.tsg.bsj@bridgestone.com' in records['Consignee']['text']
    assert 'NAGOYA TOWER' not in records['Notify Party']['text']
    assert 'ATTN. MR. SUZUKI/ MS. MIYAKE' in records['Notify Party']['text']


def test_si_booking_ports_carrier_cargo_quantities(case):
    records,*_=case
    assert records['Booking Number']['text']=='JKTG86701300'
    assert records['Port of Loading']['text']=='JAKARTA, INDONESIA'
    assert records['Port of Discharge']['text']=='TOKYO, JAPAN'
    assert records['Vessel / Voyage']['text']=='NAGOYA TOWER 033N'
    assert records['Quantity']['text']=='1,210 PIECES'
    assert records['Net Weight']['text']=='17,388.650 Kgs'
    assert records['Gross Weight']['text']=='17,388.650 Kgs'
    assert records['Gross Measurement']['text']=='65.6100 M3'
    assert records['HS Code']['text']=='4011.80-010'


def test_pl_fields_take_priority_and_date_is_metadata_not_issue_date(case):
    records,meta,*_=case
    assert records['Invoice Number']['text']=='26YA1A'
    assert records['Container & Seal']['text']=='CAJU5672554 / ID54061AB'
    assert records['PL Date']['text']=='October 24, 2026'
    assert meta['pl_date']=='October 24, 2026'
    assert not meta['conflicting_invoice']
    assert 'Date of Issue' not in records


def test_each_pl_word_points_to_real_pl_page_in_merged_pdf(case):
    records,meta,merged,offset=case
    with fitz.open(merged) as doc:
        for key in ('Container & Seal','Invoice Number','PL Date'):
            rec=records[key]
            assert rec['valid'] and rec['source']=='PL'
            assert all(w['page']==offset and doc[offset].rect.contains(w['rect']) for w in rec['words'])
        for key in ('Shipper','Consignee','Booking Number'):
            rec=records[key]
            assert rec['source']=='SI'
            assert all(w['page']==0 for w in rec['words'])


def test_comparison_26ya1a_detects_real_shipper_punctuation_change(case):
    records,meta,merged,offset=case
    diffs,locations=wb.compare_waybills(merged,SWB,FIELDS,'waybill_one',reference_records=records)
    # SI prints CIAMPEL, while the SWB prints CIAMPEL. — this is an actual
    # punctuation discrepancy, not a false multiline-address finding.
    assert [d.field for d in diffs]==['Shipper']
    assert len(locations)==1
    assert wb.REFERENCE_NEEDS_REVIEW==[]
    assert wb.REFERENCE_EXTRACTION_DIAGNOSTICS['reference_profile']=='pl_si'


@pytest.mark.parametrize('field,changed',[
    ('Booking Number','JKTG86799999'),
    ('Container & Seal','CAJU5672554 / ID99999AB'),
    ('Quantity','1,211 PIECES'),
    ('Gross Weight','17,399.650 Kgs'),
    ('Gross Measurement','66.6100 M3'),
    ('Port of Loading','SEMARANG, INDONESIA'),
    ('Consignee','BRIDGESTONE CORPORATION\nWRONG ADDRESS'),
])
def test_changed_reference_values_generate_real_findings(case,field,changed):
    records,meta,merged,offset=case
    modified=copy.deepcopy(records)
    modified[field]['text']=changed
    diffs,locations=wb.compare_waybills(merged,SWB,{field},'waybill_one',reference_records=modified)
    assert len(diffs)==1
    assert diffs[0].field==field
    assert locations[0][0]['hits'] and locations[0][1]['hits']
    with fitz.open(merged) as a,fitz.open(SWB) as b:
        for hit in locations[0][0]['hits']:
            assert a[hit['page']].rect.intersects(hit['rect'])
        for hit in locations[0][1]['hits']:
            assert b[hit['page']].rect.intersects(hit['rect'])


def test_missing_or_unreliable_reference_needs_review(case):
    records,meta,merged,offset=case
    modified=copy.deepcopy(records)
    modified['Container & Seal']={'text':'','words':[], 'valid':False}
    diffs,_=wb.compare_waybills(merged,SWB,{'Container & Seal'},'waybill_one',reference_records=modified)
    assert not diffs
    assert 'Container & Seal' in wb.REFERENCE_NEEDS_REVIEW


def test_extra_invoice_hs_net_weight_match_real_swb(case):
    records,*_=case
    diffs,missing=additional_claims(SWB,'waybill_one',records)
    assert diffs==[] and missing==[]


def test_changed_pl_invoice_is_detected_as_additional_claim(case):
    records,*_=case
    modified=copy.deepcopy(records)
    modified['Invoice Number']['text']='26YA1B'
    diffs,missing=additional_claims(SWB,'waybill_one',modified)
    assert not missing
    assert [d.field for d,_ in diffs]==['Invoice Number']
    assert all(d[0]['hits'] and d[1]['hits'] for _,d in diffs)


def test_main_carrier_field_aliases_use_structured_pl_si_source(case):
    from cross_carrier import reference_field_map
    mp=reference_field_map({'Main - Container & Seal','Main - Cargo Description'},
                           {'Container & Seal','Cargo Description'})
    assert mp=={'Main - Container & Seal':'Container & Seal',
                'Main - Cargo Description':'Cargo Description'}
    assert equivalent('Main - Container & Seal','CAJU5672554 / ID54061AB',
                      'CAJU5672554 / ID54061AB')


def test_switching_inputs_does_not_modify_source_bytes(case,tmp_path):
    original=(SI.read_bytes(),PL.read_bytes())
    merge_pdf(SI,PL,tmp_path/'ephemeral.pdf')
    assert original==(SI.read_bytes(),PL.read_bytes())


def test_weight_units_cannot_be_silently_equated():
    assert equivalent('Gross Weight','17,388.650 KGS','17388.650 KG')
    assert not equivalent('Gross Weight','17,388.650 KGS','17388.650 TONNES')
    assert equivalent('Gross Measurement','65.6100 M3','65.610 CBM')


def test_pl_si_correction_notes_use_original_multiline_source_after_restore(case):
    """No reliance on ephemeral global comparison diagnostics after session reload."""
    import ast
    from types import SimpleNamespace
    from reference_note_format import address_reference_values, is_address_field
    from waybill_rules import profile_field_names
    import re
    records,meta,merged,offset=case
    src=(ROOT/'docmatch.py').read_text(encoding='utf8')
    tree=ast.parse(src)
    klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Window')
    fn=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='grouped_correction_notes')
    # Previous correction unit tests use this same isolated-method strategy to
    # avoid requiring Qt on a headless CI runner.
    namespace={'fitz':fitz,'swb_rules':wb,'is_address_field':is_address_field,
               'address_reference_values':address_reference_values,
               'profile_field_names':profile_field_names,'re':re}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                 str(ROOT/'docmatch.py'),'exec'),namespace)
    method=namespace['grouped_correction_notes']
    with fitz.open(merged) as doc:
        class Host:
            reference_mode='pl_si'
            waybill_mode=True
            ref_view=SimpleNamespace(pdf=doc)
            ref_path=merged
            rule_mode=SimpleNamespace(currentData=lambda:'waybill_one')
            _pl_si_records=records
            _reference_profile_actual='pl_si'
            exam_marks=[{'id':1,'page':0,'rect':fitz.Rect(25,70,180,90)},
                        {'id':2,'page':0,'rect':fitz.Rect(20,250,185,300)}]
            diffs=[SimpleNamespace(field='Shipper',kind='Perubahan',apply=True),
                   SimpleNamespace(field='Notify Party',kind='Perubahan',apply=True)]
            note_overrides={}
            def default_correction_note(self,n):return 'POTONGAN SELISIH'
        host=Host()
        wb.REFERENCE_EXTRACTION_DIAGNOSTICS={}
        notes={note['field']:note for note in method(host)}
        assert notes['Shipper']['text']==records['Shipper']['text']
        assert notes['Notify Party']['text']==records['Notify Party']['text']
        host.note_overrides[notes['Shipper']['key']]='MANUAL\n    Teks Pilihan'
        assert {note['field']:note['text'] for note in method(host)}['Shipper']=='MANUAL\n    Teks Pilihan'

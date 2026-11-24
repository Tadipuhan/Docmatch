"""Reference-side independent matching for every carrier preset (no UI needed)."""
import sys
from pathlib import Path
import pytest
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import waybill_rules as wb
from flexible_reference import detect_flexible_pdf, extract_flexible

CARRIERS={
 'waybill_one':'ONEYJKTG94494400_draft_20261109183141.pdf',
 'waybill_maersk':'SWB_26B97CL1 (FINAL).pdf',
 'waybill_meratus':'MERATURS_BL 25B43TL1 (DRAFT).pdf',
 'waybill_msc':'MSC_MEDUKU761202\xa0R1.pdf',
}


def make_letter(path, values):
    doc=fitz.open()
    page=doc.new_page(width=595,height=842)
    page.insert_text((48,65),'SURAT KONFIRMASI PENGIRIMAN BARANG',fontsize=14)
    page.insert_text((48,105),'Data rujukan:',fontsize=10)
    for i,(label,value) in enumerate(values.items()):
        y=160+i*54
        page.draw_rect(fitz.Rect(45,y-18,552,y+26),color=(.5,.5,.5),width=.6)
        page.insert_text((55,y),label,fontsize=10)
        page.insert_text((265,y),value,fontsize=10)
    doc.save(str(path))
    doc.close()


@pytest.mark.parametrize('profile,filename', CARRIERS.items())
def test_reference_letter_matches_carrier(profile,filename,tmp_path):
    # Samples are optional in a standalone distribution.
    sample=Path('/mnt/data')/filename
    if not sample.exists():pytest.skip('carrier fixture unavailable')
    fields={'Waybill Number','Port of Loading','Port of Discharge'}
    original=wb.extract(sample,fields,profile)
    assert all(original[f]['text'].strip() for f in fields)
    letter=tmp_path/'independent_reference.pdf'
    make_letter(letter,{field:original[field]['text'] for field in ('Waybill Number','Port of Loading','Port of Discharge')})
    assert detect_flexible_pdf(letter,fields)
    result=extract_flexible(letter,fields)
    assert all(result[f]['valid'] for f in fields)
    diffs,locs=wb.compare_waybills(letter,sample,fields,profile)
    assert diffs==[] and locs==[]
    assert wb.REFERENCE_NEEDS_REVIEW==[]


@pytest.mark.parametrize('profile,filename', CARRIERS.items())
def test_partial_reference_is_not_false_match(profile,filename,tmp_path):
    sample=Path('/mnt/data')/filename
    if not sample.exists():pytest.skip('carrier fixture unavailable')
    original=wb.extract(sample,{'Waybill Number','Port of Loading'},profile)
    letter=tmp_path/'partial.pdf'
    make_letter(letter,{'Waybill Number':original['Waybill Number']['text'],
                        'Port of Loading':original['Port of Loading']['text']})
    fields={'Waybill Number','Port of Loading','Port of Discharge'}
    diffs,_=wb.compare_waybills(letter,sample,fields,profile)
    assert not diffs
    assert wb.REFERENCE_NEEDS_REVIEW==['Port of Discharge']


def test_changed_value_reported_even_with_different_layout(tmp_path):
    sample=Path('/mnt/data')/CARRIERS['waybill_one']
    if not sample.exists():pytest.skip('carrier fixture unavailable')
    letter=tmp_path/'changed.pdf'
    make_letter(letter,{'B/L No.':'ONEYJKTG94494400',
                        'Port of Loading':'JAKARTA, INDONESIA',
                        'Port of Discharge':'BUSAN, KOREA'})
    fields={'Waybill Number','Port of Loading','Port of Discharge'}
    diffs,_=wb.compare_waybills(letter,sample,fields,'waybill_one')
    assert [d.field for d in diffs]==['Port of Discharge']
    assert diffs[0].kind=='Perubahan'


def test_inline_reference_with_single_field_is_supported(tmp_path):
    letter=tmp_path/'surat_satu_field.pdf'
    doc=fitz.open()
    page=doc.new_page()
    page.insert_text((50,70),'Surat instruksi pengiriman',fontsize=14)
    page.insert_text((50,140),'B/L No.: MEDUKU761202',fontsize=11)
    doc.save(letter);doc.close()
    assert detect_flexible_pdf(letter,{'Waybill Number','Port of Loading'})
    values=extract_flexible(letter,{'Waybill Number','Port of Loading'})
    assert values['Waybill Number']['valid']
    assert values['Waybill Number']['text']=='MEDUKU761202'
    assert not values['Port of Loading']['valid']

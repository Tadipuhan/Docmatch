"""Formatting-only regression for cargo, seal and weight correction notes."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import sys

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference_note_format import (structured_reference_values, is_structured_field,
                                   _verbatim_structured_rows, _suspect_cross_column)
from correction_note_layout import note_box_layout, wrap_note


def _free_letter(path):
    with fitz.open() as doc:
        page=doc.new_page(width=595,height=842)
        page.insert_text((45,54),'SURAT KONFIRMASI DATA / VERIFIKASI WAYBILL',fontsize=12)
        page.insert_text((48,88),'Container & Seal',fontsize=10)
        page.insert_text((48,105),'CAAU8790019',fontname='cour',fontsize=9)
        page.insert_text((157,105),' / ID26934AA',fontname='cour',fontsize=9)
        page.insert_text((48,119),'ONEU6061381  / ID26917AA',fontname='cour',fontsize=9)
        page.insert_text((48,173),'Cargo Description',fontsize=10)
        page.insert_text((48,189),'BRIDGESTONE  BRAND  TIRES',fontname='cour',fontsize=9)
        page.insert_text((48,203),'HS CODE : 401110',fontname='cour',fontsize=9)
        page.insert_text((48,217),'FREIGHT  PREPAID',fontname='cour',fontsize=9)
        page.insert_text((48,278),'Weight & Measurement',fontsize=10)
        page.insert_text((48,296),'36,216.582  KGS / 284.086  CBM',fontname='cour',fontsize=9)
        page.insert_text((48,385),'Waybill Number',fontsize=10)
        page.insert_text((48,401),'ONEXYZ123456',fontname='cour',fontsize=9)
        doc.save(path)


def _grouped_method():
    tree=ast.parse((ROOT/'docmatch.py').read_text('utf8'))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Window')
    method=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='grouped_correction_notes')
    import re
    import waybill_rules as swb_rules
    from reference_note_format import address_reference_values, is_address_field
    env={'fitz':fitz,'re':re,'swb_rules':swb_rules,
         'address_reference_values':address_reference_values,'is_address_field':is_address_field,
         'structured_reference_values':structured_reference_values,'is_structured_field':is_structured_field}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(ROOT/'docmatch.py'),'exec'),env)
    return env['grouped_correction_notes']


def test_targets_cover_carrier_aliases_without_touching_addresses():
    for f in ('Container & Seal','Main - Container & Seal','Cargo Description',
              'Main - Cargo Description','Weight & Measurement',
              'Attached List - Weight & Measurement','Gross Weight','Gross Measurement'):
        assert is_structured_field(f)
    assert not is_structured_field('Shipper')
    assert not is_structured_field('Notify Party')
    assert not is_structured_field('Waybill Number')


def test_one_container_rows_rejoin_and_preserve_cargo_breaks():
    pdf=Path('/mnt/data/ONEYJKTGA3152700_draft_20261106130236.pdf')
    if not pdf.is_file():
        import pytest
        pytest.skip('ONE fixture not available')
    data=structured_reference_values(pdf,'waybill_one',
                                     ('Container & Seal','Cargo Description','Gross Weight','Gross Measurement'))
    rows=data['Container & Seal'].splitlines()
    assert len(rows)==4
    assert all('/ ID' in row and '  ' in row for row in rows)
    assert data['Cargo Description'].splitlines()[0]=="4X40' HQ S.T.C.:"
    assert 'HS CODE : 401110\nINVOICE NO: 26BX1UA1' in data['Cargo Description']
    assert data['Gross Weight']=='36216.582KGS'
    assert data['Gross Measurement']=='284.086CBM'


def test_free_layout_preserves_multiple_rows_spaces_and_units(tmp_path):
    p=tmp_path/'rujukan.pdf'
    _free_letter(p)
    fields=('Container & Seal','Cargo Description','Weight & Measurement')
    values=structured_reference_values(p,'waybill_one',fields)
    assert set(values)==set(fields)
    assert values['Container & Seal']=='CAAU8790019   / ID26934AA\nONEU6061381  / ID26917AA'
    assert values['Cargo Description']=='BRIDGESTONE  BRAND  TIRES\nHS CODE : 401110\nFREIGHT  PREPAID'
    assert values['Weight & Measurement']=='36,216.582  KGS / 284.086  CBM'
    assert 'ONEXYZ' not in '\n'.join(values.values())


def test_note_group_uses_complete_source_and_respects_user_edit(tmp_path):
    p=tmp_path/'rujukan.pdf';_free_letter(p)
    method=_grouped_method()
    with fitz.open(p) as ref:
        class Host:
            waybill_mode=True
            ref_view=SimpleNamespace(pdf=ref)
            ref_path=p
            rule_mode=SimpleNamespace(currentData=lambda:'waybill_one')
            exam_marks=[
                {'id':1,'page':0,'rect':fitz.Rect(80,100,200,120)},
                {'id':2,'page':0,'rect':fitz.Rect(80,120,200,145)},
                {'id':3,'page':0,'rect':fitz.Rect(80,195,200,225)},
                {'id':4,'page':0,'rect':fitz.Rect(80,300,200,320)},
            ]
            diffs=[SimpleNamespace(field=f,kind='Perubahan',apply=True)
                   for f in ('Container & Seal','Container & Seal',
                             'Cargo Description','Weight & Measurement')]
            note_overrides={}
            def default_correction_note(self,n):return f'DIFF FRAGMENT {n}'
        host=Host()
        result={v['field']:v for v in method(host)}
        assert 'CAAU8790019' in result['Container & Seal']['text']
        assert 'ONEU6061381' in result['Container & Seal']['text']
        assert 'DIFF FRAGMENT' not in result['Container & Seal']['text']
        assert result['Cargo Description']['text'].count('\n')==2
        assert result['Weight & Measurement']['text']=='36,216.582  KGS / 284.086  CBM'
        key=result['Container & Seal']['key']
        host.note_overrides[key]='Edited\nby user'
        assert {v['field']:v['text'] for v in method(host)}['Container & Seal']=='Edited\nby user'
        del host.note_overrides[key]
        host.note_overrides[2]='Manual item override'
        assert {v['field']:v['text'] for v in method(host)}['Container & Seal']!='CAAU8790019   / ID26934AA\nONEU6061381  / ID26917AA'


def test_reject_contaminated_container_and_watermarks():
    assert _suspect_cross_column('Container & Seal','ONEU1234567 INVOICE NO 1234')
    assert _suspect_cross_column('Container & Seal','MRSU4178091  TEL: +62-123456')
    assert _suspect_cross_column('Cargo Description','VERIFY COPY \n123 PACKAGES')
    assert not _suspect_cross_column('Cargo Description','INVOICE NO: 26BX1UA1\nFREIGHT PREPAID')
    assert not _suspect_cross_column('Container & Seal','CAAU8790019 / ID26934AA')


def test_pdf_note_layout_keeps_structured_format(tmp_path):
    original='CAAU8790019   / ID26934AA\nONEU6061381  / ID26917AA\nGROSS WEIGHT: 36,216.582 KGS'
    assert wrap_note(original,420)==original.split('\n')
    h, entries=note_box_layout([{'page':0,'text':original}],0,595,842)
    assert entries[0][1]==original.split('\n')
    # Real PDF note writer is tested by the unchanged v1.8.35.5 PDF export test.


def test_exported_pdf_really_contains_formatted_cargo_and_measurements(tmp_path):
    p = tmp_path/'rujukan.pdf'
    _free_letter(p)
    values = structured_reference_values(p, 'waybill_one',
                                         ('Container & Seal','Cargo Description','Weight & Measurement'))
    with fitz.open(p) as carrier:
        boxes = [fitz.Rect(48,90,250,135), fitz.Rect(48,182,300,235), fitz.Rect(48,290,360,310)]
        groups = []
        for i,(field,rect) in enumerate(zip(('Container & Seal','Cargo Description','Weight & Measurement'),boxes),1):
            groups.append({'page':0,'key':'group:0:'+field.casefold(),'field':field,
                           'numbers':[i],'text':values[field], 'anchor':rect,
                           'rectangles':[rect],'kinds':['Perubahan']})
        tree = ast.parse((ROOT/'docmatch.py').read_text('utf8'))
        cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Window')
        fn = next(n for n in cls.body if isinstance(n,ast.FunctionDef)
                  and n.name=='export_waybill_notes_pdf')
        from correction_markers import draw_number_marker,scan_ink_guard
        env={'fitz':fitz,'NOTE_MARGIN':310,'note_box_layout':note_box_layout,
             'draw_number_marker':draw_number_marker,'scan_ink_guard':scan_ink_guard}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                     str(ROOT/'docmatch.py'),'exec'), env)
        class Host:
            exam_view=SimpleNamespace(pdf=carrier)
            exam_marks=[{'page':0,'id':i,'rect':rect,'kind':'Perubahan'}
                        for i,rect in enumerate(boxes,1)]
            diffs=[SimpleNamespace(apply=True) for _ in groups]
            waybill_mode=True
            rule_mode=SimpleNamespace(currentData=lambda:'waybill_one')
            def grouped_correction_notes(self,include_unchecked=False):return groups
        output=tmp_path/'Koreksi_test.pdf'
        env['export_waybill_notes_pdf'](Host(),output)
        with fitz.open(output) as doc:
            note=doc[0].get_text(clip=fitz.Rect(595,0,905,1200))
            assert 'CAAU8790019   / ID26934AA' in note
            assert 'ONEU6061381  / ID26917AA' in note
            assert 'BRIDGESTONE  BRAND  TIRES' in note
            assert '36,216.582  KGS / 284.086  CBM' in note


def test_msc_multi_container_list_and_units_when_sample_available():
    p=Path('/mnt/data/MSC_SWB_26BX8ZA1 (DRAFT).pdf')
    if not p.is_file():
        import pytest
        pytest.skip('MSC sample was not distributed in the source ZIP')
    data=structured_reference_values(p,'waybill_msc',
                                     {'Container & Seal','Cargo Description','Gross Weight','Gross Measurement'})
    seals=data['Container & Seal']
    for number in ('TCNU1627080','MEDU7226158','MSGU5483324'):
        assert number in seals
    assert seals.count('Seal Number:')==3
    assert '25,126.640' in data['Gross Weight']
    assert '214.367' in data['Gross Measurement']
    assert 'BRIDGESTONE/FIRESTONE BRAND TIRES' in data['Cargo Description']


def test_meratus_container_and_weight_without_label_spill_when_sample_available():
    p=Path('/mnt/data/MERATUS_JKT26104490 SWB_with_TnC.pdf')
    if not p.is_file():
        import pytest
        pytest.skip('Meratus sample was not distributed in the source ZIP')
    data=structured_reference_values(p,'waybill_meratus',
                                     {'Container & Seal','Cargo Description','Gross Weight','Gross Measurement'})
    assert data['Container & Seal'].startswith('MRTU9647507/J344673/40 HC')
    assert '549 PIECES' in data['Cargo Description']
    assert data['Gross Weight']=='11,092.239 KGS'
    assert data['Gross Measurement']=='73.841 CBM'

"""Address correction notes retain source capitals, encoded spaces, and newlines."""
from __future__ import annotations
import ast
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import waybill_rules as swb_rules
from reference_note_format import address_reference_values, is_address_field
from correction_note_layout import wrap_note, note_box_layout


def _one_sample(path):
    d = fitz.open()
    page = d.new_page(width=800, height=1000)
    entries = {
        'Shipper': (90, ['Pt.  BridgeStone  TIRE INDONESIA',
                         'Kawasan  Industri  SuryaCipta,',
                         'Jl.  Surya Utama KAV. 8-13,']),
        'Consignee': (180, ['BRIDGESTONE  International  Ltd.',
                           'No.  12/4  New City,']),
        'Notify Party': (254, ['Ocean  Logistics (SEA)  Co., Ltd.',
                              'Attn:  Mr.  John  Doe']),
    }
    for _, (start, lines) in entries.items():
        for i, line in enumerate(lines):
            page.insert_text((50, start + i * 13), line, fontname='cour', fontsize=10)
    d.save(path)
    d.close()
    return {k: '\n'.join(lines) for k, (_, lines) in entries.items()}


def _free_reference(path):
    d = fitz.open()
    page = d.new_page(width=595, height=842)
    page.insert_text((55, 60), 'SURAT KONFIRMASI DATA', fontsize=12)
    data = [
        (90, 'Shipper', ['Pt.  BridgeStone  Tire Indonesia', 'Jl.  Anggrek  No.  3']),
        (172, 'Consignee', ['BRIDGESTONE  Company  Ltd.', 'South  East   Asia']),
        (250, 'Notify Party', ['MaIn  Freight (SEA)  Co.', 'Attn:  Mr.  Ahmad']),
        (330, 'Waybill Number', ['ONETEST123']),
    ]
    for y, label, lines in data:
        page.insert_text((55, y), label, fontsize=10)
        for i, line in enumerate(lines):
            page.insert_text((55, y + 17 + 13 * i), line, fontsize=10, fontname='cour')
    d.save(path)
    d.close()
    return {label: '\n'.join(lines) for _, label, lines in data}


def _grouped_method():
    tree = ast.parse((ROOT / 'docmatch.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'grouped_correction_notes')
    env = {'fitz':fitz, 're':re, 'swb_rules':swb_rules,
           'address_reference_values':address_reference_values,
           'is_address_field':is_address_field}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                 str(ROOT / 'docmatch.py'), 'exec'), env)
    return env['grouped_correction_notes']


def test_carrier_preserves_complete_addresses_exactly(tmp_path):
    path = tmp_path / 'one.pdf'
    expected = _one_sample(path)
    got = address_reference_values(path, 'waybill_one', expected.keys())
    assert got == expected
    assert '  ' in got['Shipper']
    assert got['Shipper'].count('\n') == 2


def test_flexible_reference_preserves_address_but_not_next_field(tmp_path):
    path = tmp_path / 'ref.pdf'
    expected = _free_reference(path)
    got = address_reference_values(path, 'waybill_one', {'Shipper','Consignee','Notify Party'})
    assert got == {k:expected[k] for k in ('Shipper','Consignee','Notify Party')}
    assert 'ONETEST123' not in got['Notify Party']


def test_notes_use_full_source_not_diff_and_keep_manual_overrides(tmp_path):
    path = tmp_path / 'one.pdf'
    expected = _one_sample(path)
    method = _grouped_method()
    with fitz.open(path) as ref:
        class Host:
            waybill_mode = True
            ref_view = SimpleNamespace(pdf=ref)
            ref_path = path
            rule_mode = SimpleNamespace(currentData=lambda: 'waybill_one')
            exam_marks = [
                {'id':1,'page':0,'rect':fitz.Rect(50,77,150,95)},
                {'id':2,'page':0,'rect':fitz.Rect(50,90,150,108)},
                {'id':3,'page':0,'rect':fitz.Rect(50,163,150,181)},
                {'id':4,'page':0,'rect':fitz.Rect(50,239,150,257)},
            ]
            diffs = [SimpleNamespace(field=f,kind='Perubahan',apply=True)
                     for f in ('Shipper','Shipper','Consignee','Notify Party')]
            note_overrides = {}
            def default_correction_note(self,n):
                return 'POTONGAN REVISI'

        host = Host()
        groups = method(host)
        by_field = {g['field']:g for g in groups}
        for field, text in expected.items():
            assert by_field[field]['text'] == text
        key = by_field['Shipper']['key']
        host.note_overrides[key] = 'User  Edit\nBaris Kedua'
        assert {g['field']:g['text'] for g in method(host)}['Shipper'] == 'User  Edit\nBaris Kedua'
        del host.note_overrides[key]
        host.note_overrides[1] = 'Manual  #01'
        assert {g['field']:g['text'] for g in method(host)}['Shipper'] != expected['Shipper']


def test_pdf_note_wrap_keeps_spaces_and_manual_line_breaks():
    source = 'Pt.  BridgeStone  TIRE INDONESIA\nJl.  Surya  Utama   8-13,'
    assert wrap_note(source, 400) == source.split('\n')
    too_long = 'A   B   C   D   E   F '*12
    wrapped = wrap_note(too_long, 120)
    assert ''.join(wrapped) == too_long
    assert len(wrapped) > 2
    _, entries = note_box_layout([{'page':0, 'text':source}], 0, 595, 842)
    assert entries[0][1] == source.split('\n')


def test_export_pdf_note_retains_source_text_spacing(tmp_path):
    """Check the *real PDF writer*, not only the correction text in memory."""
    path = tmp_path / 'carrier.pdf'
    values = _one_sample(path)
    with fitz.open(path) as carrier:
        rect = fitz.Rect(50, 77, 290, 108)
        groups = [{'page':0,'key':'group:0:shipper','field':'Shipper',
                   'numbers':[1], 'text':values['Shipper'],
                   'anchor':rect,'rectangles':[rect], 'kinds':['Perubahan']}]
        tree = ast.parse((ROOT/'docmatch.py').read_text(encoding='utf8'))
        cls = next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Window')
        method = next(x for x in cls.body if isinstance(x,ast.FunctionDef)
                      and x.name=='export_waybill_notes_pdf')
        from correction_markers import draw_number_marker, scan_ink_guard
        env = {'fitz':fitz,'NOTE_MARGIN':310,'note_box_layout':note_box_layout,
               'draw_number_marker':draw_number_marker,'scan_ink_guard':scan_ink_guard}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),
                     str(ROOT/'docmatch.py'), 'exec'),env)

        class Host:
            exam_view = SimpleNamespace(pdf=carrier)
            exam_marks = [{'page':0,'id':1,'rect':rect,'kind':'Perubahan'}]
            diffs = [SimpleNamespace(apply=True)]
            waybill_mode = True
            rule_mode = SimpleNamespace(currentData=lambda:'waybill_one')
            def grouped_correction_notes(self,include_unchecked=False):return groups
        target = tmp_path/'output.pdf'
        env['export_waybill_notes_pdf'](Host(),target)
        with fitz.open(target) as exported:
            # Original PDF is unchanged, and the margin contains the note.
            assert len(exported)==1
            note = exported[0].get_text(clip=fitz.Rect(810,40,1110,260))
            assert 'Pt.  BridgeStone  TIRE INDONESIA' in note
            assert 'Kawasan  Industri  SuryaCipta,' in note
            assert 'Jl.  Surya Utama KAV. 8-13,' in note

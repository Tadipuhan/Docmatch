"""Smoke-test the actual PDF correction writer without Qt or external samples."""
from __future__ import annotations
import ast
import sys
from pathlib import Path
from types import SimpleNamespace
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from correction_note_layout import note_box_layout, NOTE_MARGIN
from correction_markers import draw_number_marker, scan_ink_guard


def _writer():
    tree = ast.parse((ROOT / 'docmatch.py').read_text(encoding='utf-8'))
    window = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    method = next(n for n in window.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'export_waybill_notes_pdf')
    globals_for_writer = {'fitz': fitz, 'NOTE_MARGIN': NOTE_MARGIN,
                          'note_box_layout': note_box_layout,
                          'draw_number_marker': draw_number_marker, 'scan_ink_guard': scan_ink_guard}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                 'docmatch_writer.py', 'exec'), globals_for_writer)
    return globals_for_writer['export_waybill_notes_pdf']


def test_notes_export_matches_edit_value_and_does_not_change_source(tmp_path):
    source = fitz.open()
    source.new_page(width=590, height=842).insert_text((50, 90), 'WAYBILL: ORIGINAL123', fontsize=13)
    first = source[0].get_text()
    selected = [False]
    updated = {'text': 'NOMOR BARU 456789'}
    rect = fitz.Rect(48, 74, 231, 98)

    class Context:
        exam_view = SimpleNamespace(pdf=source)
        diffs = [SimpleNamespace(apply=False)]
        exam_marks = [{'id': 1, 'page': 0, 'rect': rect, 'kind': 'Perubahan'}]
        waybill_mode = True
        rule_mode = SimpleNamespace(currentData=lambda: 'waybill_one')

        def grouped_correction_notes(self, include_unchecked=False):
            if not include_unchecked and not selected[0]:
                return []
            return [{'page': 0, 'key': 'group:0:waybill number', 'field': 'Waybill Number',
                     'numbers': [1], 'text': updated['text'], 'anchor': rect,
                     'rectangles': [rect]}]

    context = Context()
    export = _writer()
    full = tmp_path / 'all_notes.pdf'
    export(context, full, include_unchecked=True, allow_empty=True)
    with fitz.open(full) as annotated:
        text = annotated[0].get_text()
        assert 'NOMOR BARU 456789' in text
        assert annotated[0].rect.width == 900
        assert 'CATATAN KOREKSI' in text
        assert '#01' in text
    assert source[0].get_text() == first

    omitted = tmp_path / 'no_selected.pdf'
    export(context, omitted, include_unchecked=False, allow_empty=True)
    with fitz.open(omitted) as annotated:
        assert 'NOMOR BARU 456789' not in annotated[0].get_text()
    selected[0] = True
    context.diffs[0].apply = True
    updated['text'] = 'DIEDIT LANGSUNG DARI TAB KETIGA'
    approved = tmp_path / 'selected.pdf'
    export(context, approved)
    with fitz.open(approved) as annotated:
        assert 'DIEDIT LANGSUNG DARI TAB KETIGA' in annotated[0].get_text()
    source.close()

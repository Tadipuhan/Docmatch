"""No-connector, numbered marker regression tests."""
from pathlib import Path
import ast
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
from correction_markers import marker_label, marker_rect, draw_number_marker


def test_group_marker_numbering():
    assert marker_label([1]) == '#01'
    assert marker_label([3, 4]) == '#03,#04'
    assert marker_label([7, 8, 9]) == '#07-#09'


def test_marker_stays_inside_source_not_margin():
    for anchor in (fitz.Rect(50, 75, 200, 95),
                   fitz.Rect(0, 0, 42, 12),
                   fitz.Rect(560, 825, 590, 842)):
        rect = marker_rect(anchor, '#01', 590, 842)
        assert rect.x0 >= 0 and rect.y0 >= 0
        assert rect.x1 <= 590 and rect.y1 <= 842


def test_numbered_badge_written_as_vector_text(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=590, height=842)
    page.insert_text((80, 100), 'SHIPPER - EXAMPLE', fontsize=12)
    badge = draw_number_marker(page, fitz.Rect(75, 80, 240, 103), [1], 590, 842)
    path = tmp_path / 'badge.pdf'
    doc.save(path)
    doc.close()
    with fitz.open(path) as got:
        assert '#01' in got[0].get_text()
        assert got[0].get_text().find('SHIPPER') >= 0
        assert got[0].rect == fitz.Rect(0, 0, 590, 842)
    assert badge.x1 < 75


def test_pdf_export_has_no_connectors():
    tree = ast.parse((ROOT / 'docmatch.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    writer = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'export_waybill_notes_pdf')
    calls = [n for n in ast.walk(writer) if isinstance(n, ast.Call)]
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr == 'draw_line' for n in calls)
    assert any(isinstance(n.func, ast.Name) and n.func.id == 'draw_number_marker' for n in calls)


def test_marker_update_does_not_replace_original_note_editor():
    source = (ROOT / 'correction_preview.py').read_text(encoding='utf-8')
    assert 'CATATAN DAPAT DIEDIT LANGSUNG' in source
    assert 'QPlainTextEdit(self.canvas)' in source
    assert 'self.host.note_overrides[key] = new_text' in source
    assert 'Nilai Saat Ini (di Dokumen)' not in source
    assert 'Simpan Perubahan' not in source
    assert '_build_accordion' not in source

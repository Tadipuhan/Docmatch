"""Source-level regressions for the updated steps; Qt is tested on Windows."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _window():
    tree = ast.parse((ROOT / 'docmatch.py').read_text(encoding='utf-8'))
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')

def test_run_stays_in_second_step():
    run = next(n for n in _window().body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    calls = [c for c in ast.walk(run) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
             and c.func.attr == 'show_step']
    assert len(calls) == 2
    assert all(len(call.args) == 1 and isinstance(call.args[0], ast.Constant)
               and call.args[0].value == 1 for call in calls)

def test_third_step_owns_separate_review_page():
    source = (ROOT / 'docmatch.py').read_text(encoding='utf-8')
    assert 'self.workspace_pages.addWidget(split)' in source
    assert 'self.workspace_pages.addWidget(self.correction_preview)' in source
    assert 'self.workspace_pages.setCurrentIndex(1 if index == 2 else 0)' in source

def test_shared_pdf_note_geometry_used_by_writer_and_inline_preview():
    code = (ROOT / 'docmatch.py').read_text(encoding='utf-8')
    ui = (ROOT / 'correction_preview.py').read_text(encoding='utf-8')
    assert 'note_box_layout(notes, pno' in code
    assert 'note_box_layout(self.groups, self.page_index' in ui
    assert 'self.host.note_overrides[key] = new_text' in ui
    assert 'QPlainTextEdit(self.canvas)' in ui
    assert 'CATATAN DAPAT DIEDIT LANGSUNG' in ui


def test_previous_correction_notes_layout_is_unchanged():
    import hashlib
    root = ROOT.parent / 'DocMatch_v1.8.34'
    if root.is_dir():
        # Version 1.8.35.2 only changes the default PDF filename in export_current.
        # Verify the rest of the preview widget, including the inline editors,
        # is structurally identical to the original v1.8.34 implementation.
        def widget_without_export(path):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            cls = next(node for node in tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'CorrectionPreview')
            return [ast.dump(node, include_attributes=False) for node in cls.body
                    if not (isinstance(node, ast.FunctionDef) and node.name == 'export_current')]
        assert widget_without_export(ROOT / 'correction_preview.py') == \
               widget_without_export(root / 'correction_preview.py')
    ui = (ROOT / 'correction_preview.py').read_text(encoding='utf-8')
    assert 'self._note_changed(k, e)' in ui
    assert 'editor.setGeometry(x, y, w, h)' in ui
    assert 'self._dispose_editors()' in ui
    assert 'QSplitter(Qt.Orientation.Horizontal)' not in ui


def test_notes_export_remains_non_destructive():
    source = (ROOT / 'docmatch.py').read_text(encoding='utf-8')
    writer = source.split('    def export_waybill_notes_pdf(', 1)[1].split('    def export_waybill_docx(', 1)[0]
    assert 'page.show_pdf_page(' in writer
    assert 'page.apply_redactions(' not in writer
    assert 'source.saveIncr(' not in writer

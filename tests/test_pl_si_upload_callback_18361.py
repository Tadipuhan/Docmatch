"""Regression: Qt QPushButton.clicked(bool) must not replace PL/SI key."""
import ast
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / 'docmatch.py'


def _callback_node():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    modal = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'pick_reference')
    for node in ast.walk(modal):
        if isinstance(node, ast.FunctionDef) and node.name == 'choose_pdf':
            return node
    raise AssertionError('PL/SI choose_pdf callback missing')


class _Label:
    def __init__(self):
        self.text = ''

    def setText(self, text):
        self.text = text


def test_upload_buttons_store_each_file_using_the_correct_key():
    """Replicate button clicks with Qt's boolean first argument (False/True)."""
    node = _callback_node()
    for source_key, checked in (('pl', False), ('si', True)):
        name = {'pl': 'PL 26YA1A.pdf', 'si': 'SI 26YA1A.pdf'}[source_key]
        full_path = Path('/mnt/data') / name
        label = _Label()
        selected = {'pl': None, 'si': None}
        opened = []

        def get_open_file_name(dialog, title, directory, filter_text):
            opened.append((title, filter_text))
            return str(full_path), 'PDF (*.pdf)'

        namespace = {
            'QFileDialog': SimpleNamespace(getOpenFileName=get_open_file_name),
            'Path': Path,
            'dlg': object(),
            'selected': selected,
            'key': source_key,
            'lbl': label,
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                     str(SOURCE), 'exec'), namespace)
        namespace['choose_pdf'](checked)
        assert selected[source_key] == full_path
        assert label.text == full_path.name
        assert opened == [('Pilih ' + source_key.upper(), 'PDF (*.pdf)')]
        assert set(selected) == {'pl', 'si'}  # no stray selected[False] key


def test_cancel_keeps_previous_path_and_label():
    node = _callback_node()
    picked = Path('/mnt/data/PL 26YA1A.pdf')
    selected = {'pl': picked, 'si': None}
    label = _Label()
    label.setText(picked.name)
    namespace = {
        'QFileDialog': SimpleNamespace(getOpenFileName=lambda *_: ('', '')),
        'Path': Path, 'dlg': object(), 'selected': selected,
        'key': 'pl', 'lbl': label,
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(SOURCE), 'exec'), namespace)
    namespace['choose_pdf'](False)
    assert selected == {'pl': picked, 'si': None}
    assert label.text == picked.name

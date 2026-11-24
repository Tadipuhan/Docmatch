"""Regressions for squeezed header after SWB cross-carrier comparison.

These model the actual toolbar sizing method without requiring a Qt display;
interactive DPI/scaling still needs a Windows smoke test.
"""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'docmatch.py'


def _window_method(name):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Window')
    method = next(node for node in window.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {}
    code = compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec')
    exec(code, namespace)
    return namespace[name]


class _Hint:
    def __init__(self, h):
        self.h = h

    def height(self):
        return self.h


class _Layout:
    def __init__(self, height):
        self.height = height
        self.invalidations = 0

    def invalidate(self):
        self.invalidations += 1

    def activate(self):
        return True

    def sizeHint(self):
        return _Hint(self.height)


class _Page:
    def __init__(self, height):
        self.height = height
        self.layout_obj = _Layout(height)

    def layout(self):
        return self.layout_obj

    def sizeHint(self):
        return _Hint(self.height)


class _Stack:
    def __init__(self, index, page):
        self.index = index
        self.page = page
        self.fixed_height = None

    def currentIndex(self):
        return self.index

    def currentWidget(self):
        return self.page

    def setFixedHeight(self, height):
        self.fixed_height = height


class _ReferenceProfileBar:
    def __init__(self, visible):
        self.visible = visible

    def isVisibleTo(self, ancestor):
        return self.visible


class _Host:
    def __init__(self, index, height, reference_visible):
        self.wizard_stack = _Stack(index, _Page(height))
        self.reference_profile_bar = _ReferenceProfileBar(reference_visible)


def test_header_no_longer_hard_capped_to_58_pixels():
    source = SOURCE.read_text(encoding='utf-8')
    assert 'self.wizard_stack.setMaximumHeight(58)' not in source
    assert 'self.wizard_stack.setSizePolicy(' in source
    assert 'QSizePolicy.Policy.Fixed' in source


def test_two_row_swb_header_has_safe_minimum_height():
    resize = _window_method('_sync_wizard_toolbar_height')
    host = _Host(index=1, height=73, reference_visible=True)
    resize(host)
    assert host.wizard_stack.fixed_height >= 86
    assert host.wizard_stack.page.layout_obj.invalidations == 1


def test_large_font_or_dpi_header_grows_instead_of_clipping():
    resize = _window_method('_sync_wizard_toolbar_height')
    host = _Host(index=1, height=124, reference_visible=True)
    resize(host)
    assert host.wizard_stack.fixed_height >= 130


def test_single_row_stays_compact():
    resize = _window_method('_sync_wizard_toolbar_height')
    host = _Host(index=0, height=44, reference_visible=False)
    resize(host)
    assert 48 <= host.wizard_stack.fixed_height < 86


def test_step_navigation_and_mode_changes_recalculate_height():
    source = SOURCE.read_text(encoding='utf-8')
    assert 'def show_step(self,index):' in source
    show_step = source.split('    def show_step(self,index):', 1)[1].split('    def reset_comparison(', 1)[0]
    mode_change = source.split('    def mode_changed(self,*args):', 1)[1].split('    def choose_waybill(', 1)[0]
    assert 'self._sync_wizard_toolbar_height()' in show_step
    assert 'self._sync_wizard_toolbar_height()' in mode_change
    assert 'self.wizard_stack.setVisible(index != 2)' in show_step

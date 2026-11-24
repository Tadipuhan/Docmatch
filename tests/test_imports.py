"""Semua modul harus bisa DIIMPOR (PyMuPDF/PySide6 diganti stub kosong).

Menangkap kesalahan tingkat modul (NameError, impor hilang, nama dihapus) yang lolos
dari py_compile. Ini bukan pengganti uji GUI sungguhan.
"""
import importlib
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        cls = type(name, (), {'__init__': lambda self, *a, **k: None,
                              '__getattr__': lambda self, n: (lambda *a, **k: None)})
        setattr(self, name, cls)
        return cls


def _install_stubs():
    for name in ('pymupdf', 'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'docx',
                 'docx.shared', 'docx.enum', 'docx.enum.text', 'docx.enum.table', 'docx.oxml', 'docx.oxml.ns'):
        try:
            importlib.import_module(name)
        except ImportError:
            sys.modules[name] = _StubModule(name)


def test_all_modules_import():
    _install_stubs()
    names = ['textnorm', 'region_guard', 'gsl_glyph_table', 'gsl_layout', 'gsl_font_recovery',
             'gsl_ocr', 'region_ocr_recovery', 'rules', 'flexible_reference', 'anl_semantics', 'anl_form',
             'waybill_rules']
    for name in names:
        importlib.import_module(name)


def test_waybill_rules_public_names():
    _install_stubs()
    import waybill_rules as w
    for attr in ('FIELDS', 'GSL_CELLS', 'GSL_PAGE1_FIELDS', 'GSL_SKIPPED_FIELDS', 'GSL_DIAGNOSTICS',
                 'WaybillDifference', 'compare_waybills', 'profile_field_names', 'audit_gsl_page1', '_profile_cells'):
        assert hasattr(w, attr), attr
    names = [n for n, _ in w.FIELDS]
    assert 'Final Place of Delivery' in names and 'Shipper' in names
    assert len(w.GSL_PAGE1_FIELDS) == 20 and set(w.GSL_PAGE1_FIELDS) <= set(w.GSL_CELLS)
    assert w.profile_field_names('waybill_gsl') and w.profile_field_names('waybill_anl')


def test_gui_modules_import():
    _install_stubs()
    for name in ('editor', 'legacy_v01', 'hybrid_validation', 'docmatch'):
        importlib.import_module(name)

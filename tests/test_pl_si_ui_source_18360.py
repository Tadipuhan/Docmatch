"""Static UI and persistence contracts, runnable without Windows/Qt installed."""
from pathlib import Path
import ast

SOURCE=Path(__file__).resolve().parents[1]/'docmatch.py'
SRC=SOURCE.read_text(encoding='utf-8')
TREE=ast.parse(SRC)
WINDOW=next(node for node in TREE.body if isinstance(node,ast.ClassDef) and node.name=='Window')


def method(name):
    return next(node for node in WINDOW.body if isinstance(node,ast.FunctionDef) and node.name==name)


def test_reference_button_opens_type_selection_modal():
    assert 'self.ref_btn.clicked.connect(self.pick_reference)' in SRC
    modal=ast.get_source_segment(SRC,method('pick_reference'))
    assert 'QDialog' in modal and 'QRadioButton' in modal
    assert 'SWB — satu dokumen rujukan' in modal
    assert 'Packing List (PL) + Shipping Instruction (SI)' in modal
    assert "('pl','Packing List (PL)')" in modal
    assert "('si','Shipping Instruction (SI)')" in modal
    assert 'merge_pdf' in modal and 'extract_pl_si' in modal


def test_comparison_reuses_original_swb_engine_with_composite_records():
    run=ast.get_source_segment(SRC,method('run'))
    assert 'compare_waybills(' in run
    assert "reference_records=(self._pl_si_records if self.reference_mode=='pl_si' else None)" in run
    assert 'additional_claims(' in run
    assert 'self.show_step(1)' in run


def test_session_retains_both_pdf_fingerprints_and_source_mode():
    payload=ast.get_source_segment(SRC,method('_session_payload'))
    restore=ast.get_source_segment(SRC,method('_restore_session'))
    assert "'reference_mode':self.reference_mode" in payload
    assert "'packing_list':fingerprint(self.pl_path)" in payload
    assert 'fingerprint(pl)' in restore and 'merge_pdf(ref,pl,virtual_ref)' in restore


def test_composite_notes_use_reference_source_text():
    notes=ast.get_source_segment(SRC,method('grouped_correction_notes'))
    assert "self._pl_si_records[source]['text']" in notes
    assert 'self.note_overrides.get(group_key, default)' in notes


def test_autoportable_packaging_kept_unchanged():
    build=(SOURCE.parent/'build_portable.bat').read_text(encoding='utf-8')
    assert 'pack_portable.py' in build

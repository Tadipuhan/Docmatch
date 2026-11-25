"""Pure-source checks of the responsive PDF workspace regression.

The real PySide6 layout still requires a Windows GUI smoke test; these tests
make the intended minimum-width constraints explicit without importing Qt.
"""
from pathlib import Path
from ui_layout_state import responsive_split_widths

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'docmatch.py').read_text(encoding='utf-8')


def test_paper_title_and_navigation_use_distinct_rows():
    section=SOURCE.split('class Paper(QWidget):',1)[1].split('    def set_highlights',1)[0]
    assert "title_bar.addWidget(self.heading,1)" in section
    assert "title_bar.addWidget(self.toggle,0)" in section
    assert "lay.addLayout(title_bar)" in section
    assert "lay.addLayout(toolbar)" in section
    assert section.index('lay.addLayout(title_bar)') < section.index('lay.addLayout(toolbar)')
    assert "QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed" in section
    assert "toolbar.addStretch(1)" in section
    # Prevent the old single navigation row from containing the document heading.
    assert 'toolbar.addWidget(self.heading)' not in section


def test_two_pdfs_and_inspector_fit_typical_windows_widths():
    for window_width in (1024,1280,1366,1585,1920):
        # Two 8px outer margins and a 6px splitter handle.
        avail=window_width-22
        doc,panel=responsive_split_widths(avail,360,260,430,560)
        assert doc+panel==avail
        assert doc>=560
        assert panel>=260
        assert doc/2>=280


def test_file_buttons_cannot_force_main_window_wider():
    assert "chooser.setMinimumWidth(0)" in SOURCE
    assert "chooser.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)" in SOURCE
    assert "self.exam_btn.setToolTip(str(path))" in SOURCE
    assert "self.ref_btn.setToolTip(self.ref_view.heading.text())" not in SOURCE


def test_rebalance_splitter_after_loading_either_document():
    ref=SOURCE.split('    def pick_reference(',1)[1].split('    def pick(',1)[0]
    exam=SOURCE.split('    def pick(',1)[1].split('    def mode_changed(',1)[0]
    assert 'self._queue_workspace_fit()' in ref
    assert 'self._queue_workspace_fit()' in exam
    assert "panel_min=260" in SOURCE
    assert "documents_min=560" in SOURCE

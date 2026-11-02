"""Editable review copy: local-only rich text with visible change highlighting."""
from __future__ import annotations
import difflib
from pathlib import Path
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QTextEdit, QPushButton, QMessageBox)


def changed_indices(base: list[str], current: list[str]) -> set[int]:
    result=set()
    matcher=difflib.SequenceMatcher(None,base,current,autojunk=False)
    for op,a,b,c,d in matcher.get_opcodes():
        if op!='equal':result.update(range(c,d))
    return result


def save_annotated_docx(blocks: list[str], target: Path, original: list[str]):
    """New DOCX; mark changed paragraphs in yellow. Not a layout-preserving DOCX editor."""
    doc=Document()
    changed=changed_indices(original,blocks)
    for index,block in enumerate(blocks):
        paragraph=doc.add_paragraph()
        run=paragraph.add_run(block)
        if index in changed:run.font.highlight_color=WD_COLOR_INDEX.YELLOW
    doc.save(target)


class CorrectionEditor(QDialog):
    def __init__(self,text: str, initial: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle('DocMatch — Editor Manual Hasil Koreksi')
        self.resize(960,720)
        self.initial=list(initial)
        layout=QVBoxLayout(self)
        title=QLabel('Edit dokumen hasil koreksi secara langsung')
        title.setStyleSheet('font-size:18px;font-weight:700;color:#850D1C')
        layout.addWidget(title)
        note=QLabel('Stabilo kuning menandai paragraf yang berubah dari hasil koreksi otomatis saat editor dibuka. '
                    'Teks dapat diketik, dihapus, dan diganti. Simpan Perubahan sebelum ekspor.')
        note.setWordWrap(True);layout.addWidget(note)
        self.text=QTextEdit()
        self.text.setAcceptRichText(False)
        self.text.setPlainText(text)
        self.text.setStyleSheet('QTextEdit { background:white;color:#20232A;font:13px "Segoe UI";padding:18px;border:1px solid #CDD0D5; }')
        layout.addWidget(self.text,1)
        self.text.textChanged.connect(self.rehighlight)
        row=QHBoxLayout()
        self.counter=QLabel('');row.addWidget(self.counter);row.addStretch()
        reset=QPushButton('Kembalikan ke Koreksi Otomatis');reset.clicked.connect(self.reset)
        cancel=QPushButton('Batal');cancel.clicked.connect(self.reject)
        save=QPushButton('Simpan Perubahan');save.setStyleSheet('background:#850D1C;color:white;padding:10px;border-radius:5px')
        save.clicked.connect(self.accept)
        for btn in (reset,cancel,save):row.addWidget(btn)
        layout.addLayout(row)
        self.rehighlight()

    def content(self):return self.text.toPlainText()

    def reset(self):
        answer=QMessageBox.question(self,'Konfirmasi','Batalkan semua edit manual di editor ini?')
        if answer==QMessageBox.StandardButton.Yes:self.text.setPlainText('\n'.join(self.initial))

    def rehighlight(self):
        current=self.content().split('\n')
        changed=changed_indices(self.initial,current)
        self.counter.setText(f'{len(current)} paragraf/baris · {len(changed)} berubah secara manual')
        cursor=self.text.textCursor();position=cursor.position()
        self.text.blockSignals(True)
        block=self.text.document().firstBlock();i=0
        while block.isValid():
            fmt=QTextCharFormat()
            fmt.setBackground(QColor('#FFF0A8') if i in changed else QColor('white'))
            selection=QTextCursor(block)
            selection.select(QTextCursor.SelectionType.BlockUnderCursor)
            selection.mergeCharFormat(fmt)
            block=block.next();i+=1
        cursor.setPosition(min(position,len(self.content())))
        self.text.setTextCursor(cursor)
        self.text.blockSignals(False)

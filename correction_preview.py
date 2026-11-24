"""Integrated step-3 correction review for DocMatch.

Shows a single examined-document PDF with vector margin notes on the right,
using the same writer/geometry as the exported PDF. The notes are editable
in-place; source PDFs and comparison fields are never modified.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox,
    QScrollArea, QPlainTextEdit, QMessageBox, QFileDialog,
)

from correction_note_layout import note_box_layout, NOTE_MARGIN
from export_naming import correction_pdf_filename


class CorrectionPreview(QWidget):
    """The third navigation step, not a separate dialog window."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.pdf = None
        self.groups = []
        self.page_index = 0
        self.zoom = 1.0
        self.fit_mode = True
        self.editors = []
        self._file = host.work / 'review_notes_preview.pdf'
        self._pending_fit = False

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(6)
        title = QLabel('HASIL KOREKSI  /  CATATAN DAPAT DIEDIT LANGSUNG')
        title.setStyleSheet('font-weight:700;color:#850D1C')
        top.addWidget(title)
        top.addStretch(1)

        self.all_notes = QCheckBox('Tampilkan semua temuan')
        self.all_notes.setChecked(True)
        self.all_notes.setToolTip('Aktif: semua ketidaksesuaian yang memiliki penanda. '
                                  'Nonaktif: hanya temuan yang dicentang pada Tahap 1.')
        top.addWidget(self.all_notes)
        self.all_notes.toggled.connect(lambda _: self.refresh())

        self.previous = QPushButton('‹')
        self.next = QPushButton('›')
        self.counter = QLabel('0 / 0')
        self.zoom_out = QPushButton('−')
        self.zoom_in = QPushButton('+')
        self.fit_button = QPushButton('Lebar')
        for widget in (self.previous, self.counter, self.next,
                       self.zoom_out, self.zoom_in, self.fit_button):
            top.addWidget(widget)
        root.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setObjectName('correctionScroll')
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.scroll.setStyleSheet('QScrollArea{background:#E9EDF2;border:1px solid #D8DEE5;}')
        self.canvas = QLabel('Jalankan Bandingkan pada Langkah 2 untuk menampilkan hasil koreksi.')
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet('QLabel {background:white;color:#64748B;border:1px solid #CBD5E1;}')
        self.canvas.setMinimumSize(250, 330)
        self.scroll.setWidget(self.canvas)
        self.scroll.viewport().installEventFilter(self)
        root.addWidget(self.scroll, 1)

        bottom = QHBoxLayout()
        self.info = QLabel('Teks yang diketik disimpan dalam sesi dan digunakan saat ekspor.')
        self.info.setStyleSheet('color:#475569')
        bottom.addWidget(self.info, 1)
        self.apply_btn = QPushButton('Perbarui Preview')
        self.export_btn = QPushButton('Ekspor PDF Catatan…')
        self.export_btn.setStyleSheet('background:#850D1C;color:white;font-weight:700')
        bottom.addWidget(self.apply_btn)
        bottom.addWidget(self.export_btn)
        root.addLayout(bottom)

        self.previous.clicked.connect(lambda: self.goto(self.page_index - 1))
        self.next.clicked.connect(lambda: self.goto(self.page_index + 1))
        self.zoom_out.clicked.connect(lambda: self.set_zoom(self.zoom - .12))
        self.zoom_in.clicked.connect(lambda: self.set_zoom(self.zoom + .12))
        self.fit_button.clicked.connect(self.fit_width)
        self.apply_btn.clicked.connect(self.refresh)
        self.export_btn.clicked.connect(self.export_current)
        self._set_navigation(False)

    def _set_navigation(self, available):
        count = len(self.pdf) if available and self.pdf is not None else 0
        self.counter.setText(f'{self.page_index + 1} / {count}' if count else '0 / 0')
        self.previous.setEnabled(bool(count and self.page_index > 0))
        self.next.setEnabled(bool(count and self.page_index + 1 < count))
        self.zoom_out.setEnabled(bool(count))
        self.zoom_in.setEnabled(bool(count))
        self.fit_button.setEnabled(bool(count))
        self.apply_btn.setEnabled(bool(count))
        self.export_btn.setEnabled(bool(count and self.host.waybill_mode))

    def eventFilter(self, obj, event):
        if obj is self.scroll.viewport() and event.type() == QEvent.Type.Resize and self.fit_mode:
            if not self._pending_fit:
                self._pending_fit = True
                QTimer.singleShot(0, self._fit_after_resize)
        return super().eventFilter(obj, event)

    def _fit_after_resize(self):
        self._pending_fit = False
        if self.isVisible() and self.pdf is not None:
            self.fit_width()

    def _dispose_editors(self):
        for edit in self.editors:
            edit.blockSignals(True)
            edit.hide()
            edit.setParent(None)
            edit.deleteLater()
        self.editors = []

    def clear(self, message='Jalankan Bandingkan pada Langkah 2 untuk menampilkan hasil koreksi.'):
        self._dispose_editors()
        if self.pdf is not None:
            self.pdf.close()
            self.pdf = None
        self.groups = []
        self.page_index = 0
        self.canvas.setPixmap(QPixmap())
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(250, 330)
        self.canvas.setText(message)
        self.canvas.resize(300, 380)
        self._set_navigation(False)
        self.info.setText(message)

    def refresh(self):
        """Rebuild preview from the exact same PDF writer used by export.

        Calling this after edits also recalculates line wrapping and note-box
        heights, so long corrections remain fully visible in the PDF.
        """
        viewer = getattr(self.host, 'exam_view', None)
        if viewer is None or viewer.pdf is None or not getattr(self.host, 'has_compared', False):
            self.clear('Belum ada hasil perbandingan. Gunakan Langkah 2 lalu klik Bandingkan.')
            return
        old_page = self.page_index
        self._dispose_editors()  # textChanged already saved every keystroke
        if self.pdf is not None:
            self.pdf.close()
            self.pdf = None
        try:
            if self.host.waybill_mode:
                all_findings = self.all_notes.isChecked()
                self.host.export_waybill_notes_pdf(
                    self._file, include_unchecked=all_findings, allow_empty=True)
                self.groups = self.host.grouped_correction_notes(include_unchecked=all_findings)
            else:
                # General-document mode: one examined page, without Waybill notes.
                source = viewer.pdf
                with fitz.open() as output:
                    output.insert_pdf(source)
                    output.save(str(self._file), garbage=3, deflate=True)
                self.groups = []
            self.pdf = fitz.open(str(self._file))
        except Exception as exc:
            self.clear(f'Preview catatan tidak tersedia: {exc}')
            return
        self.page_index = min(max(old_page, 0), len(self.pdf) - 1)
        if self.fit_mode:
            self.fit_width()
        else:
            self.render()
        if self.host.waybill_mode:
            self.info.setText('Klik teks dalam kotak Catatan Koreksi untuk mengedit. '
                              'Perbarui Preview jika teks menjadi lebih panjang.')
        else:
            self.info.setText('Mode umum: preview satu dokumen; kotak koreksi inline hanya pada mode SWB.')

    def goto(self, index):
        if self.pdf is None or not (0 <= index < len(self.pdf)):
            return
        self.page_index = index
        if self.fit_mode:
            self.fit_width()
        else:
            self.render()

    def set_zoom(self, new_value):
        self.fit_mode = False
        self.zoom = max(.36, min(1.65, new_value))
        self.render()

    def fit_width(self):
        self.fit_mode = True
        if self.pdf is None:
            return
        width = max(1.0, float(self.pdf[self.page_index].rect.width))
        available = max(260, self.scroll.viewport().width() - 28)
        self.zoom = max(.36, min(1.65, available / width))
        self.render()

    def _note_changed(self, key, editor):
        # Preserve work immediately; no subsequent click on a Save button is required.
        new_text = editor.toPlainText()
        if self.host.note_overrides.get(key) != new_text:
            self.host.note_overrides[key] = new_text
            # Debounce autosave; avoid one audit record for every keystroke.
            if self.host.ref_path and self.host.exam_path:
                self.host.autosave_timer.start()

    def render(self):
        if self.pdf is None:
            return
        page = self.pdf[self.page_index]
        display_zoom = self.zoom
        render_scale = display_zoom * 2.0
        self._dispose_editors()
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale),
                                  colorspace=fitz.csRGB, alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride,
                           QImage.Format.Format_RGB888).copy()
            pm = QPixmap.fromImage(image)
            pm.setDevicePixelRatio(2.0)
            # Overlay editors assume PDF coordinates start at the canvas origin.
            # A centred pixmap on a min-height QLabel would shift every editor.
            self.canvas.setMinimumSize(1, 1)
            self.canvas.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.canvas.setPixmap(pm)
            self.canvas.resize(pm.deviceIndependentSize().toSize())
        except (RuntimeError, ValueError) as exc:
            self.clear(f'Gagal merender halaman: {exc}')
            return
        if self.host.waybill_mode:
            orig_width = float(self.host.exam_view.pdf[self.page_index].rect.width)
            orig_height = float(self.host.exam_view.pdf[self.page_index].rect.height)
            _, entries = note_box_layout(self.groups, self.page_index,
                                         orig_width, orig_height, NOTE_MARGIN)
            for group, _, rect in entries:
                key = group['key']
                editor = QPlainTextEdit(self.canvas)
                editor.setObjectName('inlineCorrection')
                editor.setPlainText(str(group['text']))
                editor.setToolTip(f'{group["field"]} — edit catatan, bukan teks PDF asli')
                editor.setStyleSheet('QPlainTextEdit { background:#FFF9F6; color:#850D1C; '
                                     'border:1px solid #BD8A91; font:italic 11px Segoe UI; '
                                     'padding:3px; } '
                                     'QPlainTextEdit:focus{border:2px solid #850D1C;}')
                x = round((rect.x0 + 4) * display_zoom)
                y = round((rect.y0 + 20) * display_zoom)
                w = max(80, round((rect.width - 8) * display_zoom))
                h = max(24, round((rect.height - 25) * display_zoom))
                editor.setGeometry(x, y, w, h)
                editor.textChanged.connect(lambda k=key, e=editor: self._note_changed(k, e))
                editor.show()
                self.editors.append(editor)
        self._set_navigation(True)

    def export_current(self):
        if self.pdf is None or not self.host.waybill_mode:
            return
        name, _ = QFileDialog.getSaveFileName(
            self, 'Ekspor PDF seperti preview', correction_pdf_filename(self.host.exam_path),
            'PDF (*.pdf)')
        if not name:
            return
        try:
            target = Path(name).with_suffix('.pdf')
            self.host.export_waybill_notes_pdf(
                target, include_unchecked=self.all_notes.isChecked(), allow_empty=True)
            QMessageBox.information(self, 'Ekspor berhasil',
                                    f'PDF berisi catatan terbaru telah disimpan:\n{target}')
        except Exception as exc:
            QMessageBox.critical(self, 'Ekspor gagal', str(exc))

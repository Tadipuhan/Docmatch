"""DocMatch offline MVP. Python 3.10+."""
from __future__ import annotations
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

from docx import Document
import fitz
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QSplitter, QCheckBox)

TOKEN = re.compile(r'\d+(?:[.,]\d+)*|\w+|[^\w\s]', re.UNICODE)

@dataclass
class Difference:
    kind: str
    reference_index: int | None
    examined_index: int | None
    reference_text: str
    examined_text: str
    detail: str
    apply: bool = True


def libreoffice_convert(path: Path, ext: str, outdir: Path) -> Path:
    executable = shutil.which('libreoffice') or shutil.which('soffice')
    if not executable:
        raise RuntimeError('LibreOffice tidak ditemukan. Instal LibreOffice untuk DOC dan konversi PDF.')
    profile = (outdir / 'lo_profile').as_uri()
    command = [executable, f'-env:UserInstallation={profile}', '--headless', '--convert-to', ext,
               '--outdir', str(outdir), str(path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    target = outdir / (path.stem + '.' + ext)
    if result.returncode != 0 or not target.exists():
        raise RuntimeError('Konversi gagal: ' + (result.stderr or result.stdout))
    return target


def read_blocks(path: Path, tempdir: Path):
    ext = path.suffix.lower()
    if ext == '.doc':
        path = libreoffice_convert(path, 'docx', tempdir)
        ext = '.docx'
    if ext == '.docx':
        doc = Document(path)
        # MVP: paragraphs in body only; tables/headers/footers are not yet inspected.
        return [p.text for p in doc.paragraphs if p.text.strip()], path
    if ext == '.pdf':
        with fitz.open(path) as pdf:
            blocks = []
            for page in pdf:
                for block in page.get_text('blocks'):
                    if len(block) > 4 and block[6] == 0:
                        text = ' '.join(block[4].split())
                        if text:
                            blocks.append(text)
        if not blocks:
            raise ValueError('PDF tidak memiliki teks yang dapat diekstrak (OCR belum didukung).')
        return blocks, path
    raise ValueError('Format harus DOCX, DOC, atau PDF.')


def details(ref: str, current: str) -> str:
    a, b = TOKEN.findall(ref), TOKEN.findall(current)
    changes = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes():
        if tag != 'equal':
            changes.append(f'{tag}: {" ".join(b[i:j])!r} → {" ".join(a[k:l])!r}')
    return '; '.join(changes)[:5000]


def compare(reference: list[str], examined: list[str]) -> list[Difference]:
    # Alignment uses fuzzy anchors for modified paragraphs, not only exact matches.
    def norm(s): return ' '.join(s.lower().split())
    matcher = difflib.SequenceMatcher(None, [norm(s) for s in examined],
                                      [norm(s) for s in reference], autojunk=False)
    output = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        old = examined[i1:i2]
        new = reference[j1:j2]
        # Pair likely replacements; unpaired paragraphs become insert/delete.
        for n in range(max(len(old), len(new))):
            x = old[n] if n < len(old) else ''
            y = new[n] if n < len(new) else ''
            kind = 'Perubahan' if x and y else ('Hilang' if y else 'Berlebih')
            output.append(Difference(kind, j1+n if y else None, i1+n if x else None,
                                     y, x, details(y, x) if x and y else kind))
    return output


def corrected_blocks(examined: list[str], differences: list[Difference]) -> list[str]:
    replacements = {d.examined_index: d.reference_text for d in differences
                    if d.apply and d.examined_index is not None}
    additions = {}
    for d in differences:
        if d.apply and d.examined_index is None and d.reference_index is not None:
            # Insert before next matched reference anchor when possible.
            later = [x.examined_index for x in differences if x.reference_index is not None
                     and x.reference_index > d.reference_index and x.examined_index is not None]
            position = min(later) if later else len(examined)
            additions.setdefault(position, []).append(d.reference_text)
    result = []
    for i in range(len(examined)+1):
        result.extend(additions.get(i, []))
        if i < len(examined):
            value = replacements.get(i, examined[i])
            if value:
                result.append(value)
    return result


def save_docx(blocks: list[str], destination: Path):
    doc = Document()
    for block in blocks:
        doc.add_paragraph(block)
    doc.save(destination)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('DocMatch v0.1 — Offline')
        self.resize(1200, 800)
        self.reference_path = None
        self.examined_path = None
        self.reference = []
        self.examined = []
        self.differences = []
        self.temp = tempfile.TemporaryDirectory(prefix='docmatch_')
        self.tmp_path = Path(self.temp.name)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        bar = QHBoxLayout()
        layout.addLayout(bar)
        for title, method in [('Pilih rujukan', self.choose_reference),
                              ('Pilih diperiksa', self.choose_examined),
                              ('Bandingkan', self.run_compare),
                              ('Ekspor DOCX', self.export_docx),
                              ('Ekspor PDF', self.export_pdf),
                              ('Laporan JSON', self.export_report)]:
            btn = QPushButton(title)
            btn.clicked.connect(method)
            bar.addWidget(btn)
        self.status = QLabel('Pilih dua dokumen untuk memulai. Semua proses lokal.')
        layout.addWidget(self.status)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.ref_view = QPlainTextEdit()
        self.ref_view.setReadOnly(True)
        self.exam_view = QPlainTextEdit()
        self.exam_view.setReadOnly(True)
        splitter.addWidget(self.ref_view)
        splitter.addWidget(self.exam_view)
        layout.addWidget(splitter, 3)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Terapkan', 'Jenis', 'Posisi', 'Diperiksa', 'Rujukan'])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 2)

    def choose_reference(self):
        self.reference_path = self.choose_file()
        if self.reference_path:
            self.status.setText('Rujukan: ' + str(self.reference_path))

    def choose_examined(self):
        self.examined_path = self.choose_file()
        if self.examined_path:
            self.status.setText('Diperiksa: ' + str(self.examined_path))

    def choose_file(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Pilih dokumen', '',
                                              'Dokumen (*.docx *.doc *.pdf)')
        return Path(name) if name else None

    def run_compare(self):
        if not self.reference_path or not self.examined_path:
            QMessageBox.warning(self, 'Dokumen belum lengkap', 'Pilih kedua dokumen.')
            return
        try:
            self.reference, _ = read_blocks(self.reference_path, self.tmp_path)
            self.examined, _ = read_blocks(self.examined_path, self.tmp_path)
            self.differences = compare(self.reference, self.examined)
            self.ref_view.setPlainText('\n\n'.join(self.reference))
            self.exam_view.setPlainText('\n\n'.join(self.examined))
            self.table.setRowCount(len(self.differences))
            for i, d in enumerate(self.differences):
                check = QCheckBox()
                check.setChecked(True)
                self.table.setCellWidget(i, 0, check)
                for col, value in enumerate([d.kind, str(d.examined_index + 1) if d.examined_index is not None else '—',
                                             d.examined_text, d.reference_text], 1):
                    item = QTableWidgetItem(value)
                    item.setToolTip(d.detail)
                    self.table.setItem(i, col, item)
            self.status.setText(f'{len(self.differences)} ketidaksesuaian terdeteksi (tingkat blok).')
        except Exception as e:
            QMessageBox.critical(self, 'Gagal membandingkan', str(e))

    def selected_diffs(self):
        for i, d in enumerate(self.differences):
            checkbox = self.table.cellWidget(i, 0)
            d.apply = bool(checkbox and checkbox.isChecked())
        return self.differences

    def export_docx(self):
        if not self.examined_path or not self.reference_path:
            return
        name, _ = QFileDialog.getSaveFileName(self, 'Simpan hasil', 'docmatch_hasil.docx', 'DOCX (*.docx)')
        if name:
            try:
                save_docx(corrected_blocks(self.examined, self.selected_diffs()), Path(name))
                QMessageBox.information(self, 'Berhasil', 'DOCX baru disimpan. Tata letak asli belum dipertahankan.')
            except Exception as e:
                QMessageBox.critical(self, 'Gagal ekspor', str(e))

    def export_pdf(self):
        if not self.examined_path or not self.reference_path:
            return
        name, _ = QFileDialog.getSaveFileName(self, 'Simpan PDF', 'docmatch_hasil.pdf', 'PDF (*.pdf)')
        if name:
            try:
                docx_path = self.tmp_path / 'docmatch_pdf_source.docx'
                save_docx(corrected_blocks(self.examined, self.selected_diffs()), docx_path)
                pdf_path = libreoffice_convert(docx_path, 'pdf', self.tmp_path)
                shutil.copyfile(pdf_path, name)
                QMessageBox.information(self, 'Berhasil', 'PDF hasil koreksi disimpan.')
            except Exception as e:
                QMessageBox.critical(self, 'Gagal ekspor', str(e))

    def export_report(self):
        if not self.examined_path or not self.reference_path:
            return
        name, _ = QFileDialog.getSaveFileName(self, 'Simpan laporan', 'docmatch_laporan.json', 'JSON (*.json)')
        if name:
            payload = {'reference': str(self.reference_path), 'examined': str(self.examined_path),
                       'differences': [asdict(d) for d in self.selected_diffs()]}
            Path(name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
            QMessageBox.information(self, 'Berhasil', 'Laporan disimpan.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())

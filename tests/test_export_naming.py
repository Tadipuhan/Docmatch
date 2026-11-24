"""Regresi khusus nama default ekspor PDF Catatan."""
from pathlib import Path
from export_naming import correction_pdf_filename


def test_pdf_catatan_uses_name_of_examined_document():
    assert correction_pdf_filename('ONE - Draft Waybill.pdf') == 'Koreksi_ONE - Draft Waybill.pdf'
    assert correction_pdf_filename(r'C:\Dokumen\ANL 2026 FINAL.PDF') == 'Koreksi_ANL 2026 FINAL.pdf'
    assert correction_pdf_filename(Path('/data/ONE.2026.final.pdf')) == 'Koreksi_ONE.2026.final.pdf'


def test_missing_document_name_uses_safe_fallback():
    assert correction_pdf_filename(None) == 'Koreksi_Dokumen_Diperiksa.pdf'


def test_every_note_export_entry_uses_one_naming_function():
    root=Path(__file__).resolve().parents[1]
    preview=(root/'correction_preview.py').read_text(encoding='utf-8')
    main=(root/'docmatch.py').read_text(encoding='utf-8')
    assert "correction_pdf_filename(self.host.exam_path)" in preview
    assert main.count('correction_pdf_filename(self.exam_path)') == 3
    assert 'Waybill_Hasil_Koreksi_Catatan.pdf' not in preview
    assert 'Waybill_Hasil_Koreksi_Catatan.pdf' not in main

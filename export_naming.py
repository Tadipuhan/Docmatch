"""Nama default hasil ekspor PDF Catatan DocMatch."""
from pathlib import PureWindowsPath


def correction_pdf_filename(examined_document):
    """Return Koreksi_<nama dokumen diperiksa tanpa ekstensi>.pdf.

    Only affects the suggested filename; the user can choose another name in
    the Save As dialog. PureWindowsPath also parses paths in cross-OS tests.
    """
    if not examined_document:
        return 'Koreksi_Dokumen_Diperiksa.pdf'
    stem = PureWindowsPath(str(examined_document)).stem
    if not stem or stem in {'.', '..'}:
        stem = 'Dokumen_Diperiksa'
    return f'Koreksi_{stem}.pdf'

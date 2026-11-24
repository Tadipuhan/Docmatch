"""Pembuat surat rujukan uji (naratif / tabel) dengan layout berbeda. Data sintetis.

PyMuPDF dipakai bila ada; jika tidak, reportlab (hanya untuk lingkungan audit).
"""
import textwrap


def _wrap(value, width):
    return textwrap.wrap(value, width=width, break_long_words=False, break_on_hyphens=False) or ['']


def write_letter(path, values, layout):
    """layout: 'narrative' (label lalu nilai di bawahnya) atau 'table' (label | nilai)."""
    if layout == 'narrative':
        title, sub = 'SURAT REFERENSI DATA PENGIRIMAN', 'Dokumen Rujukan A | Data: sintetis'
    else:
        title, sub = 'LEMBAR KONFIRMASI PARAMETER LOGISTIK', 'Dokumen Rujukan B | Data: sintetis'
    ops = [('title', 48, 60, title), ('text', 48, 76, sub)]
    y = 110
    if layout == 'table':
        ops += [('bold', 55, y, 'FIELD / PARAMETER'), ('bold', 265, y, 'NILAI / VALUE')]
        y += 18
    for label, value in values.items():
        lines = _wrap(value, 70 if layout == 'narrative' else 50)
        if layout == 'narrative':
            ops.append(('bold', 48, y, label))
            for i, line in enumerate(lines):
                ops.append(('text', 48, y + 12 + i * 10, line))
            y += 12 + len(lines) * 10 + 14
        else:
            ops.append(('text', 55, y, label))
            for i, line in enumerate(lines):
                ops.append(('text', 265, y + i * 10, line))
            y += max(1, len(lines)) * 10 + 12
    _render(path, ops)


def _render(path, ops):
    try:
        import pymupdf as fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        for kind, x, y, text in ops:
            font = 'hebo' if kind in ('title', 'bold') else 'helv'
            size = 14 if kind == 'title' else 8
            page.insert_text((x, y), text, fontsize=size, fontname=font)
        doc.save(str(path))
        doc.close()
        return
    except (ImportError, AttributeError, TypeError):
        pass
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=(595, 842))
    for kind, x, y, text in ops:
        c.setFont('Helvetica-Bold' if kind in ('title', 'bold') else 'Helvetica', 14 if kind == 'title' else 8)
        c.drawString(x, 842 - y, text)
    c.save()

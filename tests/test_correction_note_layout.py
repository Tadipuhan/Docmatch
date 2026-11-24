"""Regression tests for the shared PDF margin-note layout (no Qt needed)."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from correction_note_layout import note_box_layout, wrap_note

class CorrectionNoteLayoutTests(unittest.TestCase):
    def test_note_geometry_and_order(self):
        groups = [
            {'page': 0, 'field': 'Shipper', 'key': 'g:shipper', 'text': 'PT ABC\nJAKARTA'},
            {'page': 1, 'field': 'Container', 'key': 'g:container', 'text': 'ABC123'},
            {'page': 0, 'field': 'Notify Party', 'key': 'g:notify',
             'text': 'PT XYZ ' * 35},
        ]
        height, entries = note_box_layout(groups, 0, 590, 842)
        self.assertEqual([g['key'] for g, _, _ in entries], ['g:shipper', 'g:notify'])
        self.assertEqual(entries[0][2].x0, 604)
        self.assertGreater(entries[1][2].y0, entries[0][2].y1)
        self.assertGreaterEqual(height, 842)
        self.assertGreater(len(entries[1][1]), 3)

    def test_pdf_textbox_accepts_wrapped_note(self):
        text = 'KAWASAN INDUSTRI SURYACIPTA. KEL. KUTAMEKAR, KEC. CIAMPEL, ' * 2
        _, entries = note_box_layout([{'page':0,'field':'Shipper','text':text}], 0, 590, 842)
        _, lines, rect = entries[0]
        with fitz.open() as pdf:
            page = pdf.new_page(width=900, height=842)
            result = page.insert_textbox(
                fitz.Rect(rect.x0+6, rect.y0+21, rect.x1-6, rect.y1-5),
                '\n'.join(lines), fontname='heit', fontsize=9.5,
                lineheight=1.18, color=(.35,.06,.13))
            self.assertGreaterEqual(result, 0)

    def test_other_page_no_notes(self):
        height, entries = note_box_layout([{'page':0,'text':'ABC'}], 2, 590, 842)
        self.assertEqual(entries, [])
        self.assertEqual(height, 842)

if __name__ == '__main__':
    unittest.main()

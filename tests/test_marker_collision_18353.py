"""Regression: badge placement must not hide letters or adjacent fields."""
from pathlib import Path
import ast
import pymupdf as fitz
from correction_markers import (marker_rect, draw_number_marker,
                                scan_ink_guard, _intersects_with_clearance)

ROOT = Path(__file__).resolve().parents[1]


def _page():
    doc = fitz.open()
    page = doc.new_page(width=590, height=842)
    # Simulate dense adjacent table columns and an encroaching row label.
    page.insert_text((275, 152), 'PACKAGES', fontsize=10)
    page.insert_text((338, 152), '4X40 HQ', fontsize=10)
    page.insert_text((440, 152), 'S.T.C.:', fontsize=10)
    page.insert_text((440, 168), 'BRIDGESTONE TYRES WITH', fontsize=9)
    page.insert_text((440, 182), 'TUBES AND FLAPS', fontsize=9)
    page.insert_text((440, 198), 'HS CODE : 401110', fontsize=9)
    page.insert_text((440, 214), 'INVOICE NO : 26BX1UA1', fontsize=9)
    page.insert_text((275, 132), 'QUANTITY', fontsize=8)
    page.insert_text((440, 132), 'DESCRIPTION OF GOODS', fontsize=8)
    return doc, page


def _words(page):
    return [fitz.Rect(w[:4]) for w in page.get_text('words')]


def _no_overlap(a, other):
    return not _intersects_with_clearance(a, other, .7)


def test_marker_avoids_neighboring_words_and_highlights():
    doc, page = _page()
    words = _words(page)
    anchors = [fitz.Rect(321, 139, 374, 157),
               fitz.Rect(438, 140, 474, 158),
               fitz.Rect(439, 187, 550, 219)]
    already = []
    for n, anchor in zip(([4], [5,6,7,8,9,10], [11]), anchors):
        badge = draw_number_marker(page, anchor, n, 590, 842,
                                   text_boxes=words, occupied=already,
                                   protected=anchors)
        assert badge is not None
        assert all(_no_overlap(badge, w) for w in words)
        assert all(_no_overlap(badge, a) for a in anchors)
        assert badge.x0 >= 0 and badge.x1 <= 590
    for i in range(len(already)):
        for other in already[i+1:]:
            assert _no_overlap(already[i], other)
    doc.close()


def test_marker_at_left_edge_must_move_not_overprint():
    page_width, page_height = 170, 120
    anchor = fitz.Rect(0, 12, 58, 29)
    text = [fitz.Rect(58, 12, 155, 29), fitz.Rect(0, 30, 140, 45)]
    badge = marker_rect(anchor, '#04', page_width, page_height,
                        text_boxes=text, protected=[anchor])
    assert badge is not None
    assert all(_no_overlap(badge, r) for r in [anchor, *text])


def test_marker_never_occupies_text_if_no_room():
    anchor = fitz.Rect(1, 1, 40, 15)
    whole_page = fitz.Rect(0, 0, 45, 26)
    assert marker_rect(anchor, '#05-#10', 45, 26,
                       text_boxes=[whole_page]) is None


def test_source_scan_guard_keeps_number_off_rasterized_text():
    doc = fitz.open()
    page = doc.new_page(width=260, height=140)
    page.insert_text((80, 48), 'PRINTED TEXT ONLY', fontsize=14)
    # This verifies the grayscale ink guard independently of text extraction.
    checker = scan_ink_guard(page)
    assert checker is not None
    assert checker(fitz.Rect(80, 33, 210, 50)) is False
    assert checker(fitz.Rect(10, 85, 70, 100)) is True
    doc.close()


def test_writer_reuses_original_page_text_and_occupied_markers():
    src = (ROOT / 'docmatch.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    window = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Window')
    writer = next(n for n in window.body if isinstance(n, ast.FunctionDef) and
                  n.name == 'export_waybill_notes_pdf')
    code = ast.get_source_segment(src, writer) or ''
    assert "original.get_text('words')" in code
    assert 'occupied=placed_badges' in code
    assert 'protected=protected' in code
    assert 'scan_ink_guard(original)' in code

"""v1.8.35.4: stay close to highlights, never obscure printed evidence."""
from pathlib import Path
import ast
import pymupdf as fitz
from correction_markers import (marker_rect, draw_number_marker,
                                _rect_distance, _intersects_with_clearance,
                                MAX_BADGE_DISTANCE, BADGE_GAP)

ROOT = Path(__file__).resolve().parents[1]


def test_free_left_side_is_tight():
    anchor = fitz.Rect(120, 60, 166, 76)
    found = marker_rect(anchor, '#01-#03', 300, 160)
    assert found is not None
    assert 1.5 <= anchor.x0 - found.x1 <= 2.2
    assert found.y0 <= anchor.y1 and found.y1 >= anchor.y0


def test_blocked_left_chooses_adjacent_top_not_distant_whitespace():
    anchor = fitz.Rect(110, 64, 154, 80)
    # Block the whole left zone; top remains free.
    left_text = fitz.Rect(0, 38, 108.5, 110)
    found = marker_rect(anchor, '#04', 300, 190,
                        text_boxes=[left_text], protected=[anchor])
    assert found is not None
    assert found.y1 < anchor.y0
    assert _rect_distance(anchor, found) <= 3.0
    assert not _intersects_with_clearance(found, left_text, .7)


def test_can_shift_under_highlight_by_fine_steps_to_find_tiny_gap():
    anchor = fitz.Rect(85, 58, 124, 72)
    # Some words are below the field; restrict the free band to 12..15pt.
    protected = [anchor, fitz.Rect(0, 0, 78, 120),
                 fitz.Rect(132, 0, 230, 120),
                 fitz.Rect(78, 35, 132, 56),
                 fitz.Rect(78, 88, 132, 120)]
    found = marker_rect(anchor, '#05-#10', 240, 130, protected=protected)
    assert found is not None
    assert 0 < _rect_distance(anchor, found) <= MAX_BADGE_DISTANCE
    assert all(not _intersects_with_clearance(found, p, .9) for p in protected)


def test_dense_page_does_not_jump_to_a_far_corner():
    anchor = fitz.Rect(110, 70, 143, 88)
    # Everything within 25pt of the anchor is blocked; other page is empty.
    words = [fitz.Rect(50, 40, 190, 130)]
    found = marker_rect(anchor, '#01-#03', 500, 340, text_boxes=words)
    assert found is None


def test_multi_badges_remain_collision_free_and_in_near_distance():
    doc = fitz.open()
    p = doc.new_page(width=370, height=210)
    for yy in (64, 84, 104):
        p.insert_text((34, yy), 'CONTAINER NUMBER  ONEU06061381  SEAL ID26911AA', fontsize=9)
    regions = [fitz.Rect(158, 55, 230, 66),
               fitz.Rect(158, 75, 230, 86),
               fitz.Rect(158, 95, 230, 106)]
    words = [fitz.Rect(w[:4]) for w in p.get_text('words')]
    placed = []
    for n, rect in zip(([1,2,3], [4], list(range(5,11))), regions):
        box = draw_number_marker(p, rect, n, 370, 210,
                                 text_boxes=words, protected=regions,
                                 occupied=placed)
        assert box is not None
        assert _rect_distance(box, rect) <= MAX_BADGE_DISTANCE
        assert all(not _intersects_with_clearance(box, w, .7) for w in words)
        assert all(not _intersects_with_clearance(box, h, .7) for h in regions)
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            assert not _intersects_with_clearance(a, b, 1.0)
    doc.close()


def test_old_distant_full_page_fallback_is_gone():
    source = (ROOT / 'correction_markers.py').read_text(encoding='utf-8')
    assert 'BADGE_GAP = 1.8' in source
    assert 'MAX_BADGE_DISTANCE = 22.0' in source
    assert 'for y in range(3, max(4, int(page_height - height)), 12):' not in source
    assert 'scan_ink_guard' in source


def test_source_preserves_shared_export_algorithm():
    source = (ROOT / 'docmatch.py').read_text(encoding='utf-8')
    assert 'v1.8.35.6' in source
    assert 'draw_number_marker(page' in source
    assert 'Koreksi_' in (ROOT / 'export_naming.py').read_text(encoding='utf-8')

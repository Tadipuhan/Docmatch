"""Tight, collision-aware, connector-free PDF markers (v1.8.35.4).

All positions use the examined document's original PDF-point coordinates.  A
number badge is placed outside its highlight and is never painted over known
text, another highlighted value, or an earlier badge.  If the page has no
free space, omit the badge rather than obscuring evidence; its number still
appears in the correction note's heading.

No GUI, OCR, or carrier-specific dependency is required.
"""
from __future__ import annotations

import pymupdf as fitz

MARKER_RED = (0.53, 0.05, 0.11)
BADGE_HEIGHT = 13.0
BADGE_FONT = 7.2
PAGE_INSET = 1.5
TEXT_CLEARANCE = 0.8
MARKER_CLEARANCE = 1.2
BADGE_GAP = 1.8            # PDF points; near-touching, not an excessive padding
MAX_BADGE_DISTANCE = 22.0   # never search a distant unrelated blank region


def marker_label(numbers):
    nums = sorted(set(int(n) for n in numbers))
    if not nums:
        return '#?'
    if len(nums) == 1:
        return f'#{nums[0]:02d}'
    if len(nums) == 2:
        return f'#{nums[0]:02d},#{nums[1]:02d}'
    return f'#{nums[0]:02d}-#{nums[-1]:02d}'


def _intersects_with_clearance(a, b, gap):
    """Strict positive-area overlap, treating the gap as a safety buffer."""
    return (a.x0 < b.x1 + gap and a.x1 > b.x0 - gap and
            a.y0 < b.y1 + gap and a.y1 > b.y0 - gap)


def _rect_distance(a, b):
    """Euclidean outside-edge distance; rectangles which overlap have distance 0."""
    dx = max(0.0, a.x0 - b.x1, b.x0 - a.x1)
    dy = max(0.0, a.y0 - b.y1, b.y0 - a.y1)
    return (dx * dx + dy * dy) ** 0.5


def _sample_line(start, end, step=3.0):
    """Include both endpoints to avoid missing narrow free strips."""
    if end < start:
        return [start]
    count = max(1, int((end - start) / step + .999))
    return [start + (end - start) * i / count for i in range(count + 1)]


def _candidate_positions(anchor, width, height, page_width, page_height):
    """Search along all four highlight edges at very small offsets.

    Prior algorithm tested only 8 alignment points, then distant offsets and
    page-wide whitespace. When these sparse positions hit a word, the badge
    would jump dozens of points away from the highlight. Here the badge moves
    smoothly *along* the target edge first (e.g. to the end of a text line).
    Every candidate stays outside its own target area.
    """
    offsets = (BADGE_GAP, *(float(i) for i in range(2, int(MAX_BADGE_DISTANCE) + 1)))
    y_positions = _sample_line(anchor.y0 - height - 9, anchor.y1 + 9, 1.25)
    x_positions = _sample_line(anchor.x0 - width - 9, anchor.x1 + 9, 1.25)
    options = []
    for extra in offsets:
        # The small gap is measured from the *highlight edge*, not its center.
        for yy in y_positions:
            options.append((anchor.x0 - width - extra, yy, 0))  # left
            options.append((anchor.x1 + extra, yy, 2))          # right
        for xx in x_positions:
            options.append((xx, anchor.y0 - height - extra, 1)) # top
            options.append((xx, anchor.y1 + extra, 3))          # bottom

    def _rank(row):
        x, y, side = row
        rect = fitz.Rect(x, y, x + width, y + height)
        gap = _rect_distance(rect, anchor)
        # Prefer top/left of highlighted content when same distance; this
        # makes badge positioning visually predictable across repeated rows.
        corner = abs(x - (anchor.x0 - width)) + abs(y - anchor.y0)
        return (round(gap, 4), side, corner)

    options.sort(key=_rank)
    for x, y, _ in options:
        if (x >= PAGE_INSET and y >= PAGE_INSET and
                x + width <= page_width - PAGE_INSET and
                y + height <= page_height - PAGE_INSET):
            yield x, y


def _make_word_grid(words, cell_size=32.0):
    """Index word boxes to keep the denser near-edge search fast on long SWBs."""
    from collections import defaultdict
    from math import floor
    buckets = defaultdict(list)
    for r in words:
        x0 = floor(r.x0 / cell_size)
        x1 = floor(r.x1 / cell_size)
        y0 = floor(r.y0 / cell_size)
        y1 = floor(r.y1 / cell_size)
        for xx in range(x0, x1 + 1):
            for yy in range(y0, y1 + 1):
                buckets[(xx, yy)].append(r)
    def nearby(candidate):
        x0 = floor((candidate.x0 - TEXT_CLEARANCE) / cell_size)
        x1 = floor((candidate.x1 + TEXT_CLEARANCE) / cell_size)
        y0 = floor((candidate.y0 - TEXT_CLEARANCE) / cell_size)
        y1 = floor((candidate.y1 + TEXT_CLEARANCE) / cell_size)
        found = set()
        for xx in range(x0, x1 + 1):
            for yy in range(y0, y1 + 1):
                for box in buckets.get((xx, yy), ()):
                    key = id(box)
                    if key not in found:
                        found.add(key)
                        yield box
    return nearby


def marker_rect(anchor, label, source_width: float, source_height: float,
                *, text_boxes=(), occupied=(), protected=(), ink_guard=None):
    """Return the first safe badge box, or None if no safe box exists.

    text_boxes: text/word bounding boxes from the *original* page.
    occupied:  badges already rendered on the same page.
    protected: all highlighted areas (not just this badge's own anchor).
    ink_guard: optional callable(rect)->bool; used for PDFs with no text layer.

    No fallback can draw on top of a character just to force a marker to appear.
    """
    anchor = fitz.Rect(anchor)
    source_width = float(source_width)
    source_height = float(source_height)
    if anchor.is_empty or anchor.is_infinite:
        return None
    font_size = BADGE_FONT
    badge_w = max(24.0, fitz.get_text_length(label, fontname='hebo', fontsize=font_size) + 9)
    badge_h = BADGE_HEIGHT
    if badge_w + 2 * PAGE_INSET > source_width or badge_h + 2 * PAGE_INSET > source_height:
        return None

    # Materialize once; some callers supply generators.  Filter outside-page
    # and invalid rectangles before the many candidate overlap checks.
    reserved = [anchor]
    for r in protected:
        box = fitz.Rect(r)
        if not box.is_empty and not box.is_infinite:
            reserved.append(box)
    words = []
    for r in text_boxes:
        box = fitz.Rect(r)
        if not box.is_empty and not box.is_infinite:
            words.append(box)
    existing = [fitz.Rect(r) for r in occupied]
    nearby_words = _make_word_grid(words)
    seen = set()
    for x, y in _candidate_positions(anchor, badge_w, badge_h,
                                     source_width, source_height):
        if (x < PAGE_INSET or y < PAGE_INSET or
            x + badge_w > source_width - PAGE_INSET or
            y + badge_h > source_height - PAGE_INSET):
            continue
        key = (round(x, 2), round(y, 2))
        if key in seen:
            continue
        seen.add(key)
        candidate = fitz.Rect(x, y, x + badge_w, y + badge_h)
        if any(_intersects_with_clearance(candidate, r, 1.0) for r in reserved):
            continue
        if any(_intersects_with_clearance(candidate, r, TEXT_CLEARANCE) for r in nearby_words(candidate)):
            continue
        if any(_intersects_with_clearance(candidate, r, MARKER_CLEARANCE) for r in existing):
            continue
        if ink_guard is not None and not ink_guard(candidate):
            continue
        return candidate
    return None


def scan_ink_guard(source_page):
    """Avoid ink on image-only and Type3 PDFs without introducing dependencies.

    A 1 pixel/point grayscale integral image is built once per page, so every
    potential badge box can be tested in constant time.  This works even when
    Windows users do not have NumPy installed.
    """
    try:
        from array import array
        pix = source_page.get_pixmap(matrix=fitz.Matrix(1, 1),
                                     colorspace=fitz.csGRAY, alpha=False)
        width, height = pix.width, pix.height
        stride = pix.stride
        samples = pix.samples
        step = width + 1
        prefix = array('I', [0]) * ((height + 1) * step)
        for yy in range(height):
            running = 0
            offset = yy * stride
            row = (yy + 1) * step
            previous = yy * step
            for xx in range(width):
                if samples[offset + xx] < 168:
                    running += 1
                prefix[row + xx + 1] = prefix[previous + xx + 1] + running
        def _blank(rect):
            x0 = max(0, min(width, int(rect.x0)))
            y0 = max(0, min(height, int(rect.y0)))
            x1 = max(x0, min(width, int(rect.x1 + .999)))
            y1 = max(y0, min(height, int(rect.y1 + .999)))
            if x1 <= x0 or y1 <= y0:
                return False
            dark = (prefix[y1 * step + x1] - prefix[y0 * step + x1] -
                    prefix[y1 * step + x0] + prefix[y0 * step + x0])
            # Be conservative: preserve character strokes and printed lines.
            return dark <= max(2, (x1 - x0) * (y1 - y0) * .008)
        return _blank
    except (RuntimeError, ValueError, TypeError, MemoryError):
        return None


def draw_number_marker(page, anchor, numbers, source_width, source_height,
                       *, text_boxes=(), occupied=None, protected=(), ink_guard=None):
    """Draw a legible PDF vector badge only at a collision-free location."""
    label = marker_label(numbers)
    box = marker_rect(anchor, label, source_width, source_height,
                      text_boxes=text_boxes,
                      occupied=occupied if occupied is not None else (),
                      protected=protected, ink_guard=ink_guard)
    if box is None:
        return None
    page.draw_rect(box, color=MARKER_RED, fill=MARKER_RED, width=0.3, overlay=True)
    label_width = fitz.get_text_length(label, fontname='hebo', fontsize=BADGE_FONT)
    page.insert_text((box.x0 + (box.width - label_width)/2, box.y0 + 9.5),
                     label, fontname='hebo', fontsize=BADGE_FONT,
                     color=(1, 1, 1), overlay=True)
    if occupied is not None:
        occupied.append(box)
    return box

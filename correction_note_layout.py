"""Shared, deterministic geometry for PDF margin correction notes.

This module intentionally has no Qt dependencies.  Both the vector PDF writer
and the interactive review page consume the same placement calculation.
"""
from __future__ import annotations

import pymupdf as fitz

NOTE_MARGIN = 310
NOTE_FONT_SIZE = 9.5
NOTE_LINE_HEIGHT = 14


def wrap_note(text: str, width: float, fontsize: float = NOTE_FONT_SIZE) -> list[str]:
    """Wrap to the exported PDF width without normalizing source whitespace.

    Previous ``paragraph.split()`` collapsed multiple spaces in reference
    addresses. Preserve explicitly encoded spaces and original newlines;
    introduce a new line only when an existing line exceeds the note width.
    """
    max_width = width - 15
    output = []
    paragraphs = str(text).split('\n')
    for paragraph in paragraphs:
        remaining = paragraph.rstrip('\r')
        if not remaining:
            output.append('')
            continue
        while remaining:
            if fitz.get_text_length(remaining, fontname='heit', fontsize=fontsize) <= max_width:
                output.append(remaining)
                break
            low, high = 1, len(remaining)
            while low < high:
                mid = (low + high + 1) // 2
                if fitz.get_text_length(remaining[:mid], fontname='heit', fontsize=fontsize) <= max_width:
                    low = mid
                else:
                    high = mid - 1
            # Break after an existing space if possible, keeping it unchanged.
            cut = low
            space = max(remaining.rfind(' ', 0, low + 1), remaining.rfind('\t', 0, low + 1))
            if space > 0:
                cut = space + 1
            output.append(remaining[:cut])
            remaining = remaining[cut:]
    return output or ['']


def note_box_layout(groups: list[dict], page_no: int, source_width: float,
                    source_height: float, margin: float = NOTE_MARGIN):
    """Return full-page height and (group, wrapped lines, note rect) entries.

    Group keys, note text, and ordering match `grouped_correction_notes`.
    No pixels or UI assumptions enter PDF-coordinate layout.
    """
    next_y = 43.0
    entries = []
    for group in groups:
        if group['page'] != page_no:
            continue
        lines = wrap_note(group['text'], margin - 30)
        height = 31 + len(lines) * NOTE_LINE_HEIGHT
        rect = fitz.Rect(source_width + 14, next_y,
                         source_width + margin - 9, next_y + height)
        entries.append((group, lines, rect))
        next_y = rect.y1 + 8
    page_height = max(float(source_height), next_y + 18 if entries else float(source_height))
    return page_height, entries

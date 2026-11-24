"""Verbatim reference-value layout for address and cargo fields in PDF correction notes.

This module never changes the value used for matching.  It only formats the
existing, independently extracted reference value for user-facing notes.
PDFs do not guarantee storage of visual whitespace: preserve actual encoded
spaces and separate text lines without synthesizing unseen address content.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import re
import pymupdf as fitz

ADDRESS_FIELDS = frozenset(('shipper', 'consignee', 'notify party'))


def is_address_field(field: str) -> bool:
    return ' '.join(str(field).casefold().split()) in ADDRESS_FIELDS


def _compact(value):
    return re.sub(r'\s+', '', value).casefold()


def _word_text_fallback(words):
    """Recovery fallback for Type3 glyphs that cannot be decoded by native PDF."""
    groups = []
    ordered = sorted(words, key=lambda w: (int(w.get('page', 0)), float(fitz.Rect(w['rect']).y0), float(fitz.Rect(w['rect']).x0)))
    for word in ordered:
        rect = fitz.Rect(word['rect'])
        if (not groups or groups[-1]['page'] != int(word.get('page', 0))
                or abs(groups[-1]['y'] - rect.y0) > max(2.5, min(8., rect.height * .6))):
            groups.append({'page': int(word.get('page', 0)), 'y': rect.y0, 'words': [word]})
        else:
            groups[-1]['words'].append(word)
    return '\n'.join(' '.join(str(w['word']) for w in sorted(group['words'], key=lambda w: fitz.Rect(w['rect']).x0))
                     for group in groups)


def _verbatim_from_words(doc, words):
    """Recover source characters from original PDF lines selected by field words.

    A word rectangle identifies the source *line* and the contiguous character
    interval, so neighboring table columns are not copied to the note. Actual
    spaces embedded in the PDF text stream and original case are retained.
    """
    if not words:
        return ''
    by_page = defaultdict(list)
    for token in words:
        r = fitz.Rect(token.get('rect'))
        pno = int(token.get('page', 0))
        if not r.is_empty and not r.is_infinite and 0 <= pno < len(doc):
            by_page[pno].append((r, str(token.get('word', ''))))

    lines_out = []
    for pno in sorted(by_page):
        page = doc[pno]
        raw = page.get_text('rawdict', sort=False)
        lines = []
        for bi, block in enumerate(raw.get('blocks', [])):
            for li, line in enumerate(block.get('lines', [])):
                chars = [char for span in line.get('spans', []) for char in span.get('chars', [])]
                if chars:
                    lines.append((bi, li, fitz.Rect(line['bbox']), chars))
        selected = defaultdict(list)
        unassigned = []
        for r, word in by_page[pno]:
            options = []
            for i, (_, _, line_rect, chars) in enumerate(lines):
                vertical = max(0, min(r.y1, line_rect.y1) - max(r.y0, line_rect.y0))
                horizontal = max(0, min(r.x1, line_rect.x1) - max(r.x0, line_rect.x0))
                if vertical > 0 and horizontal > 0:
                    options.append((vertical / max(r.height, .01), horizontal / max(r.width, .01), i))
            if options:
                selected[max(options)[2]].append((r, word))
            else:
                unassigned.append({'rect': r, 'word': word, 'page': pno})

        ordered = []
        for i, tokens in selected.items():
            bi, li, line_rect, chars = lines[i]
            x0 = min(r.x0 for r, _ in tokens)
            x1 = max(r.x1 for r, _ in tokens)
            # Recover encoded spaces between the first and last selected words.
            # Do not absorb text outside the selected field's word interval.
            text = ''.join(char.get('c', '') for char in chars
                           if x0 - .3 <= (char['bbox'][0] + char['bbox'][2]) / 2 <= x1 + .3)
            expected = ' '.join(word for r, word in sorted(tokens, key=lambda t: t[0].x0))
            # Type3/private glyph fonts can produce gibberish in rawdict. In
            # that case keep the trusted words already decoded by the engine.
            match = SequenceMatcher(None, _compact(text), _compact(expected), autojunk=False).ratio()
            if match < .75 or not text.strip():
                text = expected
            ordered.append((line_rect.y0, line_rect.x0, bi, li, text))
        ordered.sort(key=lambda item: (round(item[0], 1), item[1], item[2], item[3]))
        for _, _, _, _, text in ordered:
            lines_out.append(text.rstrip('\r\n'))
        if unassigned:
            fallback = _word_text_fallback(unassigned)
            if fallback:
                lines_out.append(fallback)
    return '\n'.join(lines_out).strip('\r\n')


def address_reference_values(path, profile, fields, field_map=None):
    """Read *complete* field values from PDF A for note presentation only.

    Do not guess unavailable fields. A failure returns no override, leaving the
    existing correction note logic intact. Use one extractor call for all fields.
    """
    requested = {str(field) for field in fields if is_address_field(field)}
    if not requested or not path:
        return {}
    field_map = field_map or {field: field for field in requested}
    source_fields = {source for field in requested if field in field_map
                     for source in (field_map[field] if isinstance(field_map[field], (tuple, list))
                                    else (field_map[field],))}
    if not source_fields:
        return {}
    from flexible_reference import detect_flexible_pdf, extract_flexible
    from waybill_rules import extract, profile_field_names
    path = str(path)
    # Use *all* carrier field labels as stop boundaries. Without them the last
    # address (Notify Party) may swallow the following Document Number / Port.
    all_labels = set(profile_field_names(profile)) | source_fields
    try:
        is_flexible = detect_flexible_pdf(path, all_labels) if profile != 'flexible' else True
        records = (extract_flexible(path, all_labels, word_level=False) if is_flexible else
                   extract(path, source_fields, profile=profile))
        result = {}
        with fitz.open(path) as doc:
            for field in requested:
                lookup = field_map.get(field)
                item = records.get(lookup) if isinstance(lookup, str) else None
                item = item or {}
                if item.get('valid') is False or not item.get('words'):
                    continue
                native = _verbatim_from_words(doc, item['words'])
                if native.strip():
                    result[field] = native
        return result
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError):
        # An unreliable crop must never be turned into a fabricated note.
        return {}


# Formatting-only targets; these do not change field extraction or the comparison
# engine. The actual name is preserved as used by each shipping-line profile.
STRUCTURED_FIELDS = frozenset({
    'container & seal', 'main - container & seal',
    'cargo description', 'main - cargo description',
    'weight & measurement', 'weight & measurment',
    'attached list - weight & measurement',
    'gross weight', 'gross measurement',
})


def is_structured_field(field: str) -> bool:
    return ' '.join(str(field).casefold().split()) in STRUCTURED_FIELDS


def _verbatim_structured_rows(doc, words):
    """Render the *selected* reference words into visual rows.

    Container/seal columns are often separate PDF spans positioned at the same
    Y coordinate (e.g. ONE's container number and seal). The native extractor
    emits one line per span; group only same-row selected words here, retaining
    their native characters, including encoded double spaces and punctuation.
    Never reach outside the word regions selected for this specific field.
    """
    if not words:
        return ''
    ordered = []
    for token in words:
        try:
            r = fitz.Rect(token['rect'])
            page = int(token.get('page', 0))
        except (ValueError, TypeError, KeyError):
            continue
        if r.is_empty or r.is_infinite or page < 0 or page >= len(doc):
            continue
        ordered.append((page, r, token))
    ordered.sort(key=lambda item: (item[0], (item[1].y0 + item[1].y1)*.5, item[1].x0))
    groups = []
    for page, rect, word in ordered:
        cy = (rect.y0 + rect.y1) * .5
        # At most 2 pt in ordinary waybill text. Prevent two distinct rows of
        # small table lettering from being collapsed into one correction line.
        tolerance = min(2.4, max(0.7, rect.height * .22))
        match = next((g for g in reversed(groups[-10:])
                      if g['page'] == page and abs(g['cy'] - cy) <= min(tolerance, g['tolerance'])), None)
        if match is None:
            groups.append({'page':page, 'cy':cy,'tolerance':tolerance,'words':[word]})
        else:
            match['words'].append(word)
    lines = []
    for group in groups:
        row = _verbatim_from_words(doc, group['words'])
        if not row.strip():
            continue
        # A single row with separately positioned columns can become several
        # text lines from PyMuPDF. Join those *only* because their selected
        # words share a visual baseline. Two spaces make the column break
        # legible; no guessed content is inserted.
        lines.append('  '.join(row.split('\n')))
    return '\n'.join(lines).strip('\r\n')


def _suspect_cross_column(field: str, value: str) -> bool:
    """Reject obvious spillover rather than silently supplying a wrong note."""
    normalized = ' '.join(value.upper().split())
    if not normalized or '\ufffd' in normalized:
        return True
    name = field.casefold()
    if 'container & seal' in name:
        # Phone/email/freight instructions cannot belong to the container ID
        # list; in Evergreen these come from adjacent form cells.
        if (re.search(r'\b(?:INVOICE\s+NO|FREIGHT\s+PREPAID|TEL\s*:|FAX\s*:|E-?MAIL\s*:)', normalized)
                or '@' in normalized):
            return True
    if 'cargo description' in name:
        # Some Evergreen scans leak the PRINTED watermark (VERIFY / COPY)
        # and cells from other columns into the cargo region.
        if re.search(r'\b(?:VERIFY|COPY)\b', normalized):
            return True
        if normalized.startswith(('ERIFY ', 'NDONESIA ', 'ISTICS.COM/')):
            return True
    return False


def structured_reference_values(path, profile, fields, field_map=None):
    """Complete, source-faithful cargo / weight notes from independent PDF A.

    Supports labeled free-layout references and original carrier waybills. If a
    value cannot be trusted, returns no override for that field. Manual edits
    stay managed by Window.grouped_correction_notes, and matching is unchanged.
    """
    requested = {str(field) for field in fields if is_structured_field(field)}
    if not requested or not path:
        return {}
    field_map = field_map or {field: field for field in requested}
    source_fields = {source for field in requested if field in field_map
                     for source in (field_map[field] if isinstance(field_map[field], (tuple, list))
                                    else (field_map[field],))}
    if not source_fields:
        return {}
    from flexible_reference import detect_flexible_pdf, extract_flexible
    from waybill_rules import extract, profile_field_names
    path = str(path)
    labels = set(profile_field_names(profile)) | source_fields
    try:
        is_flexible = detect_flexible_pdf(path, labels) if profile != 'flexible' else True
        records = (extract_flexible(path, labels, word_level=False) if is_flexible else
                   extract(path, source_fields, profile=profile))
        with fitz.open(path) as doc:
            result = {}
            for field in requested:
                lookup = field_map.get(field)
                sources = lookup if isinstance(lookup, (tuple, list)) else (lookup,)
                sources = [records.get(source) for source in sources if source]
                if not sources or any(not item or item.get('valid') is False or not item.get('words')
                                      for item in sources):
                    continue
                native = _verbatim_structured_rows(
                    doc, [word for item in sources for word in item['words']])
                if lookup == 'Weight & Measurement' and field in ('Gross Weight', 'Gross Measurement'):
                    from cross_carrier import _part
                    native = _part(native, field) or ''
                if native.strip() and not _suspect_cross_column(field, native):
                    result[field] = native
            return result
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError):
        return {}

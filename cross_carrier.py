"""Conservative, offline cross-carrier SWB profile detection and field correspondence.

The reference is never extracted with the examined document's cell coordinates
unless their profiles were independently identified as the same. When a
correspondence is not established, callers must request manual verification.
"""
from __future__ import annotations

import re
from typing import Optional
import pymupdf as fitz

PROFILES = (
    ('waybill_anl', 'ANL / CNC / CMA CGM'),
    ('waybill_evergreen', 'Evergreen'),
    ('waybill_gsl', 'Golden Star Line'),
    ('waybill_one', 'ONE'),
    ('waybill_maersk', 'Maersk'),
    ('waybill_meratus', 'Meratus'),
    ('waybill_msc', 'MSC'),
)
PROFILE_LABELS = dict(PROFILES)

# Names must mean the same thing; do not equate documents, booking references,
# on-board dates, and destinations just because their labels sound alike.
_FIELD_ALIASES = {
    'main - container & seal': 'container & seal',
    'main - cargo description': 'cargo description',
    'final place of delivery': 'place of delivery',
    'place and date of issue': 'place & date of issue',
    'number of original waybills': 'number of original waybills',
    'bill of lading number': 'waybill number',
    'bl number': 'waybill number',
    'b/l number': 'waybill number',
}


def canonical_field(name: str) -> str:
    key = re.sub(r'\s+', ' ', str(name).casefold().strip())
    return _FIELD_ALIASES.get(key, key)


def reference_field_map(examined_fields, reference_fields):
    """Exam field -> strictly equivalent reference field, deterministic and unique."""
    by_canonical = {}
    for name in reference_fields:
        by_canonical.setdefault(canonical_field(name), []).append(name)
    mapping = {}
    for name in examined_fields:
        matches = by_canonical.get(canonical_field(name), [])
        if len(matches) == 1:
            mapping[name] = matches[0]
            continue
        # Only a few explicitly understood compound fields can be reconciled.
        # Never map generic "Destination" to Place of Delivery, for example.
        if name == 'Vessel / Voyage' and {'Vessel', 'Voyage Number'} <= set(reference_fields):
            mapping[name] = ('Vessel', 'Voyage Number')
        elif name in ('Vessel', 'Voyage Number') and 'Vessel / Voyage' in reference_fields:
            mapping[name] = 'Vessel / Voyage'
        elif name in ('Gross Weight', 'Gross Measurement') and 'Weight & Measurement' in reference_fields:
            mapping[name] = 'Weight & Measurement'
        elif name == 'Weight & Measurement' and {'Gross Weight', 'Gross Measurement'} <= set(reference_fields):
            mapping[name] = ('Gross Weight', 'Gross Measurement')
    return mapping


def _page_text(pdf, first_pages=2):
    with fitz.open(pdf) as doc:
        if not len(doc):
            return ''
        parts = []
        for page in list(doc)[:first_pages]:
            parts.append(page.get_text(sort=False))
        return ' '.join(parts).casefold()


def detect_reference_profile(pdf, candidate_fields=None) -> Optional[str]:
    """Return a supported preset, 'flexible', or None (ambiguous/unreadable).

    Strong carrier-specific evidence only. A letter mentioning a carrier's
    name is *not* enough to be classified as that carrier's SWB form.
    """
    from flexible_reference import detect_flexible_pdf
    if detect_flexible_pdf(pdf, candidate_fields):
        return 'flexible'
    txt = _page_text(pdf)
    compact = ' '.join(txt.split())
    title = any(t in compact for t in ('sea waybill', 'way bill', 'waybill',
                                        'bill of lading', 'b/l no.', 'bl no.'))
    forms = any(t in compact for t in ('shipper', 'consignee', 'notify party'))
    if not title or not forms:
        return None
    evidence = {
        'waybill_msc': ('mediterranean shipping company s.a.' in compact or
                         ('msc' in compact and 'no. of rider pages' in compact)),
        'waybill_maersk': (bool(re.search(r'\bmaeu\b', compact)) and
                           bool(re.search(r'\bscac\b', compact))) or
                           ('maersk' in compact and 'freight & charges' in compact),
        'waybill_one': ('particulars declared by shipper but not acknowledged by the carrier' in compact and
                        ('cntr. nos.' in compact or 'ocean network express' in compact or 'original bills' in compact)),
        'waybill_meratus': ('meratus' in compact and ('received by the carrier' in compact or
                              'particulars furnished by the merchant' in compact)) or
                              ('as agent for the carrier' in compact and 'meratus' in compact),
        'waybill_gsl': ('goldstar line' in compact or 'gold star line' in compact),
        'waybill_evergreen': ('evergreen line' in compact or 'evergreen marine' in compact or
                              'evergreen shipping' in compact),
        'waybill_anl': (('anl singapore' in compact or 'anl shipping' in compact or
                           'cma cgm' in compact or 'cnc line' in compact) and
                          sum(t in compact for t in ('port of loading','port of discharge',
                                                     'number of original waybills','notify party',
                                                     'shipper','consignee')) >= 4),
    }
    matched = [name for name, present in evidence.items() if present]
    return matched[0] if len(matched) == 1 else None


def normalized_value(value):
    return re.sub(r'\s+', '', str(value)).casefold()

# Treat the combined fields conservatively: extract only when the syntax contains
# an identifiable voyage suffix or recognised measurement unit. No guessing.
_VOYAGE = re.compile(r"^(?=[A-Z0-9-]*\d)[A-Z0-9-]{3,12}$", re.I)
_WEIGHT = re.compile(r"(?<!\d)([\d.,]+)\s*(KGS?\.?|KILOGRAMS?|TONNES?|TONS?)\b", re.I)
_MEAS = re.compile(r"(?<!\d)([\d.,]+)\s*(CBM|CU\.?\s*M\.?|M3|CUBIC\s*METERS?)\b", re.I)


def _part(text, field):
    matcher = _WEIGHT if field == 'Gross Weight' else _MEAS
    match = matcher.search(str(text))
    return match.group(0) if match else None


def measurement_signature(text, field):
    """Comparable (quantity, unit-family) values or None for unsafe parsing."""
    text = str(text)
    matches = ([('weight', _WEIGHT.search(text))] if field == 'Gross Weight' else
               [('measurement', _MEAS.search(text))] if field == 'Gross Measurement' else
               [('weight', _WEIGHT.search(text)), ('measurement', _MEAS.search(text))])
    if any(match is None for _, match in matches):
        return None
    return tuple((kind, match.group(1).replace(',', ''),
                  re.sub(r'\W', '', match.group(2)).casefold()) for kind, match in matches)


def split_compound_record(source, destination):
    """Split a carrier's combined field without inventing a ship/voyage/unit."""
    words = source.get('words', [])
    text = str(source.get('text', ''))
    if destination in ('Gross Weight', 'Gross Measurement'):
        value = _part(text, destination)
        if not value:
            return {'text':'', 'words':[], 'valid':False, 'reason':'Unit tidak dapat dipisahkan'}
        # The original PDF coordinates are still from this source field. When
        # merged into one PDF span it is safer to mark the whole span.
        return dict(source, text=value, words=words)
    if destination in ('Vessel', 'Voyage Number'):
        tokens = text.split()
        if len(tokens) < 2 or not _VOYAGE.fullmatch(tokens[-1]):
            return {'text':'', 'words':[], 'valid':False, 'reason':'Nomor voyage tidak dapat dipisahkan'}
        vessel = ' '.join(tokens[:-1]).rstrip(' -/')
        if not vessel:
            return {'text':'', 'words':[], 'valid':False, 'reason':'Nama vessel kosong'}
        value = vessel if destination == 'Vessel' else tokens[-1]
        if words and len(words) == len(tokens):
            selected = words[:-1] if destination == 'Vessel' else words[-1:]
        else:
            selected = words  # merged line: keep original source geometry
        return dict(source, text=value, words=selected)
    return dict(source)

_CONTAINER_CODE = re.compile(r"\b([A-Z]{4}\s?\d{7})\b", re.I)
_SEAL_AFTER = re.compile(r"(?:\bSEAL(?:\s*(?:NO|NUMBER))?\s*[:#./-]?\s*|/\s*)([A-Z0-9][A-Z0-9-]{4,})", re.I)


def container_pairs(text):
    """Return exact unordered (container, seal) records, or None if uncertain.

    The seal must follow each container within its own entry. This prevents
    confusing a matching container number with a matching container+seal pair.
    """
    text = str(text).upper()
    containers = list(_CONTAINER_CODE.finditer(text))
    if not containers:
        return None
    found = []
    for index, match in enumerate(containers):
        end = containers[index + 1].start() if index + 1 < len(containers) else len(text)
        # The next 60 characters are enough for a seal token. Later prose is
        # never evidence of a seal associated with this container.
        tail = text[match.end():min(end, match.end() + 60)]
        seal = _SEAL_AFTER.search(tail)
        if not seal or seal.group(1) in {'CONTAINER', 'QUANTITY', 'WEIGHT'}:
            return None
        found.append((re.sub(r'\s+', '', match.group(1)), seal.group(1)))
    return tuple(sorted(found))

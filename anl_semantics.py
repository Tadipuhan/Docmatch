"""Kesetaraan NILAI field (bukan kesetaraan teks) untuk profil ANL/CNC/CMA CGM.

Dokumen rujukan berupa surat/tabel menulis nilai dengan layout berbeda dari formulir carrier:

    surat:      Weight & Measurement  "17,800.000 KGS / 100.500 CBM"
    formulir:   kolom Gross / Tare / Measurement  ->  "17800.000 6800 100.500"

Membandingkan teks keduanya selalu MISMATCH walaupun nilainya sama. Modul ini mengubah
tiap sisi ke bentuk kanonik dan membandingkan nilainya. Prinsip:

  * Hanya dipakai untuk field yang punya aturan kanonik di bawah. Selain itu: None, artinya
    pemanggil memakai perbandingan teks biasa.
  * Bagian yang hanya ada di satu sisi TIDAK dianggap berbeda (surat rujukan tidak memuat
    tare, misalnya) tetapi bagian yang ada di KEDUA sisi harus sama.
  * Bila salah satu sisi tidak bisa diurai sama sekali: None (jangan menebak, jangan
    menyatakan sama).
Fungsi di sini murni (tanpa PyMuPDF) dan diuji di tests/test_anl_semantics.py.
"""
from __future__ import annotations
import re
from datetime import date
from decimal import Decimal, InvalidOperation

_MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
_MONTHS.update({'mei': 5, 'agu': 8, 'agt': 8, 'okt': 10, 'des': 12})
_NUMBER_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
                 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}


# ----------------------------------------------------------------------------
# Angka
# ----------------------------------------------------------------------------
def parse_number(token):
    """'17,800.000' -> Decimal('17800.000'); '4911.650' -> Decimal('4911.650'); None bila bukan angka."""
    t = str(token).strip().strip('.,')
    if not re.fullmatch(r'\d[\d.,]*', t):
        return None
    has_dot, has_comma = '.' in t, ',' in t
    if has_dot and has_comma:
        decimal_sep = '.' if t.rfind('.') > t.rfind(',') else ','
        thousands = ',' if decimal_sep == '.' else '.'
        t = t.replace(thousands, '').replace(decimal_sep, '.')
    elif has_comma:
        t = t.replace(',', '') if re.fullmatch(r'\d{1,3}(,\d{3})+', t) else t.replace(',', '.')
    elif has_dot and re.fullmatch(r'\d{1,3}(\.\d{3}){2,}', t):
        t = t.replace('.', '')                      # 1.234.567 = ribuan; 4911.650 = desimal
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


_WEIGHT_UNIT = re.compile(r'(\d[\d.,]*)\s*(?:kgs?|kilograms?|kilos?)\b', re.I)
_MEASURE_UNIT = re.compile(r'(\d[\d.,]*)\s*(?:cbm|m3|m\u00b3)\b', re.I)
_TARE_LABEL = re.compile(r'tare\W{0,3}(\d[\d.,]*)', re.I)


def parse_weight_measure(text):
    """Kembalikan {'gross','tare','measurement'} (hanya yang ditemukan) atau {}.

    Bentuk yang dikenali:
      * berunit:      '17,800.000 KGS / 100.500 CBM', '17800 KG 100.5 M3'
      * tiga angka    (kolom formulir carrier): gross  tare  measurement
    """
    text = str(text or '')
    found = {}
    m = _WEIGHT_UNIT.search(text)
    if m and parse_number(m.group(1)) is not None:
        found['gross'] = parse_number(m.group(1))
    m = _MEASURE_UNIT.search(text)
    if m and parse_number(m.group(1)) is not None:
        found['measurement'] = parse_number(m.group(1))
    m = _TARE_LABEL.search(text)
    if m and parse_number(m.group(1)) is not None:
        found['tare'] = parse_number(m.group(1))
    if found:
        return found
    numbers = [parse_number(t) for t in re.findall(r'\d[\d.,]*', text)]
    numbers = [n for n in numbers if n is not None]
    if len(numbers) == 3:                           # gross, tare, measurement
        return {'gross': numbers[0], 'tare': numbers[1], 'measurement': numbers[2]}
    return {}


# ----------------------------------------------------------------------------
# Kontainer & seal
# ----------------------------------------------------------------------------
_CONTAINER = re.compile(r'\b([A-Z]{4})\s?(\d{7})\b')
_SEAL = re.compile(r'\bSEAL\b[\s:#.\-]*([A-Z0-9][A-Z0-9\-]*)', re.I)


def parse_containers(text):
    text = str(text or '')
    containers = {a + b for a, b in _CONTAINER.findall(text.upper())}
    seals = {m.group(1).upper() for m in _SEAL.finditer(text)}
    return containers, seals


# ----------------------------------------------------------------------------
# Tempat & tanggal
# ----------------------------------------------------------------------------
_DATE_PATTERNS = [
    (re.compile(r'(\d{1,2})[\s\-/.]*([A-Za-z]{3,9})[\s\-/.,]*(\d{4})'), 'dmy_name'),
    (re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'), 'ymd'),
    (re.compile(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})'), 'dmy'),
]


def parse_place_date(text):
    """'JAKARTA / 19 NOV 2026' -> ('jakarta', date(2026, 11, 19)). Bagian yang tak terbaca: None."""
    text = str(text or '').strip()
    parsed, span = None, None
    for pattern, kind in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            try:
                if kind == 'dmy_name':
                    month = _MONTHS.get(m.group(2)[:3].casefold())
                    if not month:
                        continue
                    parsed = date(int(m.group(3)), month, int(m.group(1)))
                elif kind == 'ymd':
                    parsed = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                else:                                # DD/MM/YYYY (konvensi ANL/Indonesia)
                    parsed = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                parsed = None
                continue
            span = m.span()
            break
        if parsed:
            break
    place_text = text if span is None else (text[:span[0]] + ' ' + text[span[1]:])
    place = re.sub(r'\s+', ' ', re.sub(r'[/,;|\-]+', ' ', place_text)).strip().casefold()
    return (place or None), parsed


# ----------------------------------------------------------------------------
# Jumlah dokumen asli
# ----------------------------------------------------------------------------
def parse_original_count(text):
    text = str(text or '')
    m = re.search(r'\((\d+)\)', text)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(\d+)\b', text)
    if m:
        return int(m.group(1))
    for word, value in _NUMBER_WORDS.items():
        if re.search(r'\b' + word + r'\b', text, re.I):
            return value
    return None


# ----------------------------------------------------------------------------
# API
# ----------------------------------------------------------------------------
def fields_equal(field, reference_text, examined_text):
    """True / False bila nilai dapat dibandingkan secara kanonik; None bila tidak (pakai teks)."""
    if field == 'Weight & Measurement':
        a, b = parse_weight_measure(reference_text), parse_weight_measure(examined_text)
        common = [k for k in ('gross', 'measurement', 'tare') if k in a and k in b]
        if not a or not b or not common:
            return None
        return all(a[k] == b[k] for k in common)
    if field == 'Container & Seal':
        ca, sa = parse_containers(reference_text)
        cb, sb = parse_containers(examined_text)
        if not ca or not cb:
            return None
        if ca != cb:
            return False
        if sa and sb:
            return sa == sb
        return True
    if field == 'Place & Date of Issue':
        pa, da = parse_place_date(reference_text)
        pb, db = parse_place_date(examined_text)
        if da is None or db is None:
            return None
        if da != db:
            return False
        return pa is None or pb is None or pa == pb
    if field == 'Number of Original Waybills':
        a, b = parse_original_count(reference_text), parse_original_count(examined_text)
        if a is None or b is None:
            return None
        return a == b
    return None

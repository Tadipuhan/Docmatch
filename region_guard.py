"""Validasi relevansi hasil OCR terhadap field (v1.8.30).

Confidence OCR saja tidak membuktikan bahwa teks berasal dari parameter yang
dimaksud. Pada v1.8.29 OCR untuk Notify Party pernah membaca Clauses/Cargo
Description. Di sini hasil OCR dibandingkan dengan teks native (Type3 yang sudah
terdekode) dari SETIAP kotak halaman: bila OCR hampir tidak mirip dengan field
yang diminta tetapi sangat mirip dengan field lain, kandidat ditolak.

Bila tidak ada teks native pembanding, fungsi tidak menolak (tidak bisa menilai).
"""
from __future__ import annotations
import re
from textnorm import normalize_text

OWN_MIN = 0.25       # minimal porsi token OCR yang ada di field sendiri agar lolos
OTHER_MAX = 0.60     # porsi token OCR di field lain yang dianggap "salah wilayah"


def tokens(text):
    return re.findall(r'[a-z0-9]+', normalize_text(text))


def overlap(candidate_tokens, reference_tokens):
    """Porsi token unik kandidat yang muncul di referensi (0..1)."""
    cand = set(candidate_tokens)
    return len(cand & set(reference_tokens)) / len(cand) if cand else 0.0


def check_ocr_relevance(field, ocr_text, native_by_field, own_min=OWN_MIN, other_max=OTHER_MAX):
    """Kembalikan (diterima: bool, alasan: str)."""
    cand = tokens(ocr_text)
    own = tokens(native_by_field.get(field, ''))
    if len(cand) < 2 or not own:
        return True, ''
    if overlap(cand, own) >= own_min:
        return True, ''
    best_score, best_name = 0.0, None
    for name, text in native_by_field.items():
        if name == field:
            continue
        score = overlap(cand, tokens(text))
        if score > best_score:
            best_score, best_name = score, name
    if best_score >= other_max:
        return False, 'Hasil OCR cocok dengan field "%s", bukan "%s"' % (best_name, field)
    return True, ''

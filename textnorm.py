"""Normalisasi teks tunggal untuk Tahap 1 dan Tahap 2 (v1.8.30).

Pada v1.8.29 Tahap 1 hanya membuang spasi, sedangkan Tahap 2 menghapus SEMUA
tanda baca, sehingga "HANEXPRESS CO.,LTD (BUSAN)" dan "HANEXPRESS CO LTD BUSAN"
dianggap sama di Tahap 2 tetapi berbeda di Tahap 1. Sekarang keduanya memakai
fungsi di sini.

Aturan: huruf besar/kecil diabaikan, spasi berulang diringkas, tanda baca TETAP
dihitung (kurung, titik, koma, strip bisa menjadi kesalahan dokumen yang nyata).
"""
from __future__ import annotations
import re
import unicodedata

_SPACES = re.compile(r'\s+')


def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text or '')
    return _SPACES.sub(' ', text).strip().casefold()


def normalize_compact(text: str) -> str:
    """Seperti normalize_text tetapi tanpa spasi; untuk perbandingan per-kata."""
    return normalize_text(text).replace(' ', '')


def loose_equal(a: str, b: str) -> bool:
    """Hanya untuk hint 'mirip' di UI; JANGAN dipakai untuk memutus MATCH."""
    strip = lambda t: re.sub(r'[^\w]+', '', normalize_text(t))
    return strip(a) == strip(b)

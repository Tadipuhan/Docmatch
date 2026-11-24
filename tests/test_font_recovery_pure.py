"""Fungsi murni gsl_font_recovery + textnorm (tanpa PyMuPDF, tanpa PDF)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gsl_font_recovery as gfr  # noqa: E402
import textnorm  # noqa: E402

BLANK = b'1 0 -10 -10 10 10 d1\n0.01 0 0 0.01 0 0 cm\n'
BAR = b'1 0 -10 -10 10 10 d1\n0.01 0 0 0.01 0 0 cm\n9.3 0 9.4 71.8 re\nf\n'
LETTER_A = b'1 0 -10 -10 10 10 d1\n0.01 0 0 0.01 0 0 cm\n1 0 m\n5 70 l\n9 0 l\nh\nf\n'


def test_blank_and_rect_glyphs():
    assert gfr.glyph_is_blank(BLANK)
    assert not gfr.glyph_is_blank(BAR)          # 'I' digambar dengan operator re
    assert not gfr.glyph_is_blank(LETTER_A)
    assert not gfr.glyph_is_blank(b'q /Im0 Do Q')   # raster bukan spasi


def test_space_is_by_glyph_not_by_code_number():
    """Regresi v1.8.29: kode 3 dipaksa spasi padahal bisa huruf 'A'."""
    table = {gfr.glyph_hash(LETTER_A): 'A'}
    # dokumen A halaman 3: kode 3 = 'A', spasi sebenarnya kode 6
    doc_a = gfr.build_charmap({3: LETTER_A, 6: BLANK}, table)
    assert doc_a == {3: 'A', 6: ' '}
    # dokumen B halaman 3: kode 3 = spasi
    doc_b = gfr.build_charmap({3: BLANK, 7: LETTER_A}, table)
    assert doc_b == {3: ' ', 7: 'A'}


def test_unknown_glyph_fails_safe_and_is_reported():
    report = {}
    charmap = gfr.build_charmap({1: BAR}, table={}, report=report)
    assert charmap[1] == gfr.REPLACEMENT
    assert gfr.glyph_hash(BAR) in report and report[gfr.glyph_hash(BAR)]['count'] == 1


def test_conflicting_fonts_become_ambiguous():
    merged = gfr.merge_charmaps([{1: 'A', 2: 'B'}, {1: 'C', 3: 'D'}])
    assert merged == {1: gfr.REPLACEMENT, 2: 'B', 3: 'D'}
    assert gfr.merge_charmaps([{1: 'A'}, {1: 'A'}]) == {1: 'A'}


def test_parse_differences_and_charprocs():
    assert gfr.parse_differences('[0 /0 /1 /.notdef 12 /g12 /g13]') == {
        0: '0', 1: '1', 2: '.notdef', 12: 'g12', 13: 'g13'}
    assert gfr.parse_differences('<</Type/Encoding/Differences[ 5 /a /b ]>>') == {5: 'a', 6: 'b'}
    assert gfr.parse_charprocs('<</47 12 0 R/.notdef 9 0 R/A 3 0 R>>') == {
        '47': 12, '.notdef': 9, 'A': 3}


def test_tight_rect_fixes_inflated_type3_bbox():
    inflated = (100.0, 500.0, 106.0, 519.5)            # tinggi 19,5 pt, ukuran 7,48
    x0, y0, x1, y1 = gfr.tight_char_rect(inflated, (100.0, 512.0), 7.48)
    assert (y1 - y0) < 1.1 * 7.48 and y0 < 512.0 < y1
    assert (x0, x1) == (100.0, 106.0)
    normal = (10.0, 20.0, 15.0, 28.0)                   # font normal tanpa force tidak diubah
    assert gfr.tight_char_rect(normal, (10.0, 27.0), 8.0) == normal
    assert gfr.tight_char_rect(inflated, None, 7.48) == inflated


def test_type3_box_below_baseline_is_moved_onto_the_text():
    """Kasus screenshot v1.8.30.9: kotak PyMuPDF = baseline .. baseline + 1 em (di BAWAH huruf)."""
    size, baseline = 7.48, 512.0
    below = (100.0, baseline, 105.0, baseline + size)   # tinggi 1,0 x ukuran: lolos ambang 1,35
    assert gfr.tight_char_rect(below, (100.0, baseline), size) == below        # tanpa force: tidak dikenali
    x0, y0, x1, y1 = gfr.tight_char_rect(below, (100.0, baseline), size, force=True)
    glyph_top, glyph_bottom = baseline - 0.72 * size, baseline            # huruf kapital 72% em di atas baseline
    assert y0 <= glyph_top and y1 >= glyph_bottom                         # kotak menutup huruf
    assert (y1 - y0) < 1.1 * size                                         # dan tidak membengkak
    assert (x0, x1) == (100.0, 105.0)


def test_normalisation_keeps_punctuation_differences():
    n = textnorm.normalize_text
    assert n('HANEXPRESS CO.,LTD (BUSAN)') != n('HANEXPRESS CO LTD BUSAN')
    assert n('A   B\n c') == 'a b c'
    assert textnorm.loose_equal('HANEXPRESS CO.,LTD (BUSAN)', 'HANEXPRESS CO LTD BUSAN')


def test_run_anchor_keeps_overflowing_value_in_one_cell():
    """Kasus GSL: 'CAT LAI TERMINAL - HO CHI MINH CITY' melewati garis kotak."""
    size = 7.5
    words, x = [], 180.0
    for text in ['CAT', 'LAI', 'TERMINAL', '-', 'HO', 'CHI', 'MINH', 'CITY']:
        width = 4.9 * len(text)
        words.append({'word': text, 'rect': (x, 285.0, x + width, 291.0)})
        x += width + 2.0
    gfr.assign_run_anchors(words, size)
    anchors = {w['anchor'] for w in words}
    assert len(anchors) == 1                       # satu run, satu anchor
    assert words[0]['anchor'][0] < 220             # titik tengah kata PERTAMA, bukan kata terakhir
    assert words[-1]['rect'][2] > 297              # kata terakhir memang melewati x=297 (garis kotak)


def test_run_anchor_splits_runs_on_large_gap():
    size = 7.5
    words = [{'word': 'INTERASIA', 'rect': (60.0, 285.0, 104.0, 291.0)},
             {'word': 'N044', 'rect': (106.0, 285.0, 126.0, 291.0)},
             {'word': 'JAKARTA,', 'rect': (190.0, 285.0, 230.0, 291.0)}]
    gfr.assign_run_anchors(words, size)
    assert words[0]['anchor'] == words[1]['anchor'] != words[2]['anchor']
    assert gfr.starts_new_run(126.0, 190.0, size) and not gfr.starts_new_run(104.0, 106.0, size)

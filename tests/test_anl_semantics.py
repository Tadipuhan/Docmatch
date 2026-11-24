"""Kesetaraan nilai ANL: layout rujukan berbeda tetap bisa dibandingkan pada nilai yang sama."""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import anl_semantics as s  # noqa: E402


def test_parse_number_locales():
    assert s.parse_number('17,800.000') == Decimal('17800.000')
    assert s.parse_number('4911.650') == Decimal('4911.650')        # desimal titik, bukan ribuan
    assert s.parse_number('1.234.567') == Decimal('1234567')
    assert s.parse_number('17.800,5') == Decimal('17800.5')
    assert s.parse_number('17,800') == Decimal('17800')
    assert s.parse_number('ABC') is None


def test_weight_letter_vs_form_columns():
    letter = '17,800.000 KGS / 100.500 CBM'
    form = '17800.000 6800 100.500'                                   # gross tare measurement
    assert s.fields_equal('Weight & Measurement', letter, form) is True
    assert s.fields_equal('Weight & Measurement', letter, '17800.001 6800 100.500') is False
    assert s.fields_equal('Weight & Measurement', letter, '17800.000 6800 100.501') is False


def test_weight_only_common_parts_are_compared():
    # surat tanpa tare: tare formulir tidak boleh membuatnya berbeda
    assert s.fields_equal('Weight & Measurement', '8455.454 KGS', '8455.454 3700 72.604') is True
    assert s.fields_equal('Weight & Measurement', '8455.454 KGS', '8455.000 3700 72.604') is False
    assert s.fields_equal('Weight & Measurement', 'tidak ada angka', '8455.454 3700 72.604') is None


def test_containers_and_seals():
    form = 'CAAU8541905 SEAL M2856222 ECMU5593288 SEAL M2853517'
    assert s.fields_equal('Container & Seal', 'CAAU8541905 / SEAL-M2856222; ECMU5593288 / SEAL M2853517', form) is True
    assert s.fields_equal('Container & Seal', 'ECMU5593288 SEAL M2853517 CAAU8541905 SEAL M2856222', form) is True  # urutan bebas
    assert s.fields_equal('Container & Seal', 'CAAU8541905 / SEAL-M2856222', form) is False    # kontainer kurang
    assert s.fields_equal('Container & Seal', 'CAAU8541905 SEAL X1; ECMU5593288 SEAL X2', form) is False  # seal beda
    assert s.fields_equal('Container & Seal', 'CAAU8541905; ECMU5593288', form) is True       # surat tanpa seal
    assert s.fields_equal('Container & Seal', 'tanpa nomor', form) is None


def test_place_and_date_formats():
    assert s.parse_place_date('JAKARTA / 19 NOV 2026') == ('jakarta', date(2026, 11, 19))
    assert s.parse_place_date('JAKARTA 19-NOV-2026')[1] == date(2026, 11, 19)
    assert s.parse_place_date('Jakarta, 19/11/2026')[1] == date(2026, 11, 19)
    assert s.parse_place_date('2026-11-19 JAKARTA') == ('jakarta', date(2026, 11, 19))
    assert s.fields_equal('Place & Date of Issue', 'JAKARTA / 21 OCT 2026', 'JAKARTA 21 OCT 2026') is True
    assert s.fields_equal('Place & Date of Issue', 'JAKARTA / 21 OCT 2026', 'JAKARTA 22 OCT 2026') is False
    assert s.fields_equal('Place & Date of Issue', 'JAKARTA / 21 OCT 2026', 'SURABAYA 21 OCT 2026') is False
    assert s.fields_equal('Place & Date of Issue', 'JAKARTA', 'JAKARTA 21 OCT 2026') is None  # tanggal tak ada


def test_original_waybill_count():
    assert s.fields_equal('Number of Original Waybills', '0', 'ZERO (0)') is True
    assert s.fields_equal('Number of Original Waybills', 'ZERO', 'ZERO (0)') is True
    assert s.fields_equal('Number of Original Waybills', '3', 'ZERO (0)') is False


def test_other_fields_use_plain_text_comparison():
    assert s.fields_equal('Port of Loading', 'JAKARTA', 'JAKARTA') is None
    assert s.fields_equal('Shipper', 'A', 'B') is None

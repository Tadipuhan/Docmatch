"""Dekode Type3 GSL harus sama dengan teks yang TERLIHAT pada PDF.

Teks harapan ditranskripsi dari tampilan visual kedua PDF sampel.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
pytest.importorskip('pypdf')
import samples  # noqa: E402

EXPECTED = {
    ('gsl_a', 0): [
        'PT. BRIDGESTONE TIRE INDONESIA', 'KAWASAN INDUSTRI SURYACIPTA,',
        'JL. SURYA UTAMA KAV. 8-13,', 'KEL. KUTAMEKAR, KEC. CIAMPEL,', 'KAB. KARAWANG,*',
        'BRIDGESTONE TIRE SALES KOREA LTD.', '12TH FLOOR, GS TOWER 508,',
        'NONHYEON-RO, GANGNAM-GU', 'SEOUL 135-985, KOREA**',
        'HANEXPRESS CO.,LTD (BUSAN)', 'RM503, EUNSANBAY B/D,88,', 'JUNGANG-DAERO, JUNG-GU,',
        'BUSAN, KOREA***', 'SHIPPED ON BOARD 24/09/2026', 'INTERASIA ENGAGE N044',
        'JAKARTA, INDONESIA', 'BUSAN, KOREA', 'AS PER ATTACHED LIST', 'CLAUSES AS PER ATT.LIST',
        'SINGAPORE', 'JAKARTA on 24/09/2026', 'GOSUJKT8132504',
    ],
    ('gsl_a', 2): [
        'ATTACHED LIST FOR B/L :', 'INTERASIA ENGAGE', 'JAKARTA, INDONESIA',
        'PORT OF DESTINATION:', 'FINAL DESTINATION:', '568 PIECES', 'BRIDGESTONE BRAND TIRES',
        'INVOICE NO.: 26B92KR1C', 'FREIGHT PREPAID AT SINGAPORE', '*PROP. JAWA BARAT 41363',
        'TAX ID : 001.000.118.8-092.000', 'ON BEHALF OF BRIDGESTONE ASIA', 'PACIFIC PTE. LTD.',
        '**(+82)2-3210-2480', 'ATTN: SANG HUN LEE', '***E-MAIL : BUSANO@HANEX.CO.KR',
        'TEL : +82-70-4398-280', 'CONT:CICU6801071', 'SEAL:A4261326820/HC40 (CY/CY)',
        'TOTAL:', 'FIVE HUNDRED SIXTY-EIGHT PIECES ONLY.', 'PEB : 576662 / 11-09-2026',
        'SHIPPER HEREBY IRREVOCABLY SURRENDERS ITS', 'BILL OF LADING TO PT. BRIDGESTONE TIRE',
        'HTTPS://WWW.GOLDSTARLINE.COM/#/WBL', 'SEAWAY B/L - NO ORIGINAL ISSUED',
    ],
    ('gsl_b', 0): [
        'BRIDGESTONE TIRE SALES VIETNAM LLC', '9TH FLOOR,', '233 DONG KHOI STREET,',
        'SAI GON WARD,', 'HO CHI MINH CITY, VIETNAM.**', 'YUSEN LOGISTICS (VIETNAM) CO., LTD.',
        'HOCHIMINH BRANCH', '2A-4A TON DUC THANG ST,', 'Sai Gon Ward,', 'HOCHIMINH CITY***',
        'MTT SENARI 046W', 'TAN CANG HIEP PHUOC PORT',
        'CAT LAI TERMINAL - HO CHI MINH CITY', 'GOSUJKT8133061',
    ],
    ('gsl_b', 2): [
        '2,372 PIECES', 'MADE IN INDONESIA', 'INVOICE NO.: 26BX2VN1B', 'ON BEHALF OF THAI-MC',
        'COMPANY LIMITED', '**TAX ID:0309875328', 'MS.TRAN THI HAI PHUONG/', 'MS. DO MY HA',
        'EMAIL:PHUONG.TRAN', '@BRIDGESTONE.COM', 'HA.DO@BRIDGESTONE.COM', 'TEL:84-908982466',
        'FAX:84-8-38256088', '***TAX ID: 0101936701002', 'MR. NGUYEN VAN HUNG',
        'YLVN.ML.S.CC.BSTVN', '@VN.YUSEN-LOGISTICS.COM', 'TEL: +84-28-3822-4407',
        'FAX: +84-28-3822-4408', 'CONT:JXLU6141346', 'SEAL:A4261328351/HC40 (CY/CY)',
        'CONT:JXLU6275279', 'CONT:TCKU7154523',
        'TOTAL:', 'TWO THOUSAND THREE HUNDRED SEVENTY-TWO PIECES ONLY.',
        'peb : 639772 / 08-10-2026', 'SEAWAY B/L - NO ORIGINAL ISSUED',
    ],
}


@pytest.mark.parametrize('key,page', sorted(EXPECTED))
def test_visible_text_is_decoded(key, page):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    lines = samples.pypdf_page_text(path, page)
    joined = '\n'.join(lines)
    missing = [t for t in EXPECTED[(key, page)] if t not in joined]
    assert not missing, 'Teks tidak terdekode benar: %s' % missing


@pytest.mark.parametrize('key,page', sorted(EXPECTED))
def test_no_replacement_chars(key, page):
    path = samples.sample(key)
    if not path:
        pytest.skip('PDF sampel tidak tersedia')
    bad = [l for l in samples.pypdf_page_text(path, page) if '\ufffd' in l]
    assert not bad, 'Glyph tak dikenal: %s' % bad[:5]

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from region_guard import check_ocr_relevance  # noqa: E402

NATIVE = {
    'Notify Party': 'HANEXPRESS CO.,LTD (BUSAN) RM503, EUNSANBAY B/D,88, JUNGANG-DAERO, JUNG-GU, BUSAN, KOREA***',
    'Main - Clauses': 'CLAUSES AS PER ATT.LIST',
    'Main - Cargo Description': 'AS PER ATTACHED LIST',
    'Consignee': 'BRIDGESTONE TIRE SALES KOREA LTD. 12TH FLOOR, GS TOWER 508',
}


def test_accepts_ocr_from_correct_region():
    ok, why = check_ocr_relevance('Notify Party', 'HANEXPRESS CO.,LTD BUSAN RM503 EUNSANBAY', NATIVE)
    assert ok and why == ''


def test_rejects_ocr_that_read_another_field():
    """Kasus v1.8.29: OCR untuk Notify Party membaca Clauses."""
    ok, why = check_ocr_relevance('Notify Party', 'CLAUSES AS PER ATT LIST', NATIVE)
    assert not ok and 'Main - Clauses' in why


def test_cannot_judge_without_native_text():
    assert check_ocr_relevance('Notify Party', 'APA SAJA DI SINI', {})[0]
    assert check_ocr_relevance('Notify Party', 'APA SAJA', {'Notify Party': ''})[0]


def test_uncertain_ocr_is_not_rejected_without_evidence():
    ok, _ = check_ocr_relevance('Notify Party', 'XQZT LMNP WRVB', NATIVE)
    assert ok

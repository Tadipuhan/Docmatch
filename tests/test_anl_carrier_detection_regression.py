"""ANL/CNC carrier forms must not be confused with flexible letters.

Uses a *synthetic* approximation of the identifying captions. Real GUI/PDF
layout acceptance still requires a genuine ANL/CNC/CMA CGM sample.
"""
from pathlib import Path
import sys
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from flexible_reference import detect_flexible_pdf,extract_flexible
from waybill_rules import profile_field_names

FIELDS=set(profile_field_names('waybill_anl'))

def _pdf(path, texts):
    doc=fitz.open();page=doc.new_page(width=595,height=842)
    for i,t in enumerate(texts):
        page.insert_text((25,40+i*28),t,fontsize=9)
    doc.save(path);doc.close()

def test_anl_form_with_carrier_detected_as_form(tmp_path):
    p=tmp_path/'anl.pdf'
    _pdf(p,[
        'DRAFT WAYBILL NON NEGOTIABLE',
        'CARRIER: ANL Singapore Pte. Ltd.',
        'Shipper', 'Consignee', 'Notify Party',
        'Number of Original Waybills', 'Freight To Be Paid At',
        'Vessel', 'Port of Loading', 'Port of Discharge',
        'Final Place of Delivery', 'Marks and Seals',
    ])
    assert not detect_flexible_pdf(p,FIELDS)

def test_letter_mentioning_anl_remains_flexible(tmp_path):
    p=tmp_path/'letter.pdf'
    _pdf(p,['SURAT KONFIRMASI PENGIRIMAN - ANL',
            'Waybill Number: ANL-TEST-2026',
            'Port of Loading: JAKARTA, INDONESIA',
            'Port of Discharge: TOKYO, JAPAN'])
    assert detect_flexible_pdf(p,FIELDS)
    data=extract_flexible(p,FIELDS)
    assert data['Waybill Number']['text']=='ANL-TEST-2026'
    assert data['Port of Loading']['text']=='JAKARTA, INDONESIA'

def test_anl_reference_test_kit_labels(tmp_path):
    from zipfile import ZipFile
    kit=Path('/mnt/data/DocMatch_Universal_Reference_Test_14_Surat.zip')
    if not kit.exists():return
    with ZipFile(kit) as z:
        for name in ('ANL_CNC_CMA_A_Surat_Naratif.pdf','ANL_CNC_CMA_B_Tabel_Konfirmasi.pdf'):
            p=tmp_path/name;p.write_bytes(z.read(name))
            assert detect_flexible_pdf(p,FIELDS)
            data=extract_flexible(p,FIELDS)
            assert sum(bool(data[f]['valid']) for f in FIELDS)==13

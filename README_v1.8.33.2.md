# DocMatch v1.8.33.2 — Presisi nilai & kotak SWB ANL/CNC/CMA CGM

## Menjalankan / menguji
`py docmatch.py` · `python tests\run_tests.py` (atau `pytest tests`).
Tes ANL membaca PDF contoh yang TIDAK dibundel: letakkan di folder `samples\` (atau set `DOCMATCH_SAMPLES`):
`ANL_DRAFT_SWB_26BX3AL1A.pdf`, `ANL_SWB_26B63EM4__DRAFT_.pdf`, `CNC_SWB_26B92HK1__FINAL_.pdf`
(+ GSL untuk tes GSL). Tanpa file itu tes terkait dilewati. Surat uji sintetis ada di `tests\fixtures\`.

## Hasil yang diharapkan pada formulir ANL 26BX3AL1A (Tahap 1)
Voyage Number `0SQ5AN` · Waybill Number `KTJ0315847` · Vessel `BANGKOK` · Port of Loading
`JAKARTA, INDONESIA` · Port of Discharge `FREMANTLE, AUSTRALIA` · Weight (total) `24209.468 10830 215.386` ·
Place & Date of Issue `JAKARTA 21 OCT 2026` — tanpa kata caption. Surat uji A/B vs formulir ini: 12 selisih sah
(Port of Loading cocok), 5 field Perlu Verifikasi (tidak ada pada surat).

## Status pengujian (jujur)
DIUJI (42 tes ANL + 39 tes regresi GSL lulus, di lingkungan TANPA PyMuPDF/PySide6, memakai pengganti tipis
berbasis pdfplumber untuk PDF berlapis teks): nilai tiap field pada 3 formulir; batas kotak tiap kata;
tidak ada caption/footer di nilai; tidak ada kata milik dua field; klausa dua kolom; kesetaraan nilai;
surat rujukan naratif & tabel (sama nilai -> nol selisih; satu nilai diubah -> hanya field itu);
penanda hanya pada kata yang berubah. Overlay visual kotak sebelum/sesudah diperiksa pada render halaman.
BELUM DIUJI — mohon dicek di Windows dengan PyMuPDF sungguhan:
- Geometri kata PyMuPDF (tinggi kotak sedikit berbeda dari pengganti uji; batas y memakai margin ~3 pt).
- GUI, Tahap 2, ekspor, sesi; formulir CMA CGM yang berbeda dari ANL/CNC; PDF hasil scan.

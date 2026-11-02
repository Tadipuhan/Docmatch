DocMatch v0.7 — update source code (BUKAN patch EXE)

1. Backup docmatch.py lama.
2. Salin docmatch.py dan waybill_rules.py ke folder proyek DocMatch.
3. Pertahankan legacy_v01.py, rules.py, editor.py, portable_runtime.py dan requirements lama.
4. Jalankan dari virtual environment: python docmatch.py
5. Untuk dist/DocMatch.exe: build ulang di komputer pengembang. Menyalin .py ke dist tidak memperbarui EXE.

Mode Waybill:
- Pilih 'Waybill (preset field)' pada Mode parameter.
- Klik 'Atur Field Waybill...' untuk memilih 13 field.
- Bandingkan dua PDF (DOCX/DOC dikonversi bila tersedia LibreOffice).
- Daftar ketidaksesuaian diurutkan menurut posisi penanda halaman.
- Anotasi Waybill menggunakan area field pada template ANL (bukan per kata).
- Ekspor koreksi DOCX/PDF dinonaktifkan pada mode Waybill demi mencegah korupsi tata letak; laporan JSON tersedia.
- Area field dapat mengandung label dan isi field bersebelahan. Periksa hasil secara manual.
- 'Additional Clauses' menggunakan area bawah tiap halaman; belum menangkap seluruh variasi template.
- Nomor halaman dan urutan di mode umum bersifat best-effort bila teks tidak ditemukan.

Pengujian: sintaks Python dan ekstraksi field PDF contoh telah diperiksa; GUI PySide6 dan pasangan PDF rujukan belum diuji secara end-to-end.

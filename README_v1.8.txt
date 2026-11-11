DocMatch v1.8 - FULL OCR PER FIELD GSL (PERC0BAAN)

Perubahan:
- SWB - Golden Star Line sekarang memakai Tesseract OCR sebagai SUMBER UTAMA semua field, tidak lagi mengutamakan font Type3.
- OCR dilakukan pada halaman 1 dan halaman 3 PDF; halaman kosong tidak diproses.
- Empat nilai Attached List diperiksa dalam kotak khusus: Cargo Quantity, Container Count, Gross Weight, Measurement.
- Koordinat kata OCR dipakai untuk penanda PDF.
- Field yang tidak valid tetap dilewati dan dilaporkan.
- ANL dan Evergreen tidak diubah.

PENTING: ini BUILD KIT, bukan exe. Salin rules.py dari proyek lama.
Folder tesseract harus berisi tesseract.exe dan tessdata/eng.traineddata beserta DLL pendukung.
Jalankan build_portable.bat pada Windows. Salin SELURUH folder dist/DocMatch.
Periksa judul jendela 'DocMatch v1.8' dan status 'Full OCR GSL aktif'.
Jika masih v1.7, berarti executable lama yang sedang dijalankan.

Pengujian Linux terhadap dua PDF GSL contoh:
- Cargo Quantity: 568 vs 2,372
- Container Count: 1 vs 3
- Gross Weight: 7,677.67 vs 23,238.42
- Measurement: 70.41 vs 216.821
- Sebagian teks OCR lain masih menghasilkan temuan berlebih atau salah dan WAJIB diperiksa manual.
- Pengujian GUI dan build Windows belum dilakukan.

DocMatch v1.7 — Hybrid PDF Text + OCR Offline (GSL only)

Fitur:
- Tetap menggunakan pemulihan font Type3 untuk field GSL yang terbaca.
- Jika gagal, otomatis jalankan Tesseract OCR offline pada halaman GSL, pilih teks berdasarkan kotak field.
- Koordinat OCR dipetakan kembali ke koordinat PDF untuk stabilo.
- Confidence OCR rata-rata <55 dianggap belum tervalidasi.
- Field yang belum tervalidasi tidak dianggap cocok.
- Profil ANL dan Evergreen tidak menggunakan OCR.

Persyaratan:
- Pada komputer developer Windows, siapkan folder tesseract berisi tesseract.exe, dependensi DLL yang dibutuhkan, dan tessdata/eng.traineddata.
- Build portable: jalankan build_portable.bat. Folder tesseract disalin ke dist/DocMatch/_internal/tesseract.
- Jika folder tesseract tidak tersedia, build tetap bisa dibuat, tetapi OCR GSL tidak berfungsi pada komputer tanpa Tesseract.
- File rules.py dari proyek aktif masih dibutuhkan untuk build.
- Tidak ada unduhan otomatis atau penggunaan internet saat runtime.

Penting: OCR tidak menjamin ketepatan angka atau nomor kontainer. Selalu verifikasi hasil temuan dan stabilo sebelum koreksi/ekspor.
Pengujian GUI dan build Windows harus dilakukan di Windows.

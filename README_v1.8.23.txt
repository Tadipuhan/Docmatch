DocMatch v1.8.23 — Smart Region OCR Recovery (offline)

Perubahan:
- Inspector: tombol OCR Ulang Area A/B pada area yang dipilih.
- Native text quality check untuk U+FFFD, karakter kontrol, dan area kosong.
- Kandidat OCR region warna/grayscale pada 350 DPI, PSM 6/7/11.
- Hasil OCR tidak diterapkan otomatis: pengguna memilih kandidat, memeriksa crop, dan menekan Konfirmasi & Perbarui Tahap 1.
- Riwayat OCR alternatif dan kualitas native disimpan pada record JSON.

Persyaratan: Tesseract OCR lokal + eng.traineddata, tersedia dalam PATH atau folder tesseract/ sesuai gsl_ocr.py. Tetap dapat menggunakan koreksi manual jika Tesseract tidak tersedia.

Catatan: OCR hasil scan buram tidak dapat dipastikan akurat; skor OCR bukan probabilitas validasi.
Tahap 1 tetap sebagai baseline audit; hanya hasil aktif yang diubah setelah konfirmasi.

Batasan: belum dilakukan tes interaktif GUI pada Windows. Source kiriman sebelumnya masih tidak mempunyai rules.py.

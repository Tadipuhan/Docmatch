DocMatch v0.9 — Pemilihan Ekspor PDF (patch source)

1. Tutup DocMatch dan backup docmatch.py yang sekarang.
2. Salin docmatch.py dari paket ini ke folder source DocMatch.
3. Pertahankan waybill_rules.py, rules.py, editor.py, legacy_v01.py versi sebelumnya.
4. Jalankan: py docmatch.py

Pada mode Waybill, tombol Ekspor Hasil Pemeriksaan PDF membuka tiga checkbox:
- Dokumen Rujukan Beranotasi
- Dokumen Diperiksa Beranotasi
- Dokumen Hasil Koreksi
Satu pilihan -> PDF; dua atau tiga -> ZIP.

PENTING: Ekspor Hasil Koreksi bersifat konservatif dan terbatas. Hanya temuan jenis
Perubahan yang dicentang/disetujui, berupa penggantian satu token ke satu token,
memiliki satu lokasi yang tervalidasi, dan muat di kotak asli yang dapat diproses.
Jika ada temuan terpilih yang tidak aman, ekspor koreksi DIBATALKAN, bukan diam-diam
menghasilkan PDF yang salah. PDF yang berhasil tetap harus diverifikasi visual.
Tidak mendukung koreksi otomatis multi-kata, teks hilang/berlebih, perubahan tabel
kompleks, maupun pengeditan hasil koreksi langsung di halaman PDF.

Paket ini dibuat berdasarkan DocMatch_v0.8_Export_Dua_PDF_Patch.zip yang tersedia
pada percakapan; jika source lokal sudah berbeda, integrasi perlu diperiksa.
Pemeriksaan sintaks dilakukan. Pengujian GUI Windows belum dilakukan.

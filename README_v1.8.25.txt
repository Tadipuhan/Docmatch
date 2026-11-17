DocMatch v1.8.25 — OCR Otomatis Bertingkat & Temuan Tahap 2
==============================================================
Basis: v1.8.24.

1. Hanya satu tombol OCR Otomatis A + B. Klik parameter tetap menjalankan
   AutoLocate dan OCR dua dokumen dalam worker. OCR awal grayscale PSM 6;
   jika kosong, ada karakter rusak, confidence kurang dari 78, atau native
   mencurigakan, otomatis memakai fallback PSM 11 / 7 dan grayscale / warna.
   Skor confidence merupakan petunjuk, bukan verifikasi kebenaran.
2. Hasil OCR otomatis adalah kandidat dan tidak menimpa data Tahap 1 sampai
   pengguna menekan Konfirmasi & Perbarui Tahap 1.
3. Temuan terkonfirmasi Tahap 2 status MISMATCH atau PERLU_VERIFIKASI
   masuk ke daftar ketidaksesuaian aktif; MATCH menghapus temuan lama.
   Histori tahap 1 asli tetap di baseline untuk audit.
4. Highlight kandidat otomatis dipersempit mengikuti batas kata native
   ketika geometri tepercaya; OCR tetap menggunakan area template penuh
   agar huruf tepi tidak terpotong. Kotak manual tidak diubah.

CATATAN: rules.py masih tidak tersedia di arsip sumber sebelumnya dan
perlu disalin dari instalasi DocMatch yang berfungsi. GUI Windows dan
akurasi OCR pada dokumen asli harus diuji sebelum dipakai produksi.

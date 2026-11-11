DocMatch v1.8.4 — Perbaikan ekspor PDF catatan koreksi GSL

Perubahan:
- Mengukur panjang teks catatan menggunakan metrik font PyMuPDF, bukan perkiraan jumlah karakter.
- Membungkus catatan panjang secara otomatis, termasuk token panjang.
- Memperpanjang area vertikal halaman hasil ekspor jika banyak catatan. PDF asli tetap di kiri tanpa diubah.
- Mempertahankan stabilo, nomor temuan, garis penghubung, serta teks catatan yang sudah diedit.
- Title bar diperbarui ke v1.8.4.

Batasan:
- Halaman hasil ekspor dapat lebih tinggi daripada halaman PDF asli bila jumlah catatan banyak.
- Ekspor PDF catatan tidak mengganti teks asli pada dokumen.
- Validasi GUI dan build Windows portable masih harus dilakukan pada komputer Windows.

Instalasi: cadangkan proyek, ekstrak isi ZIP, pertahankan file konfigurasi lokal yang diperlukan,
lalu build ulang dengan build_portable.bat. Tesseract dan tessdata tetap diperlukan untuk OCR GSL.

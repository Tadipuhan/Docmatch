DocMatch v1.8.28 — Persistent Multi-Parameter Annotations / Export Integration

Perubahan utama:
1. Kotak parameter yang dicentang di Tahap 2 tetap muncul bersamaan pada PDF A dan PDF B, sekalipun parameter aktif berubah.
2. Checkbox Daftar Parameter kini mengatur visibilitas highlight; bukan menghapus hasil validasi.
3. Saat batch halaman pertama menemukan area, koordinat A/B ditambahkan ke kumpulan kotak. Koreksi manual mengungguli kandidat batch.
4. Hasil & Ekspor memiliki daftar parameter bercari dan checkbox. Uncheck langsung menyembunyikan highlight Tahap 2 pada dua preview utama dan mengecualikan highlight tersebut dari PDF beranotasi.
5. Ekspor PDF Rujukan/Diperiksa Beranotasi menggambar overlay vektor sesuai pilihan yang aktif. Koreksi Tahap 2 yang telah dikonfirmasi menambahkan catatan PDF (sticky note) tanpa mengubah konten asli.
6. Koordinat, konfirmasi, dan pilihan checkbox tetap tersedia saat dialog Tahap 2 dibuka kembali dalam sesi yang sama.

Petunjuk:
- Jalankan Tahap 1, lalu Tahap 2. Tunggu batch halaman pertama selesai.
- Centang parameter yang ingin terlihat terus-menerus. Klik parameter untuk mengoreksi kotak A/B; centang dapat dimatikan untuk menyembunyikan kotaknya.
- Pergi ke langkah Hasil & Ekspor. Gunakan kotak pencarian dan checklist Parameter Ekspor untuk mengatur anotasi mana yang terlihat dan diekspor.
- Klik 'Ekspor Hasil Pemeriksaan PDF', pilih Rujukan/Diperiksa Beranotasi (satu atau keduanya).
- Coretan/kotak dan catatan ditempatkan di salinan PDF, bukan PDF asli. Riwayat hasil Tahap 1 tetap tersedia.

Batasan:
- Tampilan GUI Windows belum diuji di lingkungan build ini (PySide6 tidak tersedia).
- PDF 'Koreksi Bersih' mengubah isi tertentu berdasarkan aturan tersendiri; ia tidak dimaksudkan menampilkan overlay pemeriksaan.
- Teks hasil OCR pada region masih perlu dikonfirmasi untuk dianggap koreksi resmi.
- Source ZIP sebelumnya belum mencakup rules.py sehingga runtime aplikasi memerlukan modul tersebut dari instalasi valid.

DocMatch v1.1 - Preview & Edit Catatan Koreksi

Pasang: backup docmatch.py lama, lalu salin docmatch.py ini ke folder proyek v1.0.
File pendukung legacy_v01.py, rules.py, editor.py, waybill_rules.py tetap diperlukan.
Tidak perlu menginstal ulang paket Python bila dependensi v1.0 sudah lengkap.

1. Jalankan perbandingan Waybill seperti biasa.
2. Klik 'Preview & Edit Catatan Koreksi…'.
3. Pilih temuan, edit isi catatan, centang bila ingin ditampilkan.
4. Klik 'Simpan & Ekspor PDF Catatan…' untuk membuat PDF berdasarkan edit terbaru.
5. 'Simpan Catatan JSON…' menyimpan teks edit agar bisa diimpor lagi.
6. 'Impor Catatan JSON…' menerima laporan docmatch_laporan.json atau catatan v1.1.
   Pencocokan memakai nomor, field, dan teks diperiksa; temuan yang tidak cocok dilewati.

CATATAN:
- PDF asal tetap utuh. Catatan dibuat pada margin kanan dan garis menghubungkan stabilo.
- Tidak ada jaminan catatan yang sangat banyak muat pada satu halaman; ekspor akan menolak bila penuh.
- JSON saja tidak mengandung PDF atau koordinat stabilo. Untuk ekspor harus buka kedua PDF dan jalankan pemeriksaan.
- Perubahan editor catatan tidak mengubah PDF Hasil Koreksi Bersih.
- GUI Windows belum diuji di lingkungan ini; pemeriksaan sintaks Python berhasil.

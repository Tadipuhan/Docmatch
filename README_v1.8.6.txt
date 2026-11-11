DocMatch v1.8.6 — Koreksi GSL halaman pertama per field berdasarkan rujukan

- Satu kotak catatan dan satu garis per field per halaman.
- Untuk GSL halaman pertama, catatan default memuat isi OCR lengkap dari field rujukan dan rincian perubahan token.
- Menghindari label formulir yang ikut dianggap data dengan penyaringan label pada baris atas.
- Hasil OCR yang tidak tervalidasi tidak digunakan untuk membuat koreksi otomatis.
- Edit kotak catatan di Preview Edit Catatan Koreksi sebelum ekspor untuk memverifikasi hasil OCR.
- Field halaman ketiga dan profil lain tidak mengubah format catatan default.
- Penting: catatan PDF tidak mengubah teks PDF asli.
- Source ini memerlukan rules.py dari proyek aktif (tidak terdapat dalam paket v1.8.5).
- Build Windows dan uji end-to-end GUI belum dijalankan.

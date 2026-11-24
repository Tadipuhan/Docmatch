# Changelog v1.8.35.6 — Reference Cargo & Weight Formatting

- Melanjutkan aturan format Catatan Koreksi v1.8.35.5 untuk **Container & Seal, Cargo Description, Weight & Measurement** dan variasi nama field yang digunakan profil carrier.
- Mengambil nilai lengkap dari dokumen rujukan (PDF A) memakai koordinat ekstraksi independen dan membangun ulang baris yang sejajar (misalnya nomor container dan nomor seal pada kolom bersebelahan).
- Mempertahankan kapitalisasi, tanda baca, pemisah desimal, satuan, spasi yang tersedia pada PDF, serta urutan baris multi-container/multi-cargo.
- Menolak override otomatis saat hasil sumber invalid/kosong atau terkontaminasi teks kolom lain secara jelas.
- Mempertahankan prioritas catatan edit manual dan output format ekspor PDF yang telah ada.
- Tidak mengubah layout UI, penanda, logika matching, profil SWB, maupun mesin OCR.
- Menambahkan pengujian ekstraksi rujukan dan ekspor PDF khusus format cargo/weight.

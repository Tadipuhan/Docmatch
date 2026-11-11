DocMatch v1.6 — GSL Type3 font recovery (offline, tanpa OCR)

Perubahan:
- Memulihkan sebagian teks Golden Star Line dari outline glyph Type3, bukan OCR.
- Pemetaan hanya menerima glyph yang sudah diverifikasi terhadap contoh GSL.
- Koreksi batas kotak GSL untuk Shipper, Booking Number, Waybill Number,
  Vessel, Voyage Number, Port of Loading.
- Field yang mengandung karakter belum dipetakan / kosong TIDAK dibandingkan.
  Aplikasi menampilkan PERINGATAN daftar field yang dilewati.
- Stabilo tetap menggunakan koordinat glyph PDF asli.
- Preset ANL dan Evergreen tidak diubah.

Pengujian pada dua PDF GSL yang diserahkan:
- Pemulihan untuk Booking Number, Waybill Number, Vessel, Voyage Number,
  Consignee, Shipper, Port of Loading, Port of Discharge berjalan.
- Attached List, Cargo Description, Notify Party, Weight & Measurement,
  Place & Date of Issue, Additional Clauses, Container & Seal masih belum
  dijamin; aplikasi melewati field yang tidak tervalidasi.
- Jangan menganggap nol temuan pada field yang dilewati sebagai kesesuaian.
- Tidak ada OCR; tidak ada koneksi internet.

Pemasangan source:
1. Backup file sebelumnya.
2. Salin docmatch.py, waybill_rules.py, gsl_font_recovery.py, dan folder assets.
3. Pertahankan rules.py Anda dari proyek yang sudah berjalan.
4. Jalankan py docmatch.py.

Build portable:
1. Salin rules.py ke folder build kit ini.
2. Jalankan build_portable.bat pada Windows.
3. Salin SELURUH folder dist/DocMatch ke komputer target.

Batasan:
- Pemulihan berlaku pada glyph yang memiliki outline sama dengan dua sampel
  GSL yang disediakan; template/font baru mungkin tidak dapat dipulihkan.
- Hasil GUI dan executable Windows belum diuji pada komputer target.

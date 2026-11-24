# Changelog v1.8.35.3

**Base:** v1.8.35.2 — Export PDF Catatan Filename.

### Fixed
- Badge nomor pada Hasil Koreksi tidak lagi selalu dipaksa berada persis di kiri highlight, sehingga `#04` / `#05-#10` tidak menutupi karakter di Quantity, Cargo Description, atau field tetangga.
- Penempatan mempertimbangkan teks PDF asli, highlight, serta badge-badge lain di halaman yang sama.
- Pencarian posisi kosong yang deterministik, dengan pengecekan piksel pada formulir yang sulit diekstrak, menjaga kesesuaian preview dan ekspor.

### Unchanged
- Catatan Koreksi tetap menggunakan editor inline dari v1.8.34.
- Tanpa garis, tanpa penggantian mesin ekstraksi/OCR carrier.
- Default nama ekspor `Koreksi_[Nama Dokumen Diperiksa].pdf`.

### Testing
- 5 tes tambahan, termasuk tabel padat, tepi halaman, ruang tidak tersedia, piksel PDF, dan integrasi penulis PDF.
- Satu tes Meratus lama tetap gagal seperti di v1.8.35.2; bukan regresi baru.
- GUI Windows belum diuji langsung.

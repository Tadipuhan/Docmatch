DocMatch v1.8.16 — Kembali ke stabilo transparan GSL

- Ekspor PDF catatan GSL kini memakai stabilo token yang sama dengan viewer, bukan kotak merah field.
- Garis satu per field ditautkan ke salah satu rectangle temuan aktual, bukan outline hasil perkiraan.
- Hanya temuan yang dipilih untuk koreksi yang digambar di ekspor.
- Validasi rectangle dan penanganan error v1.8.15 dipertahankan.

BATASAN: Patch ini mengubah visualisasi ekspor, bukan algoritme deteksi/OCR.
Jika Consignee tidak terdeteksi pada daftar temuan, patch ini tidak dapat memunculkannya.

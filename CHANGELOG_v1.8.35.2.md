# DocMatch v1.8.35.2 — Nama Berkas Ekspor PDF Catatan

Perubahan terbatas pada nama default saat memilih **Ekspor PDF Catatan**.

- Nama otomatis menggunakan `Koreksi_[Nama Dokumen Diperiksa].pdf` (ekstensi asli dihilangkan).
- Berlaku untuk preview Tab 3, editor PDF catatan, editor daftar catatan, serta ekspor `notes` melalui ribbon, termasuk nama PDF di dalam ZIP gabungan.
- Pengguna tetap bisa mengganti nama dan folder melalui dialog Simpan Sebagai.
- Tidak mengubah highlight, nomor penanda, isi catatan, pembacaan SWB, validasi, atau rendering PDF.
- Bila belum ada dokumen diperiksa, fallback nama `Koreksi_Dokumen_Diperiksa.pdf`.

Contoh: `MSC_SWB_26BX8ZA1 (DRAFT).pdf` menjadi `Koreksi_MSC_SWB_26BX8ZA1 (DRAFT).pdf`.

Pengujian GUI Windows tetap diperlukan pada PC pengguna.

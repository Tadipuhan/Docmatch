# DocMatch v1.8.30.2 — Parameter & Comparison Merge

Basis: DocMatch v1.8.30.1.

## Perubahan
- Alur wizard dipersingkat dari empat menjadi tiga langkah: Pilih Dokumen, Atur Parameter & Bandingkan, Hasil & Ekspor.
- Pengaturan mode, field, cakupan, dan tombol **Bandingkan Dokumen** berada dalam satu langkah.
- Setelah perbandingan selesai atau sesi dipulihkan, aplikasi membuka Hasil & Ekspor (langkah 3).
- Tombol kembali Hasil & Ekspor menuju Atur Parameter & Bandingkan.
- Ribbon, dual PDF viewer, anotasi, ekspor, dan mesin perbandingan dipertahankan.

## Validasi
- Pemeriksaan AST dan kompilasi Python lulus.
- Pengujian unit `tests/test_core.py`: 5 lulus.
- Pengujian GUI Windows belum dilakukan (PySide6 tidak tersedia di lingkungan pengujian).

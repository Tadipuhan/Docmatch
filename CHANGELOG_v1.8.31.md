# DocMatch v1.8.31 — Precision Integration (17 November 2026)

## Dasar penggabungan
- **Layout/UI:** DocMatch v1.8.30.10_Compact_Flexible_Layout (dipertahankan).
- **Mesin akurasi:** DocMatch v1.8.30.9_r2 yang diberikan pengguna (hasil perbaikan Claude).

## Modul akurasi dari versi r2
- `gsl_font_recovery.py`: decoder Type3 berbasis bentuk glyph dengan penanganan karakter tidak dikenal dan bounding box yang lebih rapat.
- `gsl_glyph_table.py`: tabel hash glyph untuk GSL (termasuk tanda baca dan huruf kecil yang terverifikasi dalam source r2).
- `gsl_layout.py`: koordinat cell GSL mengikuti garis formulir serta penyesuaian region.
- `waybill_rules.py`: integrasi pembacaan GSL, pemetaan ANL/CNC dan pembandingan per field/penanda kata berbeda.
- `hybrid_validation.py`: OCR pada region nilai dan pemeriksaan relevansi kandidat sebelum digunakan pada validasi tahap kedua.
- `region_guard.py`, `textnorm.py`: pemeriksaan relevansi OCR dan normalisasi teks.
- Tes akurasi dari source r2 ditambahkan ke `tests/`.

## Yang tidak diambil dari r2
- `docmatch.py` berbasis UI lama, karena akan menghilangkan responsive splitter, checkbox induk, serta layout ringkas dari v1.8.30.10.
- Perubahan panel, ribbon, dan penempatan tombol lama pada `hybrid_validation.py` tidak ada pada diff r2; file ini hanya berbeda pada jalur ekstraksi/validasi.

## Validasi paket
- 30 passed; 30 skipped (fixture/dependensi uji khusus yang tidak tersedia).
- Perbandingan diri-sendiri untuk ONE, MAERSK, MERATUS, MSC: 0 temuan.
- Sintaks Python diperiksa.
- **Belum diuji secara GUI Windows** dan **GSL end-to-end belum diulang** karena PDF GSL fixture tidak ada dalam kedua ZIP.
- Source PDF asli tidak disertakan atau dimodifikasi.

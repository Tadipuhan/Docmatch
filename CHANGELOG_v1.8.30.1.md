# DocMatch v1.8.30.1 — Word-Style Review Workspace

## Perubahan
- Menu Simpan Sesi, Buka Sesi, dan Template/Alias tetap disembunyikan dari tampilan utama (fitur internal v1.8.30 dipertahankan).
- Aksi Hasil & Ekspor dipindahkan ke toolbar kontekstual bergaya ribbon dalam dua kelompok: VALIDASI dan EKSPOR LAPORAN.
- Tombol toolbar menggunakan label ringkas dengan tooltip deskriptif. Toolbar hanya muncul pada langkah ke-4.
- Daftar Ketidaksesuaian Tahap 1 dan Penanda Tahap 2 tetap di panel kanan.
- Dua viewer PDF dikelompokkan di splitter bagian dokumen (awal 50:50), dengan panel kanan terpisah.
- Mode Lebar pada masing-masing viewer menyesuaikan zoom terhadap lebar panel PDF secara otomatis ketika panel diubah ukurannya. Tombol +/- mematikan mode fit sementara; tombol Lebar mengaktifkannya lagi.
- Area preview menggunakan latar abu-abu dan halaman putih berpembatas; rendering HiDPI 2x dan anotasi lama tetap dipertahankan.
- Ekspor DOCX/PDF/JSON memakai implementasi v1.8.30 sebelumnya, tanpa perubahan pada aturan pembanding.

## Pemeriksaan
- `python -m compileall -q .`: lolos.
- `python -m pytest tests/test_core.py -q`: 5 lulus.
- Pengujian GUI PySide6 Windows tidak tersedia di lingkungan pembuat; perlu diuji di perangkat pengguna.

## Batasan
- Tampilan meniru pola ribbon/halaman Word, **bukan** editor DOCX atau implementasi Microsoft Word.
- PDF scan beresolusi rendah tidak bisa otomatis dipulihkan detailnya hanya lewat layout dan HiDPI.

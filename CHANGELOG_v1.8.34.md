# v1.8.34 — In-place Correction Notes

- Perbandingan tidak lagi berpindah otomatis ke Langkah 3.
- Langkah 3 menjadi satu dokumen hasil koreksi dengan kolom Catatan Koreksi yang dapat diedit pada halaman.
- Shared geometry `correction_note_layout.py` memastikan preview dan ekspor PDF memakai koordinat yang sama.
- `CorrectionPreview` dibangun sebagai QWidget di dalam workspace, dengan fit-width/zoom/halaman dan editor teks per field.
- Perubahan catatan tersimpan langsung ke `note_overrides` dan autosave sesi.
- Ekspor PDF dari preview memakai pilihan temuan yang sama, termasuk opsi tampilkan semua.
- Tetap menyediakan Validasi Tahap 2 dalam Panel Pemeriksaan di Langkah 2.
- Jalur ekstraksi carrier tidak diubah.

# Changelog — v1.8.36.3

## Added / Changed
- Switch Sama: ON kini mengisi **Tahap 1 dan Tahap 2** dengan field yang cocok, bukan hanya mengubah stabilo PDF.
- Switch Sama: OFF kembali ke **dua daftar perbedaan**, termasuk anotasi Tahap 2 yang telah dibuat.
- Nilai lengkap pasangan PDF A/B dan nomor halaman kecocokan dipertahankan untuk navigasi dan sesi.
- Daftar nilai sama bersifat read-only, tanpa pemilihan koreksi atau nomor temuan palsu.
- Field dengan hasil Stage-2 mismatch/perlu verifikasi disembunyikan dari daftar nilai sama.
- Pencarian Tahap 2 dibersihkan saat mode berganti; kategori filter perbedaan Tahap 1 dipulihkan ketika OFF.
- Match green overlay tidak terpengaruh checkbox visibilitas anotasi Tahap 2 yang khusus koreksi.
- Bandingkan ulang ketika switch ON mengisi ulang panel nilai sama segera.

## Preserved
- Seluruh profile SWB, Cross-Carrier, referensi SWB / PL+SI, OCR opsional, Catatan Koreksi dan ekspor, sesi kompatibel ke belakang.
- Build portable otomatis ZIP/7z dan struktur file, tidak ada dependensi besar tambahan.

## Testing
- Pengujian alur switch, kedua panel, nilai lokasi, penghindaran perubahan checkbox, dan sesi.
- Pengujian lintas dokumen 26YA1A: 11 field cocok, 1 field berbeda.
- Kegagalan referensi Vessel Meratus sudah ada pada rilis sebelumnya.
- GUI Windows/EXE belum diuji langsung.

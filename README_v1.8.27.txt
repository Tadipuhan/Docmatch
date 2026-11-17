DocMatch v1.8.27 — Page-One Batch Verification + Bidirectional Rectangle Sync

Basis: v1.8.26.

PERUBAHAN
1. Saat dialog Tahap 2 dibuka, otomatis mengantre semua parameter yang memiliki region template di halaman pertama (GSL: 20 parameter). Analisis dilakukan serial via worker agar tidak membekukan UI. Progress batch ditampilkan di panel kanan.
2. Hasil deteksi dua area + OCR kandidat ditahan di cache. Klik parameter yang sudah selesai akan menampilkan hasil tanpa OCR ulang.
3. Tombol 'Koordinat sinkron A ⇄ B' aktif secara default. Seleksi, drag, move, dan resize (preview langsung selama mouse bergerak) yang selesai di A/B memindahkan pasangan kotak ke posisi relatif sama pada halaman berindeks sama di PDF lain. Ketika PDF berukuran berbeda, posisi dinormalisasi menurut lebar/tinggi halaman. Bila tata letak dokumen berbeda, NONAKTIFKAN mode sinkron dan gunakan pencarian kandidat sesuai parameter.
4. Mirror tidak langsung dikonfirmasi: status 'mirrored_unverified' dan prompt pengecekan visual sebelum promosi nilai ke hasil Tahap 1.
5. Analisis massal tidak menyetujui hasil dan tidak mengubah Tahap 1 otomatis. Konfirmasi koreksi tetap diperlukan.

CATATAN
- Batch dilakukan untuk area yang terdefinisi di halaman pertama (GSL=20). Semua area masih perlu dipastikan secara visual, termasuk batas tabel/caption.
- OCR dapat membutuhkan waktu cukup lama pada CPU i5 dan 8 GB RAM; pemrosesan dibuat berurutan. Status progress memberi indikasi pekerjaan yang selesai.
- ZIP mengikuti source dasar dan belum menyertakan rules.py yang dibutuhkan aplikasi utama. Ambil dari instalasi DocMatch lengkap yang sebelumnya berjalan.
- PySide6 tidak tersedia di lingkungan pengemasan, sehingga GUI Windows belum diuji. Pemeriksaan sintaks dan test koordinat terpisah telah dilakukan.

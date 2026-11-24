# DocMatch v1.8.35.9 — Fix Header Tab 2 (Cross-Carrier)

## Masalah

Setelah penambahan pilihan **Profil Dokumen A (rujukan)** pada v1.8.35.8, Tab 2 memiliki dua baris kontrol. `QStackedWidget` sebelumnya dibatasi dengan `setMaximumHeight(58)`, yang hanya cocok untuk satu baris. Pada beberapa resolusi/DPI, kontrol mode parameter, tombol Bandingkan, dan pilihan profil rujukan terpotong secara vertikal; sering terlihat setelah klik **Bandingkan**.

## Perubahan

1. Menghapus batas maksimum 58 px pada `wizard_stack`.
2. Menetapkan kebijakan ukuran vertikal `Fixed`, lalu mengukur tinggi dari `sizeHint()` halaman yang sedang aktif.
3. Memakai tinggi minimum 86 px untuk Tab 2 saat baris profil rujukan ditampilkan dan menaikkan tinggi jika DPI/font membutuhkan ruang tambahan.
4. Menghitung kembali tinggi saat berpindah tahap, mengganti mode SWB/non-SWB, dan setelah stylesheet Qt diterapkan.
5. Mempertahankan Tab 1 yang ringkas dan menyembunyikan toolbar wizard pada Tab 3 seperti sebelumnya.
6. Memperbarui judul jendela/status menjadi versi v1.8.35.9.

## Tidak diubah

- Deteksi profil rujukan PDF A dan PDF B secara independen dari v1.8.35.8.
- Mesin pembanding, ekstraksi PDF, OCR, Catatan Koreksi, marker, ekspor PDF/DOCX/JSON.
- `build_portable.bat` dan `pack_portable.py`: ZIP / 7z otomatis tetap tersedia.

## Validasi

- 5 tes khusus layout header lulus (ukuran dua baris, skala font, Tab 1 ringkas, recalculation, dan pengecekan konfigurasi).
- Total regresi: **125 lulus, 59 dilewati, 1 gagal**. Kegagalan lama berhubungan dengan ekstraksi Vessel dari surat rujukan Meratus, bukan perubahan layout.
- Sintaks Python tervalidasi. Qt GUI Windows/portable EXE **belum dijalankan** pada lingkungan pengujian ini; lakukan smoke test setelah rebuild.

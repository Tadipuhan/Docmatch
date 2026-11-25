# DocMatch v1.8.36.5 — Exclusive Same/Different Markers

## Perbaikan utama

- Switch **Sama: ON** kini benar-benar memfilter kedua PDF viewer dan kedua panel Tahap 1/Tahap 2: **hanya nilai yang terbukti sama** yang ditampilkan dengan stabilo hijau.
- Switch **Sama: OFF** mengembalikan tampilan **nilai berbeda**, termasuk stabilo merah/kuning/biru, penanda koreksi, dan anotasi validasi Tahap 2. Stabilo hijau tidak ikut tampil.
- **Nomor marker hijau** `#01`, `#02`, dst. memakai urutan parameter cocok pada panel Tahap 1 dan Tahap 2; nomor yang sama digunakan pada dokumen rujukan dan dokumen diperiksa.
- Untuk tiap field/halaman hanya dibuat satu badge nomor meskipun teks panjang memiliki banyak kotak stabilo.
- Pencarian lokasi marker mengikuti tepi stabilo dengan jarak rapat dan pemeriksaan teks, stabilo lain, badge lain, serta tinta bitmap. Jika tidak ada lokasi aman, badge tidak dipaksakan di atas teks; nomor di daftar panel tetap tersedia.
- Ekspor **PDF beranotasi rujukan dan diperiksa** juga mengikuti mode eksklusif, termasuk nomor hijau. Mode ON tidak mengekspor anotasi selisih/Tahap 2 ke PDF pemeriksaan beranotasi; anotasi asli tetap tersimpan untuk mode OFF.
- **PDF Hasil Koreksi + Catatan** tetap merupakan keluaran khusus koreksi; isinya tidak dihapus oleh switch inspeksi.
- Data `self.diffs`, pilihan checkbox, Catatan Koreksi, validasi Tahap 2, pembacaan PDF, dan penyimpanan sesi tidak dihapus/diubah oleh switch.

## Verifikasi

- Dokumen contoh SI + PL → SWB ONE 26YA1A: 14 parameter cocok dan 1 selisih Shipper; nomor hijau tersedia pada kedua PDF (sebagian field berada pada halaman berbeda).
- Tes otomatis: 178 lulus, 59 dilewati, 1 gagal lama terkait field Vessel rujukan Meratus. Tes baru switch eksklusif 6/6 lulus.
- Sintaks Python dan ZIP diperiksa. GUI Windows/EXE portable belum diuji langsung.

## Upgrade

Dari v1.8.36.4, timpa `docmatch.py` dan `matched_values.py`, lalu jalankan `py docmatch.py`. Untuk portable, jalankan ulang `build_portable.bat`.

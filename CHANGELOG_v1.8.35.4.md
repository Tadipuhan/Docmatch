# DocMatch v1.8.35.4 — Tight Marker Placement

Basis: v1.8.35.3. Revisi **hanya algoritme penempatan nomor marker** pada Hasil Koreksi dan PDF Catatan.

- Gap dekat highlight menjadi 1,8 pt (koordinat asli PDF) ketika tersedia ruang aman.
- Badge sekarang menguji banyak posisi rapat sepanjang setiap tepi highlight, lalu memilih jarak paling pendek, bukan melompat ke tepi halaman atau lokasi acak.
- Tidak ada lagi fallback pencarian kosong sehalaman: jika mustahil menaruh badge dalam jarak 22 pt tanpa menghalangi karakter / marker lain, badge ditiadakan; nomor tetap tercantum pada Catatan Koreksi.
- Bounding box kata, area highlight, badge lain, dan (untuk scan/Type3) ink guard tetap diperiksa.
- Preview dan hasil ekspor menggunakan fungsi yang sama. Mesin OCR, perbandingan, profil carrier, UI Catatan Koreksi, dan pola nama ekspor tidak berubah.

Batasan: pada tabel sangat padat badge mungkin harus disembunyikan. Tidak ada jaminan akurasi pixel-perfect untuk semua hasil scan. GUI Windows belum diuji.

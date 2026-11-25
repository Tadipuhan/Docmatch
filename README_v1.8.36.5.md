# DocMatch v1.8.36.5 — Filter Eksklusif Nilai Sama/Berbeda

## Cara menggunakan

1. Upload SWB rujukan atau pasangan PDF Shipping Instruction (SI) + Packing List (PL), lalu upload SWB diperiksa.
2. Pilih profil Waybill yang sesuai, lalu klik **Bandingkan**.
3. Di panel pemeriksaan, klik switch **Sama: ON** untuk menampilkan **hanya nilai yang cocok**, baik di PDF A, PDF B, Tahap 1, maupun Tahap 2.
4. Saat **ON**, tiap parameter cocok diberi stabilo hijau dan nomor hijau `#01`, `#02`, dst. Nomor sama pada PDF A dan B serta pada kedua daftar pemeriksaan.
5. Klik **Sama: OFF** untuk menampilkan **hanya perbedaan**, stabilo koreksi, nomor temuan merah, dan anotasi Tahap 2 yang relevan. Hijau tidak terlihat.
6. Ekspor **PDF Rujukan/Diperiksa Beranotasi** untuk menghasilkan arsip yang mengikuti mode switch saat ekspor.

## Aturan keandalan

- Hanya field yang memang terverifikasi sama yang diberi hijau. Field tak terbaca, tidak pasti, atau sedang ditandai selisih tidak dipromosikan menjadi nilai sama.
- Marker hijau memakai ID **terpisah** dari ID perbedaan. Penomoran dimulai kembali dari `#01` ketika berpindah mode.
- Badge diletakkan dekat stabilo dan dicari posisi yang tidak menutupi karakter. Pada halaman yang terlalu padat, badge dapat tidak digambar, tetapi tetap terdaftar pada panel pemeriksaan.
- Switch **hanya menyembunyikan tampilan**. Temuan, keputusan checkbox, catatan koreksi, audit, dan validasi Tahap 2 tetap tersimpan.
- **Hasil Koreksi/Catatan Koreksi** tetap merupakan dokumen khusus perbaikan, tidak dijadikan laporan nilai cocok saat switch ON.
- Fungsi 100% offline, Cross-Carrier SWB, PL+SI, dan AutoZIP portable tetap tersedia.

## Jalankan dan build ulang

```powershell
py docmatch.py
```

Build EXE portable terbaru (Windows):

```powershell
.\build_portable.bat
```

## Hasil pengujian

- Tes otomatis: **178 lulus, 59 dilewati, 1 kegagalan lama Meratus**.
- Kasus PL + SI → SWB ONE 26YA1A: **14 nilai cocok dan 1 temuan Shipper**.
- Uji interaktif langsung di Windows/EXE masih diperlukan sebelum distribusi umum.

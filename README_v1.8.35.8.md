# DocMatch v1.8.35.8 — Cross-Carrier SWB Reference

Aplikasi offline untuk membandingkan **Dokumen A (Rujukan)** dengan **Dokumen B (Diperiksa)**, meskipun keduanya berasal dari **shipping line berbeda**.

## Cara menggunakan

1. Ekstrak source ZIP v1.8.35.8 ke folder baru (jangan campur berkas versi sebelumnya).
2. Jalankan `py docmatch.py` di Windows pada environment Python yang memiliki dependensi aplikasi.
3. Di Tab 1, pilih **Dokumen Rujukan (PDF A)** dan **Dokumen Diperiksa (PDF B)**.
4. Di Tab 2, pada **Mode parameter**, pilih preset SWB sesuai **PDF B**, bukan PDF A.
5. Di bawah toolbar, pilih **Profil Dokumen A (rujukan)**:
   - **Deteksi Otomatis** (default): aplikasi memeriksa apakah A adalah SWB carrier resmi atau surat/tabel rujukan berlabel.
   - Pilih carrier secara manual bila dokumen A tidak dapat dikenali. Sistem akan menolak override manual yang bertentangan dengan identifikasi kuat dari PDF A.
6. Klik **Field Waybill** untuk memilih parameter PDF B yang akan dibandingkan.
7. Klik **Bandingkan**; periksa status “Rujukan A → Diperiksa B”, daftar perbedaan, serta label **Perlu Verifikasi**.
8. Buka **Hasil & Ekspor** untuk melihat highlight dan Catatan Koreksi. Nilai catatan berasal dari **PDF A**, termasuk format baris/spasi yang dapat dibaca dari PDF.

## Contoh pasangan

- A: SWB ONE → B: SWB MERATUS
- A: SWB MAERSK → B: SWB MSC
- A: SWB Evergreen → B: SWB ONE
- A: surat rujukan berlabel → B: SWB GSL

Pemrosesan menggunakan **profil terpisah untuk tiap sisi**; pasangan tersebut adalah skenario yang didukung secara arsitektural, **bukan jaminan seluruh field setiap PDF berhasil terbaca**.

## Aturan keamanan data

- Field yang punya padanan yang jelas dibandingkan berdasarkan nilainya, bukan letak koordinat pada halaman.
- Nomor container dibandingkan beserta seal bila pasangan tersebut bisa diidentifikasi. Berat dan measurement dibaca beserta satuannya.
- Field tanpa padanan, kosong tanpa validasi, atau hasil dekode meragukan **memerlukan verifikasi manual** dan tidak diberi status cocok palsu.
- Posisi penanda PDF A menggunakan koordinat **profil A**, dan PDF B menggunakan koordinat **profil B**.
- Edit manual Catatan Koreksi tidak ditimpa saat pembaruan preview.

## Build portable dan kompresi otomatis

Seperti rilis v1.8.35.7, jalankan `build_portable.bat`. Build Windows memerlukan source lengkap, Python beserta dependency, aset, dan folder Tesseract sesuai pengecekan pada skrip build. Hasil akhirnya:

```text
dist/
├── DocMatch/                # Paket portable lengkap
├── DocMatch_Portable.zip    # ZIP otomatis
└── DocMatch_Portable.7z     # Bila 7-Zip tersedia
```

Untuk mengemas ulang folder `dist/DocMatch` tanpa mengulang PyInstaller:

```powershell
py pack_portable.py
```

Ukuran 300 MB tidak dijamin; kompresi arsip tidak membuang file aplikasi.

## Pengujian dan batasan

Tes Python: `py -m pytest -q` (atau `py tests/run_tests.py`). Uji otomatis tidak menggantikan pengujian GUI/EXE pada Windows.

Keterbatasan deteksi otomatis pada dokumen scan/logo gambar, serta penyesuaian field carrier-specific, dijelaskan di `CHANGELOG_v1.8.35.8.md`. Jangan menganggap status tanpa perbedaan sebagai konfirmasi jika masih terdapat field **Perlu Verifikasi**.

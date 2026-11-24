# DocMatch v1.8.35.7 — Auto ZIP Portable Build

## Perubahan
- `build_portable.bat` sekarang otomatis mengarsipkan **seluruh** folder `dist\DocMatch` setelah proses PyInstaller selesai.
- Arsip utama: `dist\DocMatch_Portable.zip`, memakai **ZIP Deflate standar** yang dapat diekstrak oleh Windows Explorer.
- Jika 7-Zip tersedia, selain ZIP juga dibuat `dist\DocMatch_Portable.7z` (LZMA2 solid) sebagai alternatif kompresi lebih tinggi.
- Jika 7-Zip tidak tersedia, proses tetap menghasilkan ZIP menggunakan Python stdlib (level 9).
- Semua file aplikasi, folder `_internal`, DLL, dan Tesseract yang berada di `dist\DocMatch` **tetap disertakan tanpa penghapusan**.
- Program memverifikasi daftar file dan integritas arsip, termasuk CRC ZIP dan tes 7z.
- Aplikasi, mesin ekstraksi, profil SWB, UI, dan aturan matching tetap sama dengan v1.8.35.6.

## Penggunaan

1. Pastikan Windows memiliki Python dan dependensi yang dibutuhkan untuk build seperti versi sebelumnya.
2. Jika ingin hasil kompresi paling tinggi, install **7-Zip** (opsional) di `C:\Program Files\7-Zip\7z.exe`.
3. Jalankan **di PowerShell**: ` .\build_portable.bat ` (bukan `py build_portable.bat`).
4. Tunggu tahap PyInstaller, kemudian tahap pengarsipan otomatis.
5. File hasil distribusi ada di `dist\DocMatch_Portable.zip`, serta `.7z` jika ada 7-Zip.
6. Untuk menggunakan portable, ekstrak arsip lalu jalankan `DocMatch\DocMatch.exe`.

### Kompresi ulang tanpa rebuild

Jika sudah memiliki `dist\DocMatch` dari build sebelumnya dan ingin membuat arsip lagi, jalankan:

```powershell
py pack_portable.py
```

Memilih ZIP saja: `py pack_portable.py --skip-7z-archive`.
Jika 7-Zip ada di lokasi lain: set environment `DOCMATCH_7ZIP_PATH` menunjuk ke `7z.exe`.

## Batasan ukuran

Ukuran hasil 939 MB -> ZIP manual 443 MB tidak menjamin target 300 MB. ZIP standar tetap dibatasi algoritme DEFLATE. LZMA2 `.7z` **mungkin** mencapai sekitar 300-an MB, tetapi hanya bisa dipastikan dengan build Windows sebenarnya. Mengganti ekstensi `.7z` menjadi `.zip` tidak disarankan.

**Keamanan:** jangan distribusikan hanya `DocMatch.exe`; seluruh folder portable dibutuhkan. Setelah arsip diekstrak, ukuran folder akan kembali mendekati ukuran aslinya.

# DocMatch v1.8.35.9 — Perbaikan Header Tab 2

Revisi ini memperbaiki header **Mode parameter / Profil Dokumen A (rujukan)** yang terjepit setelah klik **Bandingkan** di Tab 2.

## Instalasi source lengkap

1. Cadangkan source dan folder portable sebelumnya.
2. Ekstrak `DocMatch_v1.8.35.9_Header_Layout_Fix.zip` ke folder proyek baru.
3. Jalankan `py docmatch.py` pada Python Windows dengan dependensi proyek.
4. Uji Tab 2: pilih `SWB - EVERGREEN`, `SWB - ONE`, atau profil lain, lalu pilih profil Dokumen A dan klik **Bandingkan**.
5. Pastikan baris Mode parameter dan Profil Dokumen A terbaca penuh tanpa terpotong; masuk ke Tab 1 dan Tab 3 lalu kembali ke Tab 2.

## Instalasi patch untuk proyek v1.8.35.8

Ekstrak `DocMatch_v1.8.35.9_Header_Only_Patch.zip`, lalu salin `docmatch.py` ke **folder source v1.8.35.8**, menggantikan file lama. Disarankan menyalin changelog serta tes ke lokasi yang sama. **Jangan menerapkan patch pada source versi lebih lama yang belum memiliki fitur Cross-Carrier**, karena file `docmatch.py` membutuhkan modul `cross_carrier.py` versi terbaru.

## Perbarui portable EXE

Patch source **tidak otomatis mengubah EXE yang sudah dibuild**. Pada folder proyek yang telah diperbarui, jalankan:

```bat
build_portable.bat
```

Jika build berhasil, gunakan **hasil baru** pada `dist\DocMatch\` atau arsip ZIP/7z yang dihasilkan skrip. Aplikasi portable lama tetap akan memakai UI lama jika hanya mengganti source tanpa rebuild.

## Catatan validasi

Tes otomatis tidak dapat menggantikan pemeriksaan GUI di Windows. Setelah menjalankan aplikasi, uji skala display Windows 100% dan 125% atau 150%, serta ukuran jendela normal dan maksimal. Bandingkan juga hasil PDF untuk memastikan mesin pembanding tetap sama.

Regresi: 125 lulus, 59 dilewati, 1 gagal lama untuk pembacaan Vessel pada surat rujukan Meratus.

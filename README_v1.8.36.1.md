# DocMatch v1.8.36.1 — Perbaikan Upload PL + SI

Perbaikan khusus untuk dialog **Pilih Jenis Dokumen Rujukan**, ketika nama `PL 26YA1A.pdf` dan `SI 26YA1A.pdf` sudah terlihat tetapi klik **OK** justru menampilkan “Upload kedua file PDF SI dan PL.”

## Cara menggunakan

1. Di Tab **1 Pilih Dokumen**, klik pilih dokumen rujukan.
2. Pilih **Packing List (PL) + Shipping Instruction (SI)**.
3. Upload PL, lalu upload SI (keduanya PDF).
4. Klik **OK**. File terpilih kini disimpan di key yang benar dan diteruskan ke tahap validasi PDF.
5. Upload SWB yang diperiksa dan lakukan perbandingan.

## Instalasi

- **Source lengkap**: ekstrak paket v1.8.36.1 ke folder baru, kemudian jalankan `py docmatch.py`.
- **Patch**: ganti `docmatch.py` pada source v1.8.36.0.
- **Portable EXE**: jalankan `build_portable.bat` ulang setelah mengganti source. Mengubah source tidak memperbarui EXE lama.

Fitur perbandingan, parser SI/PL, catatan koreksi dan build ZIP/7z tetap sama. Pengujian runtime pada Windows harus dilakukan di komputer pengguna.

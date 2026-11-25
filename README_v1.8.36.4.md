# DocMatch v1.8.36.4 — Responsive PDF Workspace

Versi ini memperbaiki tampilan yang terpotong di sisi kanan ketika dokumen rujukan (SWB atau SI+PL) dan dokumen diperiksa diunggah.

### Menjalankan source

```powershell
py docmatch.py
```

### Pengujian manual Windows

1. Buka **1 Pilih Dokumen** dan unggah SI 26YA1A.pdf, PL 26YA1A.pdf, serta SWB 26YA1A.pdf.
2. Pastikan **PANEL PEMERIKSAAN** beserta switch **Sama** terlihat utuh di tepi kanan, dan tombol **Atur Parameter →** tetap terlihat utuh.
3. Cek navigasi halaman, zoom +/- dan tombol **Lebar** pada kedua panel PDF. Setiap toolbar terdiri atas dua baris agar tidak melampaui lebar panel.
4. Ubah ukuran jendela, lakukan perbandingan, lalu aktifkan switch **Sama: ON/OFF**. Pastikan Tab 1 dan 2 tetap dapat digunakan.
5. Coba mode referensi SWB biasa, lalu buka **3 Hasil & Ekspor** untuk memastikan fitur sebelumnya tetap berfungsi.

### Build portable

```powershell
.\build_portable.bat
```

Distribusi ZIP/7z dari build portable tetap mengikuti skrip v1.8.36.3. Kode tidak menghapus Tesseract ataupun library PDF.

### Catatan

Pengujian otomatis dapat dilakukan tanpa Qt, tetapi posisi piksel yang sebenarnya harus diverifikasi di Windows, terutama jika DPI scaling sistem lebih dari 100%.

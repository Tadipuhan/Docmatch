# DocMatch v1.8.35.1 — Koreksi Penanda Saja

### Perubahan dari v1.8.35

- **Penanda Hasil Koreksi** menggunakan badge bernomor kecil di samping highlight pada nilai PDF, bukan garis ke margin.
- **Catatan Koreksi kembali seperti v1.8.34**: kotak catatan pada margin kanan di dalam satu tampilan PDF; klik langsung teksnya untuk mengedit. Tidak ada accordion, tidak ada tombol Batal/Simpan yang baru.
- Pembaruan catatan tersimpan saat diketik; tombol **Perbarui Preview** menghitung kembali kotak, tombol **Ekspor PDF Catatan** menghasilkan PDF dengan highlight/badge baru dan catatan asli.
- Hasil Bandingkan tetap di Tab 2; Tab 3 berisi satu PDF diperiksa + margin catatan.

### Langkah uji

1. Jalankan `py docmatch.py` dan bandingkan dua dokumen.
2. Masuk ke **3 Hasil & Ekspor**; pastikan badge #01 dst. muncul di samping teks PDF dan tidak ada garis ke catatan.
3. Pastikan semua kotak **Catatan Koreksi** di margin kanan terlihat sekaligus, dapat diklik dan diedit langsung, tidak memakai accordion.
4. Ubah catatan, klik **Perbarui Preview**, ekspor PDF dan periksa nomor serta catatan tetap sesuai.

### Pengujian

```powershell
py -m pytest tests -q
```

Source tidak menyediakan runtime Tesseract maupun executable portable; build portable tetap membutuhkan folder Tesseract offline sesuai skrip.

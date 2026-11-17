DocMatch v1.8.14 — Penanda PDF GSL mengikuti batas teks

- Kotak koreksi pada halaman 1 GSL menggunakan gabungan koordinat glyph hasil pemulihan Type3 dari dokumen diperiksa.
- Label template di bagian atas field dikecualikan dan hasil dibatasi pada kotak field cetak.
- Padding kotak penanda 1,5 point; satu kotak dan satu garis untuk setiap field.
- Jika koordinat glyph tidak valid, sistem menggunakan batas field seperti versi sebelumnya, bukan menebak posisi teks.
- Perbandingan, nilai koreksi, dan mode ANL/Evergreen tidak diubah.

CATATAN: Perlu diuji melalui ekspor PDF di Windows. Pengujian yang dilakukan pada paket ini adalah kompilasi sintaks Python.

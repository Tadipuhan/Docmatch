# DocMatch v1.8.32 — Flexible GSL Reference Reading

## Fitur
- Mode `SWB - Golden Star Line` kini mengekstraksi PDF A (rujukan) dan PDF B (diperiksa) secara **independen**.
- PDF GSL resmi tetap memakai decoder Type3 dan koordinat presisi dari v1.8.31.
- Surat/tabel referensi dengan label parameter GSL dikenali menggunakan teks PDF dan posisi label/nilai; mendukung 26 field pada dua PDF sintetis pengujian.
- Pergantian baris pada surat berbeda layout tidak otomatis dianggap perubahan teks.
- Saat ada field yang benar-benar tidak terbaca, parameter tetap masuk daftar perlu verifikasi; nilai tidak ditebak.
- Pada validasi Tahap 2, pencarian kandidat region pada dokumen berlabel memakai posisi teks tersebut, bukan posisi template GSL.

## Keterbatasan
- Fokus saat ini pada mode GSL dan dokumen referensi berlabel yang memiliki text layer PDF.
- PDF hasil scan tanpa teks, surat tanpa label field jelas, dan layout sangat kompleks perlu OCR / pemetaan manual.
- Konten yang semantik sama tetapi ditulis dengan singkatan/urutan kata berbeda dapat tetap terdeteksi sebagai perbedaan; ini disengaja agar tidak menyamakan data secara sembarangan.
- Pengujian berpasangan dengan *PDF GSL carrier asli* dan GUI Windows belum dilakukan pada build ini.

## Uji yang sudah dijalankan
- Dokumen surat A: 26/26 field ditemukan (20 halaman utama dan 6 Attached List).
- Dokumen surat A dibandingkan dengan dirinya sendiri: 0 temuan.
- Dokumen surat A dibandingkan dengan surat B yang berbeda layout: 14 field berbeda sesuai CSV ground truth.
- Regresi otomatis: 33 lulus; 30 skip karena fixture/dependensi tidak tersedia.

## Cara mencoba
1. Jalankan aplikasi dan pilih surat PDF berlabel sebagai Dokumen Rujukan.
2. Pilih dokumen carrier GSL asli sebagai Dokumen Diperiksa.
3. Pilih mode `SWB - Golden Star Line`, lalu klik **Bandingkan**.
4. Periksa jumlah parameter perlu verifikasi serta posisi penanda; buka Validasi Tahap 2 untuk mengoreksi bagian yang belum pasti.

Dokumen PDF asli tetap tidak diubah. Pengaturan visual antarmuka mengikuti v1.8.31.

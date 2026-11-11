DocMatch v1.6 — GSL Page 3 Partial Detection Update (tanpa OCR)

Perubahan:
- Menambah field 'Attached List - Container Count' yang mendeteksi angka jumlah kontainer pada baris total halaman PDF ke-3.
- Menggunakan posisi relatif dan kedekatan dengan baris 'CONT TOT. TARE', bukan koordinat Y tetap.
- Mengoreksi kesalahan pemetaan glyph halaman 3: code 12 tidak lagi dipaksa menjadi spasi, dan separator code 3 diperlakukan sebagai spasi.
- Peringatan pemeriksaan parsial tidak lagi berupa pop-up modal; daftar field yang dilewati ada pada tooltip status.

Pengujian dengan dua contoh PDF:
- GSL_SWB 26B92KR1C (FINAL).pdf: jumlah kontainer 1
- GSL_SWB_26BX2VN1B (FINAL).pdf: jumlah kontainer 3
- Perbandingan kedua dokumen: satu temuan untuk field baru.
- Perbandingan dokumen dengan dirinya sendiri: nol temuan untuk field baru.

BATASAN PENTING:
- Ini bukan perbaikan penuh halaman 3. Banyak glyph Type3 pada cargo, seal, weight, dan measurement belum dapat divalidasi.
- Field yang belum dapat dipulihkan tetap dilewati, bukan dianggap cocok.
- Tidak menggunakan OCR dan tidak menebak karakter yang belum dapat diverifikasi.
- GUI Windows dan hasil build EXE belum diuji.

Pemasangan:
1. Cadangkan source DocMatch saat ini.
2. Ekstrak ZIP ke folder baru.
3. Salin rules.py milik proyek Anda jika diperlukan oleh build.
4. Jalankan build_portable.bat di Windows.
5. Gunakan seluruh folder dist/DocMatch, bukan EXE saja.

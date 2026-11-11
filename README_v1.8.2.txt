DocMatch v1.8.2 - Parameter GSL per kotak

- GSL: kotak utama dan kolom Attached List halaman 3 dipisah menjadi 24 pilihan field.
- Field perjalanan, identitas, muatan, berat dan measurement diberi area tersendiri.
- Vessel dan Voyage berbagi kotak cetak dan dibedakan oleh filter token.
- Semua perbandingan GSL tetap membutuhkan Tesseract OCR yang berfungsi.
- Kalibrasi koordinat mengikuti template PDF GSL 3 halaman yang sebelumnya dipakai;
  variasi layout wajib diuji ulang. Tidak ada OCR Windows binary dalam ZIP ini.
- Status OCR dapat diperiksa pada aplikasi. Jika OCR gagal, hasil bukan 0 temuan sah.
- Back up source lama, salin rules.py dari proyek aktif, jalankan build_portable.bat.
- Penting: perubahan field tidak menjamin angka dan teks OCR terbaca dengan benar.
- Pengujian yang dilakukan: sintaks Python, integritas ZIP, non-overlap kolom
  Attached List (kecuali kotak nilai turunan yang sengaja berada di dalam kolom).
- Belum diuji: runtime OCR dan tampilan aplikasi pada Windows.

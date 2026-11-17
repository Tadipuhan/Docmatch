DocMatch v1.8.8 - GSL Halaman 1, outline per kotak
- Pada ekspor PDF catatan GSL halaman pertama, setiap field yang memiliki temuan disorot sebagai SATU bingkai merah per kotak; tidak ada stabilo kata individual pada halaman tersebut.
- Satu garis penghubung dan satu catatan per field. Halaman Attached List tetap menggunakan stabilo per temuan.
- Field Forwarding Agent, Remarks, Further Routing ditambahkan sebagai pilihan field terpisah.
- Judul cetak (label) bukan nilai koreksi. OCR tetap dapat salah membaca label; verifikasi hasil dan catatan sebelum ekspor.
- Tidak ada pembetulan teks otomatis pada PDF asli.
- Koordinat GSL mengacu pada template sampel; dokumen dengan layout berbeda membutuhkan kalibrasi.
- Untuk build: salin rules.py dari proyek Anda yang sudah berfungsi, sertakan Tesseract portable dan jalankan build_portable.bat.
- Validasi: sintaks Python saja; GUI dan hasil OCR Windows belum diuji.

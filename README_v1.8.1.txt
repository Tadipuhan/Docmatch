DocMatch v1.8.1 — GSL OCR Runtime & Diagnostics Fix

Perbaikan terukur:
- GSL tidak lagi mengembalikan 0 temuan palsu ketika OCR tidak tersedia. Pemeriksaan dibatalkan dengan pesan penyebab.
- Tesseract dicari dari _internal/tesseract, folder EXE/tesseract, folder source/tesseract, atau PATH.
- TESSDATA_PREFIX mengikuti lokasi executable Tesseract yang benar-benar dipakai.
- Script build memvalidasi tesseract.exe dan bahasa eng sebelum membuat EXE.
- Setelah perbandingan GSL berhasil dijalankan, file gsl_ocr_diagnostik.json dibuat di direktori kerja sementara aplikasi; tooltip status menunjukkan lokasinya. File sementara ini dapat hilang saat aplikasi ditutup, jadi salin sebelum menutup aplikasi.

PENTING: ZIP ini adalah SOURCE/BUILD KIT, bukan EXE siap jalan. Binary Windows Tesseract tidak disertakan. Jangan mengklaim OCR aktif sebelum melihat status OCR pada aplikasi portable.

Persiapan Windows:
1. Salin rules.py yang cocok dari source yang sebelumnya berfungsi.
2. Letakkan tesseract/tesseract.exe, DLL terkait, tesseract/tessdata/eng.traineddata.
3. Jalankan build_portable.bat.
4. Jalankan dist/DocMatch/DocMatch.exe dari folder lengkap, jangan salin EXE saja.
5. Jika error, kirim pesan kesalahan dan file diagnostik.

Catatan: Perbaikan ini memperbaiki ketersediaan runtime dan pelaporan; akurasi 23 field GSL tetap perlu diuji pada Windows dengan OCR aktif.

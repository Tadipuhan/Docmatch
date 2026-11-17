# DocMatch v1.8.30.6 — SWB MAERSK

## Perubahan
- Menambahkan pilihan **SWB - MAERSK** pada Mode Parameter.
- Menambahkan **24 field** pada dialog Field Waybill MAERSK, mencakup identitas, pihak terkait, rute, kontainer, cargo, freight, tanggal, dan lampiran.
- Mendukung dua layout Maersk pada halaman 1: **Bill of Lading FINAL** dengan Notify Party di kanan dan **Non-Negotiable Waybill DRAFT** dengan Notify Party di kiri. Layout dipilih menggunakan posisi heading `Notify Party` pada dokumen, bukan nama berkas.
- Memakai koordinat relatif (halaman PDF) dengan token bounding boxes untuk penanda.
- Mengabaikan watermark besar seperti CERTIFIED, VERIFY, COPY dalam ekstraksi area.
- Memakai region profil yang tepat saat Validasi Tahap 2 menampilkan kandidat kotak.
- Profil lainnya (ONE, GSL, ANL, Evergreen) dipertahankan tanpa perubahan algoritme.

## Keterbatasan
- Dua dokumen contoh MAERSK (masing-masing 2 halaman) digunakan untuk kalibrasi, namun tidak disertakan dalam ZIP sumber.
- Halaman lampiran selain pola contoh dan PDF scan tidak dapat dijamin memiliki koordinat yang sama.
- Bidang kosong tetap kosong: tidak dilakukan tebakan dari data lain.
- OCR fallback membutuhkan Tesseract terpasang seperti pada versi sebelumnya.
- Pengujian GUI Windows belum dilakukan di lingkungan pembuatan paket.

## Pengujian
- 9 tes otomatis lulus pada sumber yang mencakup kedua contoh (fixture PDF dihilangkan dari ZIP).
- Self-comparison setiap contoh MAERSK menghasilkan 0 temuan.
- Perbandingan silang dua contoh menghasilkan temuan untuk sejumlah field yang memang berbeda.

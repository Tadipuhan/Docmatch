DocMatch v1.8.3 — Golden Star Line Attached List field grouping

Perubahan: halaman ketiga GSL kini dibagi menjadi enam field yang mengikuti
kolom/baris cetak: MKS & NOS/SEAL.NO, Description of Goods, Weight &
Measurement, CONT & SEAL, SHIPPER'S LOAD STOWAGE & COUNT, CLAUSES.
Header Attached List dipertahankan sebagai field tersendiri.

Temuan OCR tetap individual, tetapi dikelompokkan pada field induknya.
Field Cargo Quantity dan Container Count lama dihapus sebagai field terpisah
untuk menghindari temuan duplikat; angka tetap berada di area kolom/band induk.

PENTING: Koordinat berdasarkan dua PDF GSL contoh, dan belum diuji pada GUI
Windows. Mesin Tesseract + eng.traineddata tetap wajib untuk OCR GSL.
File rules.py eksternal tetap diperlukan bila proyek Anda memakainya.

Instalasi: backup source, salin file dari paket, rebuild dengan
build_portable.bat, kemudian cek daftar field pada langkah Atur Parameter.

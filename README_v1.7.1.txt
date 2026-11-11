DocMatch v1.7.1 - GSL Hybrid OCR diagnostics and numeric fields

Perbaikan:
- Build portable DIBATALKAN bila Tesseract atau eng.traineddata belum tersedia.
- Status aplikasi menunjukkan OCR aktif/tidak tersedia.
- Tambah 3 field terpisah di Attached List: Cargo Quantity, Gross Weight, Measurement.
- Angka diproses dari kotak sempit dan hanya diterima jika confidence OCR >= 75 dan hasil tunggal.
- Tidak ada OCR online. Tidak ada penggantian otomatis pada dokumen asli.

PENTING: Download distribusi resmi Tesseract Windows yang kompatibel, lalu taruh seluruh isi instalasi (exe, DLL, tessdata/eng.traineddata) di folder tesseract sebelum menjalankan build_portable.bat. Paket ZIP ini tidak menyertakan binary Tesseract.

Uji pada Windows: Jalankan hasil build, pilih SWB - Golden Star Line, cek status OCR offline aktif dan temuan halaman 3. Jangan menyetujui angka OCR tanpa memeriksa PDF asli.

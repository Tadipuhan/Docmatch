# DocMatch v1.8.35.3 — Non-Overlapping Correction Markers

Update khusus pada **penanda nomor di Hasil Koreksi (Tab 3) dan hasil Ekspor PDF Catatan**.

## Tujuan

Marker `#04`, `#05-#10`, dan marker lain tidak boleh menutupi teks asli atau nilai yang diberi highlight, termasuk teks di kolom tabel sebelahnya.

## Perubahan

- Pencarian posisi badge mengikuti urutan kiri → atas → kanan → bawah, lalu ruang kosong sekitarnya / tepi halaman.
- Posisi diperiksa terhadap seluruh bounding box kata di PDF asli, seluruh area highlight yang sedang diekspor, serta marker sebelumnya pada halaman yang sama.
- Tidak ada garis penghubung. Marker tetap mengikuti nomor koreksi yang sama dengan catatan pada panel kanan.
- Pada halaman dengan teks tidak dapat diekstrak (raster/Type3), ada pengecekan piksel grayscale untuk menghindari area yang mengandung tulisan; **tanpa dependensi baru**.
- Jika halaman benar-benar tidak memiliki ruang kosong untuk badge, label di dokumen diabaikan daripada menutupi bukti; nomor temuan masih tersedia dalam header Catatan Koreksi.
- Preview Tab 3 dan Ekspor PDF Catatan memakai penulis PDF yang sama, sehingga posisi badge konsisten.

## Yang tidak berubah

- Tampilan dan perilaku Catatan Koreksi tetap seperti v1.8.34 / v1.8.35.2 (bisa diketik langsung, tanpa accordion).
- Tombol Bandingkan dan navigasi tab.
- Field Waybill serta semua modul ekstraksi, OCR, validasi, dan mesin carrier.
- Nama file ekspor tetap `Koreksi_[Nama Dokumen Diperiksa].pdf`.

## Cara menguji

1. Ekstrak ZIP ke folder terpisah, jalankan `py docmatch.py`.
2. Bandingkan dua PDF; pilih beberapa temuan Quantity, Container & Seal, Cargo Description, dan Weight.
3. Buka Tab 3 **Hasil & Ekspor**, periksa marker yang berdekatan, lakukan zoom, lalu **Perbarui Preview**.
4. Pilih **Ekspor PDF Catatan**. Pastikan marker tidak menutupi huruf baik di preview maupun hasil PDF.
5. Jalankan `py -m pytest -q` jika `pytest` tersedia.

## Validasi dan batasan

- Uji sintaks Python dan uji pengaturan marker/ekspor berhasil.
- Uji pada PDF ONE asli membuktikan marker berdekatan bisa dipindah ke area kosong tanpa menutupi kata berdasarkan bounding box hasil ekstraksi.
- Pada scanned PDF, pemeriksaan piksel bersifat konservatif; jika tidak ada ruang kosong badge dapat tidak digambar.
- Pengujian GUI Windows belum dijalankan.
- Satu regresi ekstraksi **surat rujukan Meratus**, yang juga gagal di versi dasar v1.8.35.2, belum diperbaiki dalam revisi penanda ini.

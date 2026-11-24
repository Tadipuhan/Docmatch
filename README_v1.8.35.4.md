# DocMatch v1.8.35.4 — Tight Marker Placement

**Tujuan:** nomor `#01-#03`, `#04`, `#05-#10`, dan penanda lain berada sedekat mungkin dengan area highlight tanpa menimpa karakter.

## Perubahan yang dibatasi
- Pemilihan kandidat mengutamakan tepi stabilo, dengan jarak awal **1,8 PDF point** dan pencarian sepanjang tepi berjarak 2,5 pt.
- Setiap kandidat diuji terhadap teks asli, semua kotak highlight, badge lain, dan (jika relevan) piksel gambar hasil scan.
- Maksimal perpindahan badge dari stabilo 22 pt. Bila tidak ada ruang aman, badge tidak ditampilkan di atas PDF; nomor koreksi tetap ada di catatan. Hindari salah mengartikan marker yang tidak muncul sebagai temuan yang hilang.
- Ekspor PDF dan preview Tab 3 berbagi algoritme penempatan.

## Fitur dipertahankan
- Catatan Koreksi tetap seperti v1.8.34 (editor langsung, bukan accordion).
- Nama ekspor `Koreksi_[Nama Dokumen Diperiksa].pdf`.
- Semua mode SWB dan OCR tidak diubah.

## Verifikasi di Windows
1. Ekstrak ZIP ke folder baru, jalankan `py docmatch.py`.
2. Bandingkan contoh ONE, periksa dokumen di Tab 3.
3. Pastikan marker berada dekat highlight, tidak menutup huruf meskipun ada beberapa marker berdekatan.
4. Perbarui Preview dan ekspor PDF; periksa konsistensi kedua tampilan.

**Status:** tes otomatis di lingkungan pengembangan, pengujian GUI Windows masih diperlukan. Ada satu kegagalan regresi Meratus lama yang tidak berasal dari modifikasi marker.

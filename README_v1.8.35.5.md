# DocMatch v1.8.35.5 — Catatan Koreksi Sesuai Format Dokumen Rujukan

## Perubahan utama
Hanya **Shipper**, **Consignee**, dan **Notify Party** pada area **Catatan Koreksi (Tab 3)** yang diubah: nilai otomatis mengikuti nilai field lengkap di Dokumen Rujukan (PDF A), termasuk kapitalisasi, baris, tanda baca, dan spasi yang tersedia pada lapisan teks PDF.

Jika Shipper memiliki beberapa perbedaan (#02-#06), satu kartu Catatan Koreksi akan menampilkan satu blok alamat utuh milik PDF A; tidak menggabungkan hanya cuplikan kata yang berubah. Nilai pada dokumen diperiksa tetap tidak berubah.

## Prioritas data
1. Edit manual pengguna pada kotak Catatan Koreksi — selalu dipertahankan.
2. Nilai alamat lengkap asli dari Dokumen Rujukan.
3. Bila nilai tidak berhasil diekstrak dengan aman, catatan lama dipertahankan untuk verifikasi manual.

## Pembatasan
- Tidak mengubah mesin matching, metode OCR, penanda/stabilo, format ekspor nama file, maupun layout panel.
- Pengembalian baris dan spasi berlaku untuk **karakter yang tersimpan/dapat didekode** dari PDF. Layout pada gambar hasil scan atau teks yang diposisikan satu glyph per glyph mungkin tidak menyediakan informasi spasi persis seperti yang tampak di layar.
- Field lainnya tidak mengalami perubahan format catatan.

## Cara menguji
1. Ekstrak ZIP ke folder baru dan jalankan `py docmatch.py`.
2. Masukkan PDF A dan PDF B, pilih SWB masing-masing, lalu **Bandingkan** di Tab 2.
3. Buka Tab 3, periksa format Shipper, Consignee, Notify Party pada Catatan Koreksi terhadap PDF A.
4. Ubah satu catatan secara manual, klik **Perbarui Preview**, lalu ekspor `Koreksi_[Nama Dokumen Diperiksa].pdf`. Pastikan hasil edit tetap sama.
5. Untuk alamat dengan 2–3 baris, periksa spasi, kapitalisasi dan pergantian baris pada hasil PDF ekspor.

## Pemeriksaan yang dilakukan
- Unit test nilai alamat di PDF carrier dan surat rujukan dengan label.
- Pengujian catatan dari beberapa temuan dalam satu field, override manual, dan ekspor PDF.
- Regresi dasar seluruh profil. GUI Windows belum diuji pada lingkungan ini.

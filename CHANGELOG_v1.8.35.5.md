# DocMatch v1.8.35.5 — Source-Faithful Address Correction Notes

## Perubahan
- Catatan Koreksi otomatis untuk **Shipper, Consignee, dan Notify Party** kini mengambil **nilai field lengkap dari Dokumen Rujukan (PDF A)**, bukan menggabungkan potongan teks perbedaan yang semula kehilangan tata baris.
- Menjaga kapitalisasi asli, tanda baca, spasi yang benar-benar terkode dalam PDF, dan baris teks seperti pada sumber; tidak menormalisasi ejaan atau spasi di catatan. Penentuan MATCH/MISMATCH tetap menggunakan mesin perbandingan sebelumnya.
- Mendukung carrier PDF dan rujukan fleksibel berlabel. Pengenalan label field lain tetap digunakan sebagai batas agar data berdekatan tidak terseret ke alamat Notify Party.
- Perubahan manual pengguna (baik per-item maupun per-group) **tidak ditimpa** saat preview di-refresh atau hasil diekspor.
- Pembungkusan teks PDF margin kini mempertahankan spasi berturut-turut serta manual line breaks alih-alih menggabungkannya menggunakan `split()`.
- Skrip build portable menyertakan modul `reference_note_format.py`.

## Tidak diubah
- Tampilan editor Catatan Koreksi v1.8.34, penanda rapat v1.8.35.4, dan nama file `Koreksi_[Nama Dokumen Diperiksa].pdf`.
- Profil SWB, aturan perbandingan, hasil OCR, posisi stabilo, dan validasi dua tahap.

## Hasil validasi
- Pengujian khusus rujukan carrier, referensi fleksibel, override manual, preservasi spasi/enter, dan penulisan file PDF ekspor.
- Seluruh regresi; satu kegagalan pengujian Meratus yang sama telah dibuktikan ada pada v1.8.35.4 sebelum revisi ini.

## Batasan
PDF tidak selalu menyimpan pemisahan visual sebagai karakter spasi/enter (terutama hasil scan, font Type3 khusus, atau tata letak hasil positioning). Sistem mempertahankan karakter yang benar-benar dapat dipulihkan dari lapisan teks; bila tidak tersedia, menggunakan kata tepercaya dari mesin ekstraksi. Kesamaan pixel-perfect dengan tata letak teks asli tidak dapat dijamin. Pengujian GUI Windows masih diperlukan.

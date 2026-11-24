# DocMatch v1.8.33.1 — ANL/CNC/CMA CGM Reference Recognition Fix

## Perbaikan
- Pengenal formulir SWB ANL/CNC/CMA CGM pada `flexible_reference.py` sekarang menguji kombinasi judul, identitas carrier, dan ciri field formulir.
- Dokumen B carrier tidak lagi otomatis salah diklasifikasikan sebagai surat rujukan fleksibel hanya karena memiliki label Shipper, Consignee, dan Notify Party.
- Surat rujukan ANL naratif atau tabel tetap menggunakan ekstraksi label independen.
- Nama/nilai field profil ANL dan koordinat ekstraksi carrier tetap dipertahankan. Layout UI dan pemrosesan dokumen lain tidak dimodifikasi.

## Penting
- Surat uji ANL sintetis hanya memuat 13 dari 19 field profil. Enam field lainnya harus tetap membutuhkan verifikasi; nilainya tidak boleh ditebak.
- Dokumen rujukan sintetis dan PDF SWB asli yang berbeda transaksi memang dapat menghasilkan banyak MISMATCH yang sah; itu bukan indikasi seluruh mesin ekstraksi gagal.
- Regresi: 46 passed, 30 skipped pada lingkungan pengujian ini. Formulir carrier ANL pada tes klasifikasi dibuat secara sintetis; PDF carrier asli dari screenshot belum tersedia untuk pengujian end-to-end.
- Pengujian GUI Windows belum dilakukan.

DocMatch v1.8.9 — GSL halaman 1, preset 20 kotak

- Memetakan 20 field halaman 1 sesuai nomor pada gambar pengguna.
- Menambahkan Point and Country of Origin, Initial Carriage, Place of Receipt,
  Freight Payable At sebagai field tersendiri.
- Vessel dan voyage berada dalam satu kotak, sesuai gambar nomor 11.
- Header layout dipisahkan melalui masking pita caption (termasuk label dua baris).
- Kotak yang kosong tidak otomatis dikategorikan sebagai OCR gagal.
- Satu catatan per field dan bingkai merah tetap menggunakan alur ekspor sebelumnya.
- Attached List halaman 3 dipertahankan.

PENTING:
Koordinat adalah preset terkalibrasi secara perkiraan dari contoh gambar, bukan
hasil verifikasi terhadap pasangan PDF asli. Hasil OCR wajib diperiksa manual
sebelum koreksi disetujui. OCR tidak dapat menjamin identifikasi font bold.
Perlu pengujian PDF rujukan dan diperiksa untuk memvalidasi batas kotak dan
akurasi penanda. Source belum diuji di GUI Windows.

Pemasangan: cadangkan source lama, ekstrak paket, sertakan rules.py dari
proyek Anda jika dipakai oleh build, lalu jalankan build_portable.bat.

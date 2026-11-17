DocMatch v1.8.15 — Perbaikan ekspor GSL

- Memperbaiki exception: 'Rect' object has no attribute 'is_finite'.
- Validasi rectangle menggunakan math.isfinite untuk semua koordinat.
- Penanda GSL mengikuti union bounding box kata yang telah tervalidasi dan dipotong pada area isi field.
- Label template di bagian atas kotak tidak dimasukkan ke dalam penanda.
- Nama versi pada title bar diperbarui ke 1.8.15.

CATATAN: Belum ada uji visual ekspor PDF di Windows. Koordinat Type3
masih perlu diverifikasi pada PDF pengguna. Tidak ada perubahan pada
algoritme pembandingan Booking/Waybill dalam patch ini.

Cara pakai: backup source lama, salin semua file dari folder ini ke
folder source DocMatch. Untuk EXE portable, rebuild menggunakan skrip build.

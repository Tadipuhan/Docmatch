DocMatch v1.8.13 — GSL Type3 decoder-first (tanpa OCR)

Basis: v1.8.12.
- GSL tidak lagi mensyaratkan Tesseract/OCR untuk menjalankan perbandingan.
- Glyph Type3 yang sudah tervalidasi dipulihkan secara offline, lalu dipetakan ke kotak GSL.
- Booking Number, Waybill Number, Consignee, Vessel, Port of Loading dan Port of Discharge diuji dengan dua PDF GSL yang disertakan pengguna.
- Setiap field halaman pertama dibandingkan sebagai satu temuan, bukan per kata.
- Karakter belum terpetakan atau field kosong ditandai BELUM TERVERIFIKASI, bukan dianggap sama.
- Area Point and Country of Origin diperbaiki agar teks Remarks tidak salah masuk.
- Mode ANL/Evergreen tidak diubah.

HASIL UJI DUA PDF GSL:
Perubahan: Booking Number, Waybill Number, Consignee, Vessel, Port of Discharge.
Shipper dan Port of Loading cocok.
18 field lainnya belum terverifikasi; termasuk sebagian Attached List.
Ini bukan klaim akurasi penuh. Validasi tambahan diperlukan untuk font/glyph lain.

INSTALASI:
Backup source DocMatch lama. Salin docmatch.py, waybill_rules.py, gsl_font_recovery.py dari paket ini ke folder source.
Jalankan aplikasi atau rebuild portable menggunakan build_portable.bat.
Tidak perlu memasang OCR.

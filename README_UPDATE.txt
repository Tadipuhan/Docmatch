DocMatch v1.6 — Field SWB per kotak

Perubahan:
- SWB - EVERGREEN: 20 field termasuk Pre-Carriage, Place of Receipt,
  Document Number, Export References, Freight & Charges, Place of Delivery,
  dan Attached List (halaman 2). Vessel dan Voyage Number dipisahkan.
- SWB - Golden Star Line: 15 field termasuk Booking Number dan Attached List
  (halaman 3 PDF sampel; halaman 2 kosong). Pemetaan area visual diperbaiki.
- Dialog Field Waybill kini mengikuti preset yang dipilih, bukan 13 field ANL.
- SWB ANL/CNC/CMA CGM tidak diubah.
- OCR tidak digunakan. PDF GSL sampel memiliki font encoding rusak dan
  pemeriksaan otomatis tetap dihentikan untuk mencegah temuan palsu.

Pemasangan: backup docmatch.py dan waybill_rules.py, lalu ganti kedua file
beserta folder assets. Jalankan py docmatch.py. Jika memakai EXE, build ulang.

Catatan: koordinat dikalibrasi dari SATU contoh per carrier. Perlu uji dengan
pasangan SWB yang berbeda dan template revisi sebelum dipakai operasional.

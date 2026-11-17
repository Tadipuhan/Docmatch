# DocMatch v1.8.30.8 — SWB - MSC

Menambahkan mode `SWB - MSC (Mediterranean Shipping Company)` tanpa mengubah mesin pembaca ANL/CNC, EVERGREEN, GSL, ONE, MAERSK, atau MERATUS.

## Dukungan

- MSC *Bill of Lading* DRAFT tanpa Rider Page (contoh: MEDUKU761202).
- MSC *Sea Waybill* DRAFT dengan Rider Page (contoh: MEDUKU991874).
- Nama jenis dokumen, jumlah Rider Pages, dan daerah muatan dibaca dari PDF, bukan nama file.
- 25 parameter dapat dicentang di menu **Field Waybill**; parameter rider hanya berisi nilai bila Rider Page tersedia.
- Teks Terms & Conditions tidak digunakan untuk Cargo Description.
- PDF sumber tetap tidak diubah.

## Penggunaan

1. `py docmatch.py` pada folder sumber lengkap (termasuk `rules.py`).
2. Pilih dua PDF di langkah Pilih Dokumen.
3. Di Mode Parameter pilih **SWB - MSC (Mediterranean Shipping Company)**.
4. Klik **Field Waybill** untuk memilih parameter.
5. Klik **Bandingkan**, lalu periksa highlight, hasil, dan bila diperlukan Validasi Tahap 2.

## Field utama

Waybill Number, Document Type, Shipper, Consignee, Notify Party, Vessel / Voyage, Booking Number, Shipper Reference, Port of Loading, Port of Discharge, Place of Receipt, Place of Delivery, Container Count, Freight & Charges, Place of Issue, Date of Issue, Shipped on Board Date, Number of Rider Pages, Gross Weight, Gross Measurement, Quantity, Container & Seal, Cargo Description, Invoice Number, dan Rider - Container Details.

## Batasan

Profil MSC ini dikalibrasi dari dua PDF digital contoh. Template MSC lain, pemindaian resolusi rendah, dan variasi Rider Page lebih panjang memerlukan verifikasi tambahan. Isi field kosong/placeholder tetap ditampilkan sebagaimana tertulis dalam PDF. Perbandingan dua pengiriman berbeda akan menghasilkan temuan yang memang berbeda; bukan berarti dokumen tersebut salah.

## Pengujian

`python -m pytest -q tests/test_msc_profile.py`

Uji fixture opsional menggunakan `tests/fixtures/msc_bl.pdf` dan `msc_swb.pdf`, yang **tidak** disertakan demi menjaga dokumen pengguna tetap terpisah dari paket source. Sebelum dipakai di produksi, jalankan uji GUI dan ekspor pada Windows.

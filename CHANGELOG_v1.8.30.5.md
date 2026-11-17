# DocMatch v1.8.30.5 — SWB - ONE

- Menambahkan preset `SWB - ONE (Ocean Network Express)` di Mode Parameter.
- Menambahkan daftar 27 field pada dialog Field Waybill untuk ONE, termasuk lampiran halaman kedua.
- Mendukung layout awal yang sama untuk Draft Sea Waybill dan Draft Bill of Lading ONE.
- Menyimpan pilihan field terpisah ketika berpindah masuk ke preset ONE.
- Ekstraksi native PDF menggunakan koordinat halaman dan pemilihan titik tengah kata.
- Untuk baris ringkasan container, quantity, cargo, gross weight dan measurement, posisi mengikuti penanda `N/M` agar tabel 2/4 container tetap terbaca.
- Bagian Attached List - Clauses menggunakan anchor `OCEAN FREIGHT` halaman dua, bukan potongan statis yang mencampur deskripsi.
- Menjaga seluruh preset ANL/CNC, EVERGREEN, GSL, serta logika validasi/ekspor sebelumnya.

## Batasan

- Preset ONE dikalibrasi dari dua PDF draft 2 halaman yang disediakan, bukan semua revisi template ONE.
- `Vessel / Voyage` diperlakukan sebagai satu field karena tercetak dalam satu sel.
- Kotak kosong tetap bisa menghasilkan teks kosong, bukan OCR atau dugaan.
- Untuk PDF scan tanpa text layer, verifikasi OCR Tahap 2 masih diperlukan.
- Pengujian GUI Windows belum dilakukan.

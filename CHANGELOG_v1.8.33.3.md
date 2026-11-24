# DocMatch v1.8.33.3 — Perbaikan rujukan Meratus Way Bill (+ seluruh isi v1.8.33.2)

## Gejala (tangkapan layar pengguna)
Rujukan Meratus Way Bill: penanda Consignee/Notify Party jatuh pada paragraf syarat di sisi kanan,
penanda menutupi caption ("Port of Loading", "Gross Weight", "Revenue Tons ..."), temuan palsu
(Vessel/Port of Loading yang nilainya sama dilaporkan berubah), dan status bar "13 field perlu verifikasi".

## Akar masalah
`flexible_reference._is_carrier_form` mengenali formulir Meratus hanya bila kata "meratus" ada sebagai
TEKS di bagian atas halaman. Pada Way Bill, "MERATUS" adalah logo grafis, sehingga dokumen dikira surat
rujukan dan dibaca oleh pembaca label (nilai = baris terdekat dari label), bukan oleh sel Meratus yang
sudah dikalibrasi. Aturan ini identik pada v1.8.33.1; v1.8.33.2 tidak mengubah jalur Meratus, tetapi
perilaku salahnya ada di kedua versi. "Perlu verifikasi" hanya dihasilkan oleh pembaca label: itu petunjuknya.
Direproduksi pada rekonstruksi sintetis Way Bill: pembaca label membaca Consignee = paragraf "Received by the
carrier ...", Vessel = baris caption; jalur sel membaca semuanya benar.

## Perbaikan
- `flexible_reference._looks_like_meratus_form` (baru): formulir Meratus dikenali dari STRUKTUR cetak:
  judul WAY BILL/BILL OF LADING di atas + heading "Shipper" di kiri atas (geometri yang sama dengan
  `meratus_layout`) + >= 3 frasa cetak khas (OCEAN FREIGHT AND CHARGES, As Agent for the Carrier,
  Shipped on Board the Vessel, Place and Date of Issued, No. of Original Bill, Final Destination for The
  Merchant's reference only, ...). Surat rujukan yang menyebut Meratus tetap dibaca sebagai surat.
- Tahap 2 ikut membaik (memakai fungsi deteksi yang sama).
- Tes baru: `test_meratus_reference_detection` (6 tes) + `synthetic_forms.py`. Kontrol negatif: tanpa aturan
  baru 3 tes gagal persis pada gejala di atas.

## Tidak diubah
Sel Meratus (BL/SWB), `extract`, profil lain, UI. Profil MSC/ONE/Maersk punya rute deteksi sendiri; bila logo
mereka juga grafis dan frasa cetaknya tidak ada di daftar tetap, gejala serupa mungkin muncul (belum ada sampel).

## Batas pengujian
PDF Meratus uji adalah REKONSTRUKSI dari tangkapan layar (PDF asli tidak tersedia bagi saya). Cek akhir:
buka rujukan Meratus Way Bill asli dan pastikan status bar tidak lagi menampilkan "field perlu verifikasi".

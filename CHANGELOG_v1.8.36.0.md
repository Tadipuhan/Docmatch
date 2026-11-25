# Changelog — DocMatch v1.8.36.0

## Added
- Modal **Pilih Jenis Dokumen Rujukan** pada Tab 1: `SWB` atau `Packing List (PL) + Shipping Instruction (SI)`.
- Dua kolom unggah PDF SI dan PL dengan validasi kedua file sebelum perbandingan.
- Modul `pl_si_reference.py`: parser offline berbasis label dan koordinat sumber SI/PL, serta viewer PDF gabungan sementara.
- Pemetaan SI untuk Booking, Shipper, Consignee, Notify Party, Loading, Destination/Discharge, Vessel/Voyage, Quantity, Cargo, Net/Gross Weight, Measurement, HS Code.
- Pemetaan PL untuk Container, Seal, Invoice No. dan Date; validasi silang Invoice No. antara SI dan PL.
- Pemeriksaan nilai Invoice Number, HS Code dan Net Weight dari deskripsi SWB (ketika tersedia), dengan pilihan field di Tab 2.
- Pembacaan lanjutan Shipper/Consignee/Notify Party pada halaman 2 SWB ONE dengan tag SH>, CN>, NP>.
- Metadata PL/SI dan fingerprint kedua sumber dalam sesi dan laporan JSON.
- Tes regresi khusus dengan tiga PDF contoh 26YA1A (tidak dibundel ke source).

## Changed
- Comparison dapat memakai record referensi SI/PL tanpa mengeksekusi profil koordinat SWB B pada file SI/PL.
- Catatan Koreksi menggunakan teks lengkap SI/PL, termasuk baris dan kapitalisasi, dengan prioritas terhadap edit manual.
- Penormalan whitespace pada alamat tetap mengabaikan pemecahan baris tetapi mendeteksi perubahan tanda baca seperti `CIAMPEL,` menjadi `CIAMPEL.`.
- Perbandingan berat mengenali KG/KGS dan M3/CBM tanpa menyamakan satuan massa lain yang berbeda.
- Tanggal PL ditampilkan sebagai metadata, **bukan** dibandingkan ke Date of Issue/On Board SWB.

## Preserved
- SWB reference normal dan SWB cross-carrier.
- Tab 2 header dynamic sizing, marker positioning, Catatan Koreksi langsung, ekspor PDF/DOCX/JSON, build AutoZIP/7z.
- Offline processing dan OCR/GSL decoder sebelumnya.

## Validation
- Tes fitur baru: 26 lulus.
- Semua regresi: 151 lulus, 59 skip, 1 gagal lama (Vessel rujukan Meratus).
- PySide6 GUI Windows dan PyInstaller executable belum diuji di runtime ini.

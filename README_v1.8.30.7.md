# DocMatch v1.8.30.7 — SWB / Bill of Lading MERATUS

## Perubahan
- Mode baru `SWB - MERATUS` di dropdown Mode Parameter.
- Daftar Field Waybill khusus MERATUS (28 field gabungan dua varian).
- Deteksi layout dari posisi heading `Shipper` pada halaman pertama:
  - **BL DRAFT** tradisional (satu halaman dalam contoh).
  - **WAY BILL** baru (tiga halaman dalam contoh, termasuk lanjutan dan Terms & Conditions).
- Pembacaan native PDF memakai koordinat relatif, dan pencocokan kata berdasarkan titik tengah bounding box.
- Crop dipisahkan dari teks syarat pengangkutan dan watermark agar tidak tercampur dengan nilai field.
- Pencarian kandidat region Tahap 2 mewarisi geometri MERATUS per varian.
- Mode ONE, MAERSK, GSL, ANL/CNC, EVERGREEN dan seluruh logika ekspor terdahulu dipertahankan.

## Panduan singkat
1. Pilih dua file PDF di halaman pertama.
2. Pilih `SWB - MERATUS` pada Mode Parameter.
3. Klik **Field Waybill** untuk mencentang field sesuai kebutuhan.
4. Klik **Bandingkan** dan tinjau penanda serta daftar temuan.
5. Koreksi bidang melalui Validasi Tahap 2 jika region bergeser pada template lain.

## Batasan dan pengujian
- Dua contoh PDF digital telah digunakan untuk kalibrasi (BL satu halaman dan SWB tiga halaman). Sampel PDF **tidak** dibundel ke ZIP.
- Nilai kosong tetap kosong; tidak diisi dari perkiraan atau teks formulir lain.
- Profil tidak otomatis mengenali scan gambar tanpa text layer. OCR fallback di aplikasi masih tunduk pada instalasi lokal Tesseract dan akurasi region.
- PDF Terms & Conditions halaman terakhir bukan bagian field halaman pertama.
- Perubahan layout lain perlu kalibrasi ulang dan pengujian tambahan.
- GUI Windows belum dapat diuji di lingkungan pembuat ZIP; uji startup, perbandingan dan ekspor langsung di Windows sebelum dipakai produksi.

## Tests
Jalankan `python -m pytest -q tests/test_meratus_profile.py`.
Uji yang memakai PDF akan di-skip jika tidak ada file contoh. Untuk pengujian lokal, letakkan **salinan yang diizinkan** dengan nama `meratus_bl.pdf` dan `meratus_swb.pdf` di `tests/fixtures/`.

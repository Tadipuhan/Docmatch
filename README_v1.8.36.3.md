# DocMatch v1.8.36.3 — Panel Tahap 1 & Tahap 2 Mengikuti Switch Sama

Versi ini adalah revisi **v1.8.36.2**. Kode perbandingan inti, Catatan Koreksi, dan fitur upload SWB / PL + SI tetap dipertahankan.

## Perubahan

Switch **Sama: ON/OFF** pada **Panel Pemeriksaan (Tab 2)** sekarang mengendalikan **dua viewer PDF dan kedua daftar hasil**:

| Mode | Tahap 1 | Tahap 2 | PDF |
|---|---|---|---|
| **Sama: ON** | Field yang terbukti cocok beserta nilai rujukan/diperiksa. Tidak ada checkbox koreksi. | Daftar field cocok (hanya baca); dapat klik untuk menuju halaman sumber. | Stabilo hijau pada nilai cocok; anotasi selisih tetap ada seperti versi sebelumnya. |
| **Sama: OFF** | Daftar perbedaan/perlu verifikasi dengan checkbox koreksi lama. | Daftar field berbeda; field yang telah punya anotasi Tahap 2 tetap memiliki checkbox penanda. | Stabilo hijau disembunyikan; penanda selisih tetap seperti sebelumnya. |

### Aturan keamanan

1. **ON tidak mengubah nilai pembanding atau menambah temuan koreksi.** Daftar nilai sama adalah hasil verifikasi matching, bukan perkiraan atau hasil OCR yang belum dipastikan.
2. Tidak ada checkbox *apply correction* di daftar nilai sama.
3. Nilai yang kosong, tidak terbaca, atau sedang ditandai berbeda tidak muncul sebagai cocok.
4. Switch dapat diubah tanpa menjalankan ulang **Bandingkan**, termasuk saat tetap ON sebelum klik Bandingkan ulang.
5. Saat OFF, pilihan checkbox temuan berbeda, anotasi, dan Catatan Koreksi tidak hilang.
6. Perbedaan filter Tahap 1 dipulihkan ketika kembali OFF; pencarian Tahap 2 dibersihkan ketika mode berganti.
7. Hasil yang sama beserta teks dan halaman PDF A/B disimpan dalam sesi baru; sesi v1.8.36.2 tetap dapat dibuka dengan daftar fallback nama field, tetapi detail teks sama mungkin perlu Bandingkan ulang.
8. Switch tidak otomatis menyetujui perubahan apa pun dari **Validasi Tahap 2**; proses validasi manual tetap terpisah.

## Contoh 26YA1A (Shipping Instruction + Packing List vs SWB ONE)

Untuk dua belas parameter utama yang diuji: **11 sama**, **1 berbeda** (`Shipper`, tanda baca). Saat ON, kedua tab menampilkan 11 nilai sama; saat OFF, Tahap 1 dan 2 menampilkan `Shipper` sebagai temuan.

## Instalasi

1. Ekstrak source lengkap v1.8.36.3 ke folder terpisah. Atau terapkan ZIP patch ke source v1.8.36.2 dengan struktur direktori yang sama.
2. Jalankan `py docmatch.py` pada lingkungan Python yang sudah memiliki dependensi.
3. Pilih dokumen A dan B, tentukan profil, kemudian klik **Bandingkan**.
4. Nyalakan **Sama: ON** untuk daftar kecocokan; matikan untuk kembali ke daftar koreksi.
5. Untuk portable Windows, jalankan kembali `build_portable.bat`. Arsip ZIP/7z otomatis versi sebelumnya tetap digunakan.

## Batasan pengujian

Pengujian otomatis source (termasuk simulasi dua tab, integritas checkbox, SI/PL/SWB 26YA1A) dilakukan di Linux. **GUI PySide6 Windows dan EXE portable belum diuji langsung** pada mesin Windows.

Tes lama pembacaan Vessel dari surat rujukan Meratus tetap gagal pada versi sebelumnya dan tidak terkait fitur panel.

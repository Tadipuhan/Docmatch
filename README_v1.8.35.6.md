# DocMatch v1.8.35.6 — Reference Cargo & Weight Formatting

## Tujuan
Penyempurnaan **isi otomatis Catatan Koreksi (Tab 3)** agar tiga kelompok Field Waybill mengikuti nilai lengkap pada **Dokumen Rujukan / PDF A**:

- **Container & Seal** (termasuk `Main - Container & Seal`): mempertahankan urutan container dan seal, baris berulang, karakter `/`, `-`, dan tanda baca yang dapat dibaca dari PDF.
- **Cargo Description** (termasuk `Main - Cargo Description`): mempertahankan isi deskripsi lengkap, huruf besar/kecil, spasi yang tersedia pada sumber, dan pergantian baris.
- **Weight & Measurement** (termasuk `Attached List - Weight & Measurement`; untuk carrier yang memisahkan nilai, `Gross Weight` serta `Gross Measurement`): mempertahankan angka, pemisah ribuan/desimal, unit seperti `KGS` / `CBM`, dan pergantian baris.

Field **Shipper, Consignee, Notify Party** tetap menggunakan perbaikan v1.8.35.5.

## Mekanisme
1. Setiap field tetap dibaca secara independen dari PDF A memakai pengenal layout carrier atau label pada surat rujukan.
2. Koordinat kata yang telah diekstrak digunakan untuk mengambil karakter asli dan menyusun kembali baris secara visual. Kolom terpisah yang berada pada satu baris tidak digabung sebagai dua paragraf.
3. Catatan pada Tab 3 memakai nilai field **lengkap**, bukan hasil penggabungan kata yang berubah satu per satu.
4. Catatan yang sudah diedit pengguna, baik per-temuan maupun per-grup, **tidak ditimpa**.
5. Jika teks yang terpilih kosong, tidak valid, atau memiliki indikasi kontaminasi jelas dari kolom lain, aplikasi mempertahankan catatan sebelumnya untuk ditinjau manual.
6. Ekspor PDF memakai teks catatan yang sama melalui modul `correction_note_layout.py`, termasuk enter dan spasi yang bisa dipulihkan.

## Batasan
- PDF mungkin tidak menyimpan spasi visual sama persis dengan tampilan cetak. Jarak antar-kolom yang hanya ditentukan oleh koordinat digambarkan sebagai pemisah yang dapat dibaca, bukan jumlah spasi yang pasti berasal dari PDF.
- Pada file scan, font Type3 yang tidak dapat didekode, atau OCR yang meragukan, sistem tidak boleh menebak nilai field. Periksa Catatan Koreksi secara manual.
- Kolom sumber yang sudah salah terdeteksi oleh mesin ekstraksi tidak otomatis diperbaiki oleh pembaruan format. Mode matching dan algoritme ekstraksi **tidak diubah**.
- Catatan panjang bisa dibungkus lagi mengikuti lebar kolom catatan PDF ekspor. Nilai dan karakter yang tersimpan tetap diprioritaskan.

## Cara mencoba
1. Ekstrak ZIP ke folder baru lalu jalankan `py docmatch.py`.
2. Pilih PDF A (rujukan) dan PDF B (diperiksa), pilih profil SWB, kemudian **Bandingkan** pada Tab 2.
3. Buka Tab 3 — **Hasil & Ekspor**, lalu periksa penomoran dan **Catatan Koreksi** untuk Container & Seal, Cargo Description, serta Weight & Measurement.
4. Pastikan semua nomor container dan seal tersusun berbaris, deskripsi tidak disatukan menjadi satu kalimat, angka serta unit tidak berubah.
5. Edit salah satu catatan secara manual, lakukan **Perbarui Preview**, dan ekspor `Koreksi_[Nama Dokumen Diperiksa].pdf` untuk memastikan perubahan pengguna dipertahankan.

## Pengujian
Tes unit mencakup surat rujukan fleksibel, beberapa container dalam baris berbeda, kolom pada baseline yang sama, nilai berat/measurement, override manual, pengaman kontaminasi, serta ekspor PDF nyata. Contoh PDF carrier milik pengguna tidak dimasukkan ke ZIP.

Regresi lintas-modul tetap memiliki satu kegagalan yang sudah ada sejak versi sebelumnya pada deteksi nilai `Vessel` surat rujukan Meratus. GUI Windows belum diuji secara langsung.

# DocMatch v1.8.36.2 — Switch Stabilo Nilai Sama

Versi ini melanjutkan v1.8.36.1 (perbaikan upload PL+SI) tanpa menghapus fitur sebelumnya. **Status cocok ditampilkan sebagai penanda visual, bukan tanda persetujuan atau koreksi.**

## Fitur

- Di Tab **2 Parameter & Bandingkan**, pada baris judul **PANEL PEMERIKSAAN** tersedia switch **○ Sama: OFF / ● Sama: ON**.
- **OFF (awal)**: hanya penanda ketidaksesuaian (warna merah/kuning/biru) dan penanda Tahap 2 sebelumnya.
- **ON**: menambahkan stabilo hijau tipis pada **nilai field yang terbukti cocok** di **Dokumen Rujukan (A)** dan **Dokumen Diperiksa (B)** sekaligus.
- Menekan switch **tidak menjalankan Bandingkan ulang**: posisi dan status pembacaan dari hasil perbandingan terakhir digunakan.
- Penanda hijau **tidak bernomor**, tidak menambah temuan, dan tidak membuat Catatan Koreksi baru.
- Highlight hijau hanya tersedia jika kedua sumber mempunyai teks yang terbaca dan koordinat PDF. Field kosong, tidak terbaca, atau **Perlu Verifikasi** tidak dianggap cocok.
- Berlaku pada **SWB ↔ SWB**, **SWB beda carrier**, dan **SI + PL → SWB**. Pada mode paragraf biasa, pencarian posisi sengaja ketat: hanya paragraf identik yang dapat ditemukan secara unik di kedua PDF yang ditandai hijau.
- Ketika ekspor **Waybill Rujukan Beranotasi** atau **Waybill Diperiksa Beranotasi**, switch ON juga mencetak stabilo hijau pada salinan PDF. OFF tidak menambah stabilo hijau. PDF **Hasil Koreksi dengan Catatan** tetap khusus temuan/koreksi, tidak diisi tanda hijau.
- Kondisi switch dan koordinat hasil yang sama disimpan di sesi baru; sesi lama tanpa informasi tersebut tetap dapat dibuka, tetapi tidak otomatis membuat koordinat hijau yang tidak tersimpan.
- Ekspor PDF hanyalah **salinan beranotasi**. PDF SI, PL, dan SWB asli tidak diubah.

## Contoh dari berkas 26YA1A

Dengan `SI 26YA1A.pdf`, `PL 26YA1A.pdf`, dan `SWB 26YA1A.pdf`, untuk 12 field utama yang dipilih:

- **11 field cocok**, antara lain Booking Number, Container & Seal, Quantity, Consignee, Notify Party, ports, vessel/voyage, cargo, berat, dan measurement.
- **1 field berbeda:** Shipper, karena penulisan `CIAMPEL,` pada SI tidak sama dengan `CIAMPEL.` pada SWB; tidak diberi hijau.
- Pemeriksaan tambahan Invoice No., HS Code, dan Net Weight juga dapat diberi hijau ketika field tersebut dipilih sebagai bagian perbandingan dan nilai serta koordinat valid.

Tampilan ini **tidak** menyatakan bahwa keseluruhan dokumen sudah disetujui. Setiap field yang belum punya padanan aman tetap memerlukan verifikasi.

## Cara mencoba

1. Jalankan `py docmatch.py` atau build portable versi baru.
2. Upload SWB rujukan atau SI+PL, lalu masukkan SWB diperiksa.
3. Pilih profil SWB Dokumen B dan klik **Bandingkan**.
4. Di **PANEL PEMERIKSAAN**, tekan **Sama: OFF** menjadi **Sama: ON**. Periksa hijau di kedua panel PDF.
5. Tekan lagi untuk menghilangkan hijau. Temuan merah serta Catatan Koreksi tidak berubah.
6. Bila diperlukan, ekspor **PDF beranotasi** dari Tab 3, dengan switch sebelumnya ON.

## Instalasi

- **Source lengkap**: ekstrak source ZIP v1.8.36.2 ke folder baru.
- **Patch**: dari source v1.8.36.1, timpa `docmatch.py`, `waybill_rules.py`, `pl_si_reference.py`, dan `build_portable.bat`; tambahkan `matched_values.py`. Lihat changelog dan tes tambahan.
- Jalankan `py docmatch.py` dari folder source. Untuk memperbarui **EXE portable**, jalankan `build_portable.bat` kembali.

## Keterbatasan pengujian

Unit test dan pemeriksaan posisi PDF telah dijalankan dengan file 26YA1A asli dan sampel pembanding. GUI PySide6 / EXE Windows belum dijalankan pada host ini; periksa visual switch pada Windows, terutama pada layar DPI tinggi. Satu regresi lama pada ekstraksi `Vessel` rujukan surat Meratus tetap ada dari v1.8.36.1.

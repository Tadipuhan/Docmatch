# DocMatch v1.8.36.0 — Rujukan SWB atau Packing List + Shipping Instruction

## Ringkasan

DocMatch sekarang menyediakan **dua jenis dokumen rujukan** pada Tab **1 Pilih Dokumen**:

1. **SWB**: unggah satu SWB rujukan. Mode lama, termasuk cross-carrier SWB, tetap tersedia.
2. **Packing List (PL) + Shipping Instruction (SI)**: unggah dua PDF secara terpisah, lalu pilih sebuah **SWB sebagai Dokumen Diperiksa**.

Seluruhnya diproses **offline**. SI dan PL asli tidak dimodifikasi. Aplikasi membuat PDF sementara untuk tampilan rujukan: **halaman SI terlebih dahulu, kemudian halaman PL**; penanda pada rujukan PL muncul di halaman PL, bukan di halaman SI.

## Cara menggunakan

1. Jalankan `py docmatch.py` dari folder proyek.
2. Buka **1 Pilih Dokumen**, klik **Pilih Dokumen Rujukan**.
3. Pada dialog baru, pilih **SWB — satu dokumen rujukan** atau **Packing List (PL) + Shipping Instruction (SI) — dua PDF**.
4. Untuk mode PL + SI, unggah file SI dan PL pada **dua kolom terpisah**. Keduanya harus PDF. Klik **OK**.
5. Klik **Pilih Dokumen Diperiksa** dan unggah SWB. Pilih preset shipping line SWB di Tab 2 (contoh: **SWB - ONE**). Bila preset belum dipilih, deteksi otomatis dapat mengisi preset ketika profil SWB B terbaca dengan yakin.
6. Pada **2 Parameter & Bandingkan**, pilih field yang diperlukan, lalu klik **Bandingkan**.
7. Tinjau hasil. Pada **3 Hasil & Ekspor**, Catatan Koreksi untuk Shipper/Consignee/Notify Party serta Container/Cargo/Weight memakai isi rujukan SI/PL. Koreksi manual tidak ditimpa.
8. Ekspor laporan dan PDF seperti versi sebelumnya.

### Contoh file uji dari pengguna

- `SI 26YA1A.pdf` — Shipping Instruction
- `PL 26YA1A.pdf` — Packing List
- `SWB 26YA1A.pdf` — SWB ONE yang diperiksa, terdiri dari dua halaman

Ketiga PDF tersebut **tidak dibundel** ke paket source karena merupakan dokumen pengguna. Apabila tersedia, file dapat dipakai menjalankan `pytest -q tests/test_pl_si_reference_18360.py`.

## Sumber rujukan untuk tiap parameter

| Parameter dibandingkan | Sumber |
| --- | --- |
| Booking Number / Booking No. | SI |
| Shipper | SI, multiline |
| Consignee | SI, multiline |
| Notify Party | SI, multiline |
| Port of Loading | SI |
| Port of Discharge (Port of Destination pada SI) | SI |
| Vessel / Voyage atau Vessel + Voyage Number | SI, `1st Carrier` |
| Quantity | SI, jumlah barang dalam Description of Goods |
| Cargo Description | SI, termasuk invoice dan HS Code yang tercetak di deskripsi |
| Net Weight | SI, dikroscek dengan data di Cargo Description SWB jika tersedia |
| Gross Weight | SI |
| Gross Measurement / Measurement | SI, M3 ↔ CBM setara |
| Container & Seal | PL, pasangan nomor container–seal |
| Invoice Number / Invoice No. | PL; nilai SI juga diperiksa konsistensinya |
| HS Code | SI; dikroscek dengan deskripsi SWB jika tersedia |
| Date pada PL | PL, **metadata saja**, bukan Date of Issue / On Board SWB |

**Aturan penting:** Tanggal `October 24, 2026` dalam PL **bukan** tanggal penerbitan SWB `04 NOV 2026`. Aplikasi tidak menganggap kedua tanggal tersebut sama. Field SWB yang tidak punya rujukan aman ditandai **Perlu Verifikasi**, bukan dinyatakan cocok.

Pada SWB ONE yang menerapkan tag `SH>`, `CN>`, dan `NP>`, alamat yang dilanjutkan ke halaman 2 dapat digabungkan ke field pihak yang benar untuk pembandingan. Penggabungan ini membutuhkan tag yang benar-benar ditemukan di PDF.

## Pemeriksaan pada tiga PDF 26YA1A

Nilai yang terbaca dari SI dan PL mencakup:

- Booking: `JKTG86701300`
- Shipper: `PT. BRIDGESTONE TIRE INDONESIA` beserta alamat hingga Tax ID
- Consignee: `BRIDGESTONE CORPORATION` beserta alamat, telepon, dan email
- Notify Party: `SBS TIRE FRONTIER CO., LTD.` beserta alamat dan kontak
- Loading: `JAKARTA, INDONESIA`; discharge: `TOKYO, JAPAN`
- Vessel/Voyage: `NAGOYA TOWER 033N`
- Quantity: `1,210 PIECES`
- Gross/Net: `17,388.650 Kgs`; Measurement: `65.6100 M3`
- HS Code: `4011.80-010`
- Container: `CAJU5672554`; Seal: `ID54061AB`
- Invoice: `26YA1A`; Tanggal PL: `October 24, 2026`

Semua field ini dapat dipulihkan dari sumber. Dalam perbandingan ketat ada **satu perbedaan tanda baca pada Shipper**: SI `CIAMPEL,` sedangkan SWB `CIAMPEL.`. Pergantian baris PDF, sebaliknya, tidak otomatis dinilai sebagai perubahan.

## Keamanan pembacaan dan keterbatasan

- Parser PL/SI disesuaikan pada **struktur SI dan PL 26YA1A yang dilampirkan** dengan deteksi label dan area field. **Belum diuji untuk semua layout SI/PL lain.** Jika label/koordinat bergeser jauh, hasilnya perlu verifikasi dan aturan ekstraksi tambahan.
- PDF scan tanpa lapisan teks **belum otomatis dibaca** oleh parser PL/SI ini; file tersebut perlu OCR atau validasi manual. Tesseract **tidak ditambahkan** sebagai dependensi baru untuk fitur PL+SI.
- Nama file tidak digunakan sebagai satu-satunya dasar deteksi nilai. Isi PDF dan posisinya tetap diperiksa.
- Jika Invoice No. SI bertentangan dengan PL, pengambilan rujukan ditolak dengan peringatan sampai sumber diperiksa.
- Jika satuan quantity/weight tidak dapat dipercaya, field ditandai Perlu Verifikasi. `KG`/`KGS` dan `M3`/`CBM` dikenali sebagai unit setara. Unit massa berbeda tidak otomatis disamakan.
- Catatan Koreksi mempertahankan huruf, tanda baca dan baris yang tersedia dalam lapisan teks PDF; jarak visual yang **tidak disimpan sebagai karakter** pada file PDF tidak bisa dipulihkan persis.
- Tanggal PL disimpan di status dan JSON, bukan dibandingkan dengan tanggal penerbitan SWB.
- Fitur marker dekat stabilo, Catatan Koreksi editable, PDF/DOCX/JSON, SWB lintas carrier, validasi tahap 2, dan AutoZIP/7z tetap tersedia.

## Build portable (Windows)

Source ini **bukan executable Windows**. Setelah dependensi proyek terpasang, jalankan:

```bat
build_portable.bat
```

Skrip yang sudah ada akan membuat `dist\DocMatch` dan (sesuai ketersediaan 7-Zip) `dist\DocMatch_Portable.zip` serta `dist\DocMatch_Portable.7z`. Tidak ada perubahan pada komponen Tesseract atau aturan kompresi portable dari v1.8.35.9.

Untuk mengarsipkan ulang build tanpa menjalankan PyInstaller:

```bat
py pack_portable.py
```

## Verifikasi

- Pengujian parsing SI dan PL, koordinat halaman gabungan, deteksi perbedaan nyata, validasi tambahan invoice/HS/net-weight, catatan setelah restore, dan alur UI source: **26 tes khusus lulus**.
- Regresi keseluruhan pada lingkungan pengembangan: **151 lulus, 59 dilewati, 1 gagal**. Kegagalan ada pada ekstraksi Vessel surat rujukan Meratus yang juga terjadi di source sebelumnya.
- Pengujian antarmuka PySide6 dan hasil PyInstaller Windows **belum dilakukan di lingkungan ini**. Uji langsung pada Windows sebelum mendistribusikan executable.

## File yang berubah

`docmatch.py`, `waybill_rules.py`, modul baru `pl_si_reference.py`, tes baru `tests/test_pl_si_reference_18360.py` dan `tests/test_pl_si_ui_source_18360.py`, README dan changelog. Modul OCR, engine export, pemampatan portable dan profil carrier lama tidak diganti.

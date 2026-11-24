# DocMatch v1.8.35.9

**Aplikasi Pembanding, Validasi, dan Koreksi Dokumen PDF — Offline**  
**Rilis:** v1.8.35.9 — *Cross-Carrier SWB & Header Layout Fix*

DocMatch adalah aplikasi desktop Windows untuk membandingkan nilai parameter dokumen rujukan (**Dokumen A**) dengan dokumen yang diperiksa (**Dokumen B**). Aplikasi menyediakan profil Field Waybill berdasarkan perusahaan pelayaran, pemeriksaan ketidaksesuaian, validasi ulang, penanda pada dokumen, Catatan Koreksi, dan ekspor hasil.

Versi **1.8.35.8** memungkinkan Dokumen A dan Dokumen B berasal dari SWB **shipping line berbeda**. Ekstraksi PDF A memakai profil A sendiri (otomatis atau manual), sedangkan field serta koordinat PDF B tetap mengikuti preset yang dipilih. Fitur build ZIP/7z otomatis dari v1.8.35.7 dipertahankan.

**Baru v1.8.35.9:** memperbaiki header Tab 2 yang terpotong akibat tinggi toolbar 58 px pada dua baris kontrol. Tinggi toolbar sekarang menyesuaikan halaman aktif dan DPI/font. Lihat `README_v1.8.35.9.md` dan `CHANGELOG_v1.8.35.9.md`. Kemampuan Cross-Carrier dari v1.8.35.8 tetap dipertahankan.

## 1. Fitur utama

**Baru v1.8.35.8:** di Tab 2, pilih profil Dokumen B pada Mode parameter, lalu pilih Deteksi Otomatis atau carrier pada "Profil Dokumen A (rujukan)". Lihat `README_v1.8.35.8.md` untuk tutorial, padanan field, dan batasan verifikasi.

- **Perbandingan PDF A dan PDF B:** periksa nilai Field Waybill sesuai mode yang dipilih.
- **Universal Reference Matching:** rujukan dapat memiliki susunan dokumen berbeda selama parameter dan nilainya dapat dikenali.
- **Profil SWB:** GSL, Evergreen, ANL/CNC/CMA CGM, ONE, MAERSK, MERATUS, dan MSC.
- **Validasi Tahap 2:** pemeriksaan dan koreksi hasil Tahap 1, termasuk OCR ulang untuk area yang membutuhkannya jika Tesseract tersedia.
- **Hasil & Ekspor:** preview dokumen diperiksa dengan highlight dan marker bernomor, Catatan Koreksi yang dapat diedit, serta ekspor PDF/DOCX/JSON sesuai fitur yang tersedia.
- **Format catatan dari rujukan:** Shipper, Consignee, Notify Party, Container & Seal, Cargo Description, dan Weight/Measurement menggunakan teks rujukan yang dapat dipulihkan; edit manual tetap diprioritaskan.
- **Penamaan PDF Catatan:** `Koreksi_[Nama Dokumen Diperiksa].pdf`.
- **Offline:** tidak membutuhkan layanan cloud untuk menjalankan fungsi yang telah dibundel.

> **Batasan:** Kemampuan membaca PDF scan atau font yang sulit didekode bergantung pada kualitas dokumen dan OCR. Layout yang berbeda tidak otomatis menjamin setiap field terbaca tanpa verifikasi.

## 2. Kebutuhan lingkungan

### Menjalankan source Python

- Windows dengan Python yang kompatibel dengan dependensi proyek.
- Paket yang tercantum di `requirements-build.txt`: `PySide6`, `PyMuPDF`, `python-docx`, dan `pyinstaller` (yang terakhir untuk build).
- File source proyek lengkap, termasuk `rules.py` dan modul-modul pembacaan/validasi.

### Membuat aplikasi portable

- Python dan akses instalasi paket sesuai `requirements-build.txt` **di komputer build**.
- Tesseract runtime lengkap pada folder `tesseract/` di root proyek; **skrip build versi ini masih mewajibkannya**.
- **7-Zip opsional**: diperlukan hanya jika ingin ZIP yang dikompres oleh 7-Zip dan file `.7z` LZMA2 solid.

Pengguna akhir tidak perlu menginstal Python secara terpisah untuk menjalankan hasil build **PyInstaller `onedir`** yang lengkap.

## 3. Struktur proyek yang relevan

```text
DocMatch/
├── docmatch.py                 # Titik masuk GUI
├── rules.py                    # Aturan dasar yang diperlukan
├── waybill_rules.py            # Profil pembacaan Waybill
├── flexible_reference.py      # Pembacaan rujukan lintas-layout
├── hybrid_validation.py       # Validasi Tahap 2
├── correction_preview.py      # Preview hasil koreksi
├── correction_note_layout.py  # Tata letak catatan koreksi
├── correction_markers.py      # Penanda/marker PDF
├── reference_note_format.py   # Format isi catatan dari rujukan
├── build_portable.bat          # Build EXE + auto archive
├── pack_portable.py           # Kompresi dan verifikasi arsip
├── requirements-build.txt
├── preflight.py
├── assets/
│   ├── docmatch.ico
│   ├── docmatch_logo.png
│   └── docmatch_128.png
└── tesseract/
    ├── tesseract.exe
    ├── tessdata/
    │   └── eng.traineddata
    └── ...                     # DLL/runtime pendukung
```

Struktur ini menampilkan **file utama**, bukan seluruh isi proyek. Jangan menghapus modul Python lain yang disertakan dalam source ZIP.

## 4. Menjalankan source untuk pengembangan

Buka **PowerShell** di folder source DocMatch, lalu jalankan:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe preflight.py
.\.venv\Scripts\python.exe docmatch.py
```

`preflight.py` hanya memeriksa ketersediaan file dan paket dasar; keberhasilan preflight **bukan jaminan** semua fungsi GUI, OCR, dan ekspor berjalan tanpa masalah.

## 5. Build portable + kompresi otomatis

1. Ekstrak **source lengkap** v1.8.35.7 ke satu folder.
2. Pastikan `requirements-build.txt`, `build_portable.bat`, `pack_portable.py`, seluruh source, `assets/`, dan Tesseract runtime berada pada lokasinya.
3. Buka **PowerShell** di folder proyek.
4. Jalankan skrip batch berikut **secara langsung**, bukan sebagai skrip Python:

```powershell
.\build_portable.bat
```

Skrip akan melakukan pemeriksaan source/aset, pemeriksaan Tesseract, membuat atau memakai `.venv`, menginstal dependensi build, memeriksa sintaks dan import, membuat paket PyInstaller `onedir`, menyalin Tesseract ke `_internal`, kemudian menjalankan `pack_portable.py`.

### Hasil yang diharapkan

```text
dist/
├── DocMatch/
│   ├── DocMatch.exe
│   └── _internal/
│       ├── assets/
│       ├── tesseract/
│       └── ...
├── DocMatch_Portable.zip
└── DocMatch_Portable.7z      # Hanya jika 7-Zip tersedia
```

`dist\DocMatch` **tidak dihapus atau dikurangi isinya** oleh proses kompresi. File arsip dibuat sebagai hasil tambahan di folder `dist`.

### Kompresi ulang tanpa menjalankan PyInstaller

Jika `dist\DocMatch\DocMatch.exe` beserta `_internal` sudah tersedia:

```powershell
py -3 pack_portable.py
```

Untuk membuat **ZIP saja**:

```powershell
py -3 pack_portable.py --skip-7z-archive
```

Untuk memaksa pemakaian kompresi ZIP bawaan Python (tanpa memanggil 7-Zip):

```powershell
py -3 pack_portable.py --no-7z
```

Jika `7z.exe` terpasang pada lokasi yang tidak terdeteksi otomatis:

```powershell
$env:DOCMATCH_7ZIP_PATH = 'C:\Program Files\7-Zip\7z.exe'
py -3 pack_portable.py
```

Skrip akan memeriksa daftar file dalam arsip, menguji CRC ZIP, dan menjalankan pengujian arsip 7z jika dibuat. Pemeriksaan arsip tidak menggantikan uji fungsional aplikasi.

## 6. ZIP vs 7z dan target ukuran

| Hasil | Kompresi | Penggunaan |
|---|---|---|
| `DocMatch_Portable.zip` | **Deflate level tinggi** (7-Zip jika tersedia; fallback Python level 9) | Paling mudah diekstrak dengan Windows |
| `DocMatch_Portable.7z` | **LZMA2 solid** | Alternatif untuk mencoba rasio kompresi lebih tinggi |

Pada pengujian sebelumnya, folder `dist\DocMatch` pengguna berukuran **sekitar 939 MB** dan kompresi ZIP manual menghasilkan **sekitar 443 MB**. Target **300-an MB adalah sasaran**, **bukan ukuran yang dijamin**. Arsip `.7z` mungkin lebih kecil, tetapi ukurannya harus diukur pada hasil build Windows sebenarnya.

Setelah diekstrak, ukuran folder portable akan kembali mendekati ukuran asli. Jangan sekadar mengganti ekstensi `.7z` menjadi `.zip`.

## 7. Menjalankan hasil portable di komputer lain

1. Salin `DocMatch_Portable.zip` atau `DocMatch_Portable.7z` ke komputer tujuan.
2. **Ekstrak semua file** terlebih dahulu; jangan menjalankan `DocMatch.exe` langsung dari dalam arsip.
3. Buka folder `DocMatch` hasil ekstraksi.
4. Jalankan `DocMatch.exe`.
5. Uji membuka PDF, membandingkan parameter, Validasi Tahap 2, preview koreksi, dan ekspor PDF.

**Penting:** pada build `onedir`, menyalin `DocMatch.exe` **saja** tidak cukup. Folder `_internal` beserta DLL, aset, dan runtime yang dibundel harus tetap menyertainya.

## 8. Troubleshooting

| Gejala | Kemungkinan penyebab / solusi |
|---|---|
| `SyntaxError` pada `@echo off` | Jangan jalankan `py build_portable.bat`; gunakan `.\build_portable.bat`. |
| `tesseract\tesseract.exe tidak ditemukan` | Lengkapi folder `tesseract/` di root proyek. Jangan hanya menyalin EXE tanpa DLL dan `tessdata`. |
| Bahasa `eng` tidak tersedia | Pastikan `tesseract\tessdata\eng.traineddata` tersedia dan perintah `tesseract.exe --list-langs` berhasil. |
| Import modul gagal | Periksa file source lengkap, `rules.py`, serta instalasi paket pada `.venv`. |
| `dist\DocMatch\DocMatch.exe tidak ditemukan` | Build PyInstaller gagal atau belum dijalankan; periksa log sebelum tahap kompresi. |
| ZIP dibuat tetapi `.7z` tidak ada | 7-Zip tidak ditemukan atau opsi `--skip-7z-archive` digunakan. ZIP tetap bisa didistribusikan. |
| Proses kompresi gagal | Periksa ruang disk, izin menulis ke `dist`, lokasi 7-Zip, dan log `pack_portable.py`. Folder `dist\DocMatch` tetap dipertahankan. |
| ZIP lebih besar dari 300 MB | Tidak selalu error: ukuran ditentukan kompresibilitas dependensi. Coba `.7z` dan ukur aktualnya. |
| EXE tidak berjalan pada PC lain | Pastikan seluruh isi folder portable diekstrak; uji dependensi runtime, keamanan Windows, dan hasil OCR/ekspor. |

## 9. Perubahan pada v1.8.35.7

- Menambahkan pengarsipan otomatis setelah proses build PyInstaller berhasil.
- Menghasilkan ZIP standar dan file 7z LZMA2 solid secara opsional.
- Mendukung kompresi ulang tanpa menjalankan PyInstaller.
- Memeriksa kelengkapan file dan integritas arsip.
- Tidak menghapus file, DLL, modul OCR, atau konten portable asli.
- Tidak mengubah mesin pembacaan atau tampilan aplikasi dari v1.8.35.6.

## 10. Batasan dan validasi sebelum distribusi

- Skrip **belum menjamin ukuran 300 MB**; ukur hasil pada komputer Windows tempat build dilakukan.
- Build masih **mewajibkan runtime Tesseract**. Versi ini **bukan** varian *Lite* tanpa OCR.
- Uji start-up GUI dan fungsi utama pada komputer Windows tujuan tetap diperlukan.
- Pada rangkaian pengujian source sebelumnya masih tercatat **satu kasus regresi terkait pembacaan field Meratus** yang perlu diverifikasi; v1.8.35.7 tidak dimaksudkan memperbaiki kasus itu.
- Simpan salinan versi yang sudah stabil sebelum mengganti source atau folder hasil build.

---

**Dokumentasi ini disusun berdasarkan `build_portable.bat`, `pack_portable.py`, `requirements-build.txt`, dan README/changelog yang tersedia dalam paket source DocMatch v1.8.35.8.**

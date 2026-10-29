# DocMatch v0.4 — Offline Selective Comparison

## Instalasi (Windows)

Python 3.10+ dan LibreOffice diperlukan untuk DOC lama, serta rendering DOCX menjadi PDF. Semua proses lokal.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python docmatch.py
```

## Aturan tertanam dalam rujukan

Letakkan tag sebagai **paragraf terpisah** (bukan bagian dari kalimat):

```
[DOCMATCH:START id="objek" mode="exact"]
Pihak Pertama menyediakan 25 unit komputer.
[DOCMATCH:END]

Nilai kontrak sebesar Rp150.000.000.
```

Hanya paragraf dalam tag yang dipilih pada mode *Tag dokumen saja*. Pilih *Gabungkan tag + pilihan aplikasi* untuk menambahkan pilihan lewat tombol **Pilih Paragraf Rujukan…**. Tag tidak ikut dibandingkan, tetapi masih dapat terlihat pada preview PDF asli.

Untuk memeriksa seluruh dokumen, centang **Periksa seluruh dokumen**.

## Keterbatasan yang harus diketahui

- Seleksi bekerja pada blok teks hasil ekstraksi, bukan koordinat pilihan mouse langsung pada kertas. Tombol pemilihan membuka daftar paragraf.
- Pencocokan target menggunakan ambang kemiripan konservatif. Bagian yang tidak terpetakan perlu ditinjau manual; tidak otomatis dikategorikan hilang.
- Parser PDF menggunakan blok ekstraksi PyMuPDF, sehingga batas paragraf dapat berbeda dari DOCX.
- DOC lama membutuhkan LibreOffice; PDF hasil scan membutuhkan OCR yang belum disediakan.
- Koreksi DOCX/PDF **membangun ulang teks** dan tidak mempertahankan semua format, gambar, tabel, dan tata letak. Jangan gunakan ekspor koreksi sebagai pengganti dokumen resmi tanpa pemeriksaan manual.
- Tag yang tampak pada dokumen rujukan akan tampak juga di preview karena preview menggunakan dokumen asli. Metadata tersembunyi DOCX belum diimplementasikan.
- Mode `exact` dan `normalized` pada tag diterima sebagai metadata tetapi belum menjadi strategi pencocokan yang berbeda.
- Ketidaksesuaian tambahan di luar cakupan sengaja tidak dilaporkan. Laporan JSON menyertakan bagian yang tidak diperiksa.

## Pengujian

```powershell
python -m unittest discover -s tests -v
```

Tidak memerlukan server, internet, atau unggahan dokumen.

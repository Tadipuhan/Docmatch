# DocMatch v0.1 — prototipe offline

## Menjalankan

Python 3.10+ diperlukan.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python docmatch.py
```

Untuk membaca `.doc` lama dan mengekspor PDF, instal **LibreOffice** dan pastikan `soffice`/`libreoffice` ada pada PATH. Pada Windows, tambahkan folder `C:\Program Files\LibreOffice\program` ke PATH jika diperlukan.

## Cara memakai

1. Pilih dokumen rujukan.
2. Pilih dokumen diperiksa.
3. Klik Bandingkan.
4. Centang perbedaan yang akan dikoreksi.
5. Ekspor DOCX/PDF dan laporan JSON.

## Batasan penting

- Ini MVP **berbasis blok teks**, bukan editor dokumen dengan pelestarian layout.
- Ekspor DOCX/PDF membuat **dokumen baru** dengan paragraf teks, tidak mempertahankan tabel, gambar, header/footer, font, dan format asal.
- DOCX: hanya paragraf utama yang dibaca; tabel, header/footer, catatan kaki belum diperiksa.
- PDF: hanya PDF dengan teks; hasil ekstraksi dapat berbeda dari urutan baca visual; OCR tidak tersedia.
- DOC: perlu LibreOffice lokal untuk konversi.
- Perbedaan dipasangkan menurut urutan dalam rentang perubahan; penyisipan/perpindahan blok besar dapat menyebabkan false positive atau koreksi salah.
- Jangan gunakan koreksi otomatis untuk dokumen hukum/keuangan tanpa pemeriksaan manual menyeluruh.
- Tidak ada akses jaringan atau unggahan dokumen dalam kode aplikasi.
"# Docmatch" 

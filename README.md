# DocMatch v0.3 — PDF tajam & stabilo transparan

## Perubahan dari v0.2
- Pratinjau PDF dirender dengan **supersampling 2×** dari ukuran tampilan; lebih tajam ketika di-zoom dan ditampilkan pada layar HiDPI.
- Penanda perbedaan berupa **stabilo semi-transparan** (alpha 65/255), sehingga tulisan di bawahnya tetap terbaca.
- Garis batas penanda tipis dan semi-transparan, nomor penanda dipindahkan ke atas area teks bila memungkinkan.
- Checkbox **Stabilo** di setiap viewer untuk mengaktifkan atau menyembunyikan anotasi.
- Zoom diperlihatkan di toolbar masing-masing viewer.

## Menjalankan di Windows
1. Instal Python 3.10+ dan LibreOffice untuk pratinjau DOCX/DOC.
2. Ekstrak paket, lalu di folder `docmatch_v0.3` jalankan:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python docmatch.py
```

## Pengujian
Buka dua PDF contoh, klik **Bandingkan Dokumen**, perbesar halaman, lalu hidupkan/matikan checkbox **Stabilo**. Pastikan teks tetap terbaca di bawah penanda merah dan hijau.

## Batasan yang belum berubah
- Pencocokan posisi teks masih berbasis `page.search_for` dan belum selalu akurat untuk teks berulang, terpotong baris, atau blok hilang.
- PDF scan tanpa text layer belum didukung (memerlukan OCR).
- Ekspor koreksi DOCX/PDF masih membuat ulang dokumen berbasis teks dan **tidak menjamin format asli**.
- Belum diuji secara interaktif dalam lingkungan ini (PySide6 tidak terinstal); pemeriksaan sintaks berhasil.
- Semua proses dilakukan secara lokal tanpa unggahan ke server.

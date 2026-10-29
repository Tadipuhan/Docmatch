# DocMatch v0.2 — Visual Document Audit (Offline)

## Instalasi (Windows)

1. Instal Python 3.10+ dan LibreOffice (tambahkan folder `program` LibreOffice ke PATH bila perlu).
2. Buka terminal di folder ini.
3. Jalankan:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python docmatch.py
```

## Fitur

- Antarmuka light: dua halaman dokumen berdampingan dan daftar perbedaan di kanan.
- Input DOCX, PDF, DOC lama. DOC lama memerlukan LibreOffice lokal.
- Pratinjau halaman berbasis PDF lokal, dengan penanda nomor dan kotak merah/hijau pada teks yang berhasil ditemukan.
- Navigasi ke halaman dari daftar perbedaan, filter jenis, dan checkbox koreksi.
- Ekspor hasil koreksi sebagai DOCX/PDF berbasis teks dan laporan JSON.
- Tidak menggunakan API jaringan atau mengunggah dokumen.

## Batasan penting

- Penanda visual bersifat *best effort* melalui pencarian teks PDF, **bukan** pemetaan semantik presisi; bisa salah posisi atau tidak muncul, khususnya pada teks berulang, line wrap, dan perubahan besar.
- Perbedaan dihitung pada tingkat blok, sehingga satu blok dapat mengandung beberapa perubahan kata/angka.
- Bagian hilang atau berlebih hanya dapat ditandai pada sisi yang memiliki teks; sisi yang kosong tidak diberi kotak lokasi semu.
- Ekspor koreksi **belum mempertahankan format asli**, tabel, gambar, header/footer, atau posisi halaman. Gunakan salinan dokumen dan periksa hasil sebelum dipakai resmi.
- PDF scan tanpa teks memerlukan OCR, belum tersedia.
- Konversi DOC/PDF dilakukan oleh LibreOffice lokal, tanpa koneksi jaringan.

## Pengujian

Jalankan dengan pasangan DOCX dalam paket contoh DocMatch. Klik item perbedaan untuk berpindah halaman, pilih koreksi melalui checkbox, lalu ekspor.

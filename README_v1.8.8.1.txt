DocMatch v1.8.8.1 — perbaikan serialisasi koordinat PDF

Akar masalah: GSL_DIAGNOSTICS menyimpan words dengan rect PyMuPDF.
Saat pemeriksaan selesai, json.dumps gagal dengan pesan Object of type Rect is not JSON serializable.

Perbaikan:
- Serialisasi koordinat Rect/IRect menjadi [x0,y0,x1,y1] pada file diagnostik OCR.
- Serialisasi Point dan Quad jika muncul.
- Terapkan serialisasi aman yang sama untuk ekspor laporan JSON.
- Objek Rect tetap utuh di memori untuk rendering dan highlight.

Catatan: Tidak ada perubahan pada algoritma OCR, ekstraksi field, atau tampilan.
Paket mengikuti struktur sumber v1.8.8; rules.py harus tetap tersedia dari proyek Anda.
Build executable Windows dan tes UI perlu dilakukan di komputer Windows.

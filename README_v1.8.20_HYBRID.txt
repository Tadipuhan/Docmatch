DocMatch v1.8.20 — HYBRID MANUAL VALIDATION (Prototype Integrasi)
=================================================================

FITUR BARU
- Tombol Manual Validation — Tahap 2 setelah perbandingan pertama.
- Viewer dua PDF independen dengan navigasi halaman, zoom, drag, move, resize kotak (8 handle).
- Ekstraksi ulang teks PDF digital dari kotak; pemulihan Type3 GSL jika memungkinkan.
- Pencarian kandidat PDF B lewat koordinat template yang sudah ada dan pencarian teks.
- Kandidat otomatis berwarna kuning sampai pengguna menekan Konfirmasi & Bandingkan.
- Fallback pemilihan kotak manual PDF B jika kandidat tidak cocok.
- Koreksi teks dan penyimpanan status MATCH, MISMATCH, PERLU_VERIFIKASI.
- Ekspor validasi tahap 2 sendiri sebagai JSON, serta terlampir dalam JSON laporan utama.
- Data tahap 1 tidak diubah oleh tahap 2.

BATASAN YANG WAJIB DIPERHATIKAN
- Pengujian dijalankan untuk sintaks/struktur source, bukan GUI Windows end-to-end.
- File rules.py TIDAK ADA pada ZIP v1.8.19 yang diunggah. Wajib disalin dari source
  DocMatch yang lengkap agar aplikasi bisa diimpor dan build sukses. Jangan buat stub.
- Folder tesseract portable juga tidak ada pada ZIP. Script build asli mewajibkannya.
- Tidak menambahkan engine OCR baru. PDF scan tanpa text layer dapat menampilkan
  kotak, tetapi teks hasil pembacaan tetap kosong sampai OCR diintegrasikan.
- Kandidat pencarian adalah usulan dan tidak otomatis divalidasi.
- Region GSL Type3 yang belum dapat dipulihkan dilaporkan PERLU_VERIFIKASI.
- Simpan hasil JSON sebelum menutup dialog; data tahap 2 di memori aplikasi tetap
  terjaga dalam satu sesi jika dialog dibuka lagi.
- Perlu uji nyata dengan PDF GSL/ANL/CNC, khususnya mapping koordinat,
  rotasi halaman, tabel multi-baris, dan toleransi karakter Type3.

MENJALANKAN
1) Tambahkan rules.py asli (dari source DocMatch yang sebelumnya bekerja).
2) Install requirements-build.txt pada environment yang kompatibel.
3) Jalankan: python docmatch.py
4) Pilih PDF A/B -> Bandingkan -> Manual Validation — Tahap 2.
5) Gambar kotak PDF A -> Cari Otomatis di PDF B.
6) Pilih kandidat atau gambar kotak PDF B -> edit teks jika perlu -> Konfirmasi.
7) Ekspor Validasi JSON atau kembali ke laporan utama.

PERUBAHAN FILE
- hybrid_validation.py (baru)
- docmatch.py (tombol, integrasi, penyimpanan hasil, laporan)
- build_portable.bat (menambahkan modul baru ke kompilasi dan PyInstaller)

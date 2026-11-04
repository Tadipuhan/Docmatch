DocMatch v1.6 - Windows Portable Build Kit

PENTING: Ini paket untuk MEMBANGUN .exe di Windows, bukan .exe siap pakai.

1. Siapkan Windows 10/11 64-bit, Python 3 yang kompatibel dengan dependensi, dan koneksi internet saat build.
2. Salin rules.py dari folder proyek DocMatch yang saat ini berhasil dijalankan ke folder kit ini. File tersebut tidak tersedia pada paket v1.6 yang diberikan.
3. Jalankan build_portable.bat.
4. Setelah sukses, salin SELURUH folder dist\DocMatch ke komputer lain, bukan hanya DocMatch.exe.
5. Uji PDF dan ekspor. DOC/DOCX memerlukan LibreOffice yang tersedia/terkonfigurasi pada komputer target; build ini TIDAK membundel LibreOffice.
6. Untuk distribusi benar-benar mandiri DOC/DOCX, perlu mengemas LibreOffice portable dan menyesuaikan fungsi libreoffice_convert di legacy_v01.py.

CATATAN: Build Windows harus dijalankan di Windows. Tidak ada klaim pengujian GUI atau exe di komputer pengguna.

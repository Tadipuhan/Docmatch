DocMatch v1.6 — Portable Build Kit (Perbaikan Dependensi)

PERBAIKAN:
- legacy_v01.py kini valid (merge conflict lama dibersihkan).
- build_portable.bat memeriksa keberadaan semua modul dan import sebelum build.
- PyInstaller memasukkan legacy_v01, rules, editor, waybill_rules sebagai hidden imports.

WAJIB SEBELUM BUILD:
1. Salin rules.py dari project DocMatch yang sebelumnya dapat dijalankan ke folder ini.
   rules.py tidak tersedia pada arsip source yang diberikan, sehingga TIDAK boleh dibuat-buat.
2. Pastikan Windows + Python 3 terpasang, lalu jalankan build_portable.bat.
3. Hasil ada di dist\DocMatch\DocMatch.exe; pindahkan SELURUH folder dist\DocMatch.
4. Uji .exe pada Windows, termasuk pembukaan PDF, perbandingan, dan ekspor.
5. DOC/DOCX tetap memerlukan LibreOffice. Build kit ini BELUM membundel LibreOffice.
   Jika terpasang di jalur nonstandar, set variabel lingkungan DOCMATCH_SOFFICE.

CATATAN: Ini kit untuk build di Windows, bukan .exe yang sudah dibangun/diuji.

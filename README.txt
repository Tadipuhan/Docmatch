DocMatch v0.8 — Waybill Export Patch

Ganti hanya docmatch.py pada folder source DocMatch. Pertahankan waybill_rules.py, legacy_v01.py, rules.py, editor.py.
Jalankan: py docmatch.py

WAYBILL PDF: salinan PDF diperiksa dengan stabilo transparan, layout halaman dipertahankan. Tidak mengganti teks secara otomatis.
WAYBILL DOCX: laporan temuan yang dapat diedit + lampiran gambar halaman Waybill beranotasi. Teks dalam gambar halaman tidak dapat diedit sebagai Word.

Catatan: jika ingin koreksi teks langsung pada Waybill sambil menjaga layout PDF asli, dibutuhkan modul penggantian teks berbasis koordinat dan verifikasi manual; belum tersedia pada patch ini.

Dependensi: python-docx, PyMuPDF, PySide6 (sudah digunakan proyek). Tidak perlu LibreOffice untuk ekspor Waybill PDF/DOCX dari PDF.

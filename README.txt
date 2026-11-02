DocMatch v1.0 — 4 Pilihan Ekspor PDF Waybill

INSTALASI
1. Backup docmatch.py dari proyek Anda.
2. Ekstrak ZIP ini dan timpa docmatch.py pada folder proyek DocMatch.
3. File lain (waybill_rules.py, editor.py, legacy_v01.py, rules.py) tidak berubah.
4. Jalankan: py docmatch.py
5. Untuk memperbarui EXE PyInstaller, build ulang setelah mengganti source.

EKSPOR PDF
- Rujukan Beranotasi: PDF rujukan + stabilo.
- Diperiksa Beranotasi: PDF diperiksa + stabilo.
- Hasil Koreksi Bersih: teks diperiksa diganti untuk perubahan satu token yang disetujui dan aman.
- Hasil Koreksi dengan Catatan: PDF diperiksa + stabilo + catatan koreksi mirip tulisan tangan di margin kanan.

Pilih satu: simpan PDF. Pilih beberapa: simpan ZIP.
Pilih Semua / Hapus Semua tersedia.

CATATAN PENTING
- Hanya temuan dengan checkbox persetujuan dicentang yang mendapat catatan koreksi.
- Semua stabilo perbandingan tetap terlihat, termasuk temuan yang belum disetujui.
- Catatan menggunakan font miring untuk kesan tulisan tangan, bukan handwriting asli.
- Catatan mengambil teks rujukan, bukan teks hasil edit manual.
- Untuk temuan Berlebih tanpa nilai rujukan, catatan menyatakan hapus teks berlebih.
- Jika catatan tidak muat pada margin, ekspor dibatalkan dengan pesan kesalahan.
- PDF catatan mempertahankan teks asli; hanya PDF koreksi bersih yang mencoba mengganti teks.
- Kode telah lulus pemeriksaan sintaks; belum diuji pada GUI Windows.

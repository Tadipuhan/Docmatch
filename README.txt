DocMatch v1.4 — Integrasi Logo dan Ikon Resmi

Isi: docmatch.py, assets/docmatch.ico, assets/docmatch_128.png, assets/docmatch_logo.png

Pemasangan source:
1. Backup docmatch.py lama.
2. Salin docmatch.py dan folder assets/ ke folder utama proyek.
3. Jangan hapus legacy_v01.py, rules.py, editor.py, waybill_rules.py.
4. Jalankan: py docmatch.py

PyInstaller (jalankan dari folder proyek):
pyinstaller --noconfirm --windowed --name DocMatch --icon assets/docmatch.ico --add-data "assets;assets" docmatch.py

Perubahan: ikon aplikasi, titlebar/taskbar, logo kecil pada header. Fitur perbandingan tidak diubah.
Catatan: build Windows belum diuji di lingkungan Windows; bila memakai .exe, rebuild diperlukan.

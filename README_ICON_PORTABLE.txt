DocMatch v1.6 - Portable branding update

Perubahan:
- Windows AppUserModelID untuk ikon taskbar DocMatch.
- Ikon DocMatch pada title bar dan aplikasi.
- Splash logo DM saat proses pembukaan aplikasi.
- Ikon DM pada file DocMatch.exe melalui PyInstaller --icon.
- Pemeriksaan keberadaan aset logo di build_portable.bat.

Cara build Windows:
1. Pastikan rules.py dari proyek lama tersedia di folder ini.
2. Jalankan build_portable.bat.
3. Jalankan dist\\DocMatch\\DocMatch.exe.
4. Distribusikan seluruh folder dist\\DocMatch, bukan hanya exe.

Catatan:
- Build belum dijalankan di Windows dalam lingkungan ini.
- Jika ikon lama tetap terlihat pada Explorer, coba rename exe atau refresh Windows icon cache.
- LibreOffice belum termasuk dalam paket portable ini.

DocMatch v1.8.22 — Verification Workspace (Tahap 2)
Baseline: DocMatch v1.8.21

IMPLEMENTASI
1) Sidebar hanya di sisi kanan. DAFTAR PARAMETER dan INSPECTOR VALIDASI adalah dua section collapsible independen (klik header untuk buka/tutup ke bawah).
2) Tombol "Sembunyikan Panel Kanan" menyembunyikan seluruh sidebar. Dokumen A/B otomatis menempati area tersisa. Tombol yang sama memunculkannya lagi.
3) PDF Tahap 2 diraster pada resolusi 2x dibanding ukuran layar, dengan devicePixelRatio 2. Koordinat seleksi tetap di unit PDF. Tombol "Lebar" per dokumen memberikan fit-width, selain zoom +/-.
4) Tahap 2 menerima status temuan dari Tahap 1 (untuk mode Waybill).
5) Jika hasil Tahap 1 telah diperiksa dan tidak ada perubahan, klik "Berikutnya" untuk mencatat VERIFIED_UNCHANGED dan pindah ke parameter berikutnya. Temuan aktif Tahap 1 tidak berubah.
6) Jika ada koreksi: pilih kotak A/B, periksa hasil, edit teks bila perlu, lalu klik "Konfirmasi & Perbarui Tahap 1".
7) Ketika dikonfirmasi pada mode Waybill, temuan aktif tahap 1 langsung dibangun ulang dari baseline: MATCH menghapus temuan parameter dari daftar aktif; MISMATCH mengganti dengan temuan validasi tahap 2. Tidak menciptakan duplikasi saat diperbaiki berkali-kali.
8) Baseline asli Tahap 1 tidak dimodifikasi dan dilampirkan dalam ekspor laporan JSON sebagai audit; file PDF asli juga tidak dimodifikasi.
9) Parameter dengan status PERLU_VERIFIKASI karena tidak terbaca tidak dapat dilewati via Berikutnya sebelum area/text diverifikasi.

BATASAN
- Pembaruan daftar temuan Tahap 1 secara langsung hanya diaktifkan untuk mode Waybill dengan identitas field. Mode dokumen umum masih menyimpan validasi terpisah karena tidak ada pemetaan field yang aman ke perbedaan paragraf.
- Rendering HiDPI dapat mempertajam PDF yang memiliki data visual cukup; scan sumber beresolusi rendah tidak dapat dipulihkan menjadi detail baru oleh pengaturan DPI.
- ZIP source asal tidak menyertakan rules.py. Masukkan rules.py dari instalasi DocMatch yang sebelumnya berhasil berjalan ke folder yang sama dengan docmatch.py.
- Untuk build Windows, dependency dari requirements-build.txt dan portable Tesseract (jika build script memerlukannya) tetap harus dipenuhi.
- Source sudah lolos kompilasi semua modul Python. Pengujian GUI Qt secara langsung belum dilakukan di lingkungan ini (PySide6 tidak terpasang).

CARA UJI
1. Backup instalasi lama; ekstrak ZIP ke folder baru dan salin rules.py yang dipakai versi aktif.
2. Jalankan aplikasi, pilih SWB GSL/ANL/CNC, muat dua PDF, dan jalankan Bandingkan Dokumen.
3. Buka Manual Validation — Tahap 2, periksa sidebar kanan, collapse dua section dan hide sidebar.
4. Pilih Waybill Number, periksa dua PDF, gunakan Berikutnya jika data tahap 1 benar.
5. Untuk field yang perlu koreksi, drag kotak PDF A/B, edit teks A/B, konfirmasi, lalu tutup dialog.
6. Pastikan daftar temuan Tahap 1 berubah sesuai status MATCH/MISMATCH; ekspor laporan JSON dan periksa original_differences.

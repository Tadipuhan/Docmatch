# DocMatch v1.8.33 — Independent Reference / Carrier Field Matching

## Tujuan
Dokumen **Rujukan (A)** boleh berupa surat atau tabel berbeda layout. Daftar parameter **tetap ditentukan oleh profil SWB Dokumen B**: ANL/CNC, Evergreen, GSL, ONE, Maersk, Meratus, atau MSC.

## Cara kerja
1. Pilih profil SWB dan field yang ingin dibandingkan pada menu **Field Waybill**.
2. Dokumen A otomatis diperiksa apakah merupakan surat/tabel dengan field berlabel eksplisit. Jika ya, ekstraksi label/nilai digunakan tanpa koordinat carrier. Jika dokumen A berupa carrier template sesuai profil, ekstraksi lama tetap digunakan.
3. Dokumen B diproses secara independen. Jika bentuknya carrier asli, modul akurasi carrier yang ada tetap digunakan. Dokumen B berlabel bebas juga didukung.
4. Field dibandingkan berdasarkan nama parameter dan alias terkontrol, bukan kesamaan posisi atau kemiripan angka saja.
5. Field yang tidak berhasil ditemukan pada dokumen berlabel **tidak dianggap MATCH atau MISMATCH**; tercatat sebagai **Perlu Verifikasi** di status (dan diagnostik rujukan), bukan dimasukkan sebagai perbedaan yang ditebak.
6. Hasil yang benar-benar berbeda tetap memakai penanda lokasi spesifik pada kedua PDF.

## Batasan yang disengaja
- Layout bebas berarti susunan visual boleh berbeda, **bukan** pembacaan universal dari semua bentuk PDF. Saat ini diperlukan label yang dikenali dan teks PDF yang dapat diekstrak.
- Dokumen scan tanpa text layer, tabel tanpa label, label ambigu, atau nilai yang tidak dapat dikaitkan dengan satu field memerlukan pemeriksaan/OCR manual.
- Nama field SWB dan field khusus carrier tidak diganti. Alias hanya digunakan pada pencarian nilai di surat.
- Tidak dilakukan fuzzy matching bebas antara nomor container, invoice, booking, port, atau nilai angka karena berisiko salah cocok.
- Input dan output tetap offline; PDF asli tidak diedit.
- Belum dilakukan pengujian GUI Windows pada lingkungan ini.

## Tes
- Regresi proyek: **43 lulus; 30 skipped** (fixture atau dependensi di luar bundel).
- Perbandingan surat tabel berbeda layout terhadap PDF carrier asli untuk ONE, MAERSK, MERATUS, MSC pada tiga field inti (Waybill Number, Port of Loading, Port of Discharge): 0 selisih palsu.
- Satu nilai sengaja diubah: tercatat `Perubahan` pada field yang sesuai.
- Rujukan hanya mengandung sebagian field: field lainnya masuk `REFERENCE_NEEDS_REVIEW`, bukan dianggap cocok.
- Surat satu field berlabel inline (`B/L No.: ...`): didukung.
- Decoder Type3 GSL, profil koordinat carrier, menu, dan layout tidak dimodifikasi.

## Penggunaan
1. Ekstrak ZIP ke folder terpisah.
2. Jalankan `py preflight.py` lalu `py docmatch.py`.
3. Pilih dua PDF dan profil SWB sesuai dokumen yang diperiksa.
4. Klik **Field Waybill** dan pilih parameter relevan.
5. Klik **Bandingkan**. Lihat temuan dan bagian `field perlu verifikasi` pada status jika nilai rujukan tidak dapat ditemukan.
6. Periksa bukti highlight dan lakukan validasi Tahap 2 bila diperlukan.

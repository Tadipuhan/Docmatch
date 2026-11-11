DocMatch v1.8.5 — Ekspor Catatan Koreksi per Field

Perubahan:
- Satu kotak catatan untuk tiap Field Waybill per halaman PDF, bukan per temuan.
- Satu garis penghubung dari field menuju kotak catatan.
- Catatan tiap temuan dalam field digabung dan teks identik tidak diulang.
- Preview edit kotak merah mengikuti pengelompokan yang sama. Edit kelompok disimpan
  di note_overrides dengan kunci group:<page>:<field>, tanpa mengubah catatan individu.
- Stabilo individual tetap dipertahankan sebagai bukti temuan.
- Penanganan catatan panjang dari v1.8.4 dipertahankan.

Catatan:
- Teks default disusun dari catatan koreksi tiap temuan, bukan rekonstruksi otomatis
  seluruh isi field dari dokumen rujukan. Periksa dan edit kotak gabungan sebelum ekspor.
- Pengujian: sintaks dan smoke-test 3 temuan Consignee menjadi 1 kotak berhasil.
- Build executable Windows dan pengujian GUI belum dilakukan di lingkungan ini.

Instalasi: cadangkan proyek lama, ekstrak ZIP, jalankan build_portable.bat
menggunakan lingkungan Tesseract yang sebelumnya sudah berhasil.

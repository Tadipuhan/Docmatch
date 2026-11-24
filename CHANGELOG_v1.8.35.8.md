# DocMatch v1.8.35.8 — Cross-Carrier SWB Reference Matching

Tanggal rilis source: 24 November 2026.

## Yang berubah
- Dokumen A (Rujukan) dan Dokumen B (Diperiksa) kini menggunakan **profil ekstraksi masing-masing** ketika A berupa SWB carrier lain.
- Mode **Deteksi Otomatis** untuk dokumen A (default), dan dropdown untuk memilih profil A secara manual jika deteksi tidak cukup pasti.
- Ketika A adalah surat/tabel referensi berlabel, mekanisme Universal Reference Matching tetap digunakan.
- Perbandingan menggunakan nama field yang dipetakan secara konservatif; misalnya `Main - Container & Seal` ↔ `Container & Seal`, dan `Final Place of Delivery` ↔ `Place of Delivery`.
- Field gabungan `Vessel / Voyage` dapat dipisahkan menjadi `Vessel` dan `Voyage Number` jika suffix voyage terbaca jelas; arah sebaliknya juga didukung.
- `Gross Weight` dan `Gross Measurement` dikenali pada field gabungan `Weight & Measurement` apabila nilai dan satuan dapat dipisahkan secara pasti.
- Pasangan nomor container+seal diperiksa bersama. Nomor container yang sama tetapi seal berbeda tidak boleh dianggap cocok.
- Field tanpa padanan tepercaya masuk daftar **Perlu Verifikasi**. Tidak dipaksakan sama dan tidak dikarang.
- Catatan Koreksi mengambil nilai dan susunan teks dari profil A yang sebenarnya; perubahan manual pengguna tetap diutamakan.
- Profil rujukan dan peta field ikut tersimpan dalam sesi / laporan audit.
- Modul `cross_carrier.py` diikutsertakan dalam build portable; tahapan ZIP/7z otomatis tetap sama dengan v1.8.35.7.

## Tidak berubah
- Seluruh preset yang sudah ada; layout Tab 2/3; mekanisme highlight/marker v1.8.35.4; format Catatan Koreksi v1.8.35.5–6; fungsi ekspor; mesin Type3 GSL; OCR opsional yang masih dipanggil Validasi Tahap 2.

## Batasan
- Dokumen A yang tidak memiliki bukti teks/form yang cukup (misalnya logo gambar atau PDF scan) **tidak ditebak profilnya**. Pilih profil A manual atau periksa dokumen secara manual.
- Tidak semua field antarshipping line punya padanan semantik; sebagian perlu diverifikasi, terutama istilah freight, attached list, tanggal penerbitan, final destination, dan field carrier-specific.
- OCR dan pembacaan tabel tergantung mutu dokumen; status hasil ekstraksi tidak berarti isi setiap bidang sudah pasti benar.
- GUI Windows / executable PyInstaller belum dijalankan di lingkungan pengujian Linux.
- Ada satu tes lama pada surat rujukan Meratus yang masih gagal pada source sebelum versi ini; perubahan ini tidak dimaksudkan memperbaiki masalah tersebut.

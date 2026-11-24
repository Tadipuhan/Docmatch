# DocMatch v1.8.34 — Inline Correction Review

## Perubahan alur

- **Langkah 2 — Parameter & Bandingkan:** tombol **Bandingkan** menjalankan perbandingan dan **tetap di langkah 2**. Viewer PDF A (rujukan), PDF B (diperiksa), dan Panel Pemeriksaan tetap tersedia untuk mengecek temuan. Tombol **Validasi Tahap 2** juga tersedia di bawah panel kanan.
- **Langkah 3 — Hasil & Ekspor:** dua viewer digantikan oleh **satu preview dokumen diperiksa** dengan kolom **CATATAN KOREKSI** di margin kanan. Tampilan memakai writer vektor yang sama dengan berkas PDF `Waybill_Hasil_Koreksi_Catatan` yang telah digunakan sebelumnya.
- **Edit langsung di kolom merah:** klik isi catatan, ubah teks, dan perubahan langsung tersimpan di `note_overrides` serta autosave sesi (ketika dokumen A/B tersedia). Ini bukan pengeditan permanen pada PDF asli.
- **Perbarui Preview:** hitung ulang ukuran kotak dan pemenggalan baris setelah perubahan teks yang panjang.
- **Semua temuan** (default) menampilkan setiap temuan yang memiliki posisi di PDF B. Nonaktifkan untuk menampilkan hanya temuan yang dicentang pada daftar Tahap 1.
- **Ekspor PDF Catatan…** pada preview mengekspor isi catatan terbaru seperti yang terlihat. Dari ribbon **Ekspor PDF**, pilihan PDF Catatan menjadi default saat berada pada Langkah 3 dan ada temuan dengan posisi.
- Tombol **Lebar**, **+**, **−**, serta navigasi halaman tersedia di preview tunggal.

## Yang tidak berubah

- Mesin ekstraksi dan pemetaan profil GSL, ANL/CNC/CMA CGM, Evergreen, ONE, MAERSK, MERATUS, dan MSC.
- Perbandingan dan logika `WaybillDifference`.
- Validasi Tahap 2 serta PDF asli yang tidak pernah ditimpa ketika menambahkan catatan.
- Semua format ekspor sebelumnya masih tersedia.

## Penggunaan

1. Pilih PDF A dan PDF B.
2. Pada langkah 2, pilih mode SWB dan klik **Bandingkan**. Hasil perbandingan tetap di langkah 2; centang temuan yang ingin ditinjau atau validasi kembali.
3. Klik **3 Hasil & Ekspor**. Satu PDF diperiksa ditampilkan dengan catatan di sebelah kanan.
4. Ketik langsung di dalam kotak catatan. Klik **Perbarui Preview** apabila teks telah menjadi lebih panjang.
5. Klik **Ekspor PDF Catatan…** untuk menyimpan hasilnya. Buka kembali tab 2 bila perlu mengubah pilihan atau validasi.

## Batasan

- Editor catatan langsung berlaku pada **profil SWB**. Mode umum hanya menampilkan preview tunggal dokumen diperiksa tanpa kotak edit Waybill.
- Temuan tanpa posisi highlight pada dokumen diperiksa tidak dapat digambar dengan garis penghubung; pemeriksaan manual masih diperlukan.
- Ketika dokumen cocok 100% dan tidak ada temuan, langkah 3 tetap menampilkan dokumen diperiksa tanpa catatan.
- PDF yang diekspor tetap berupa **salinan beranotasi**; penggantian konten PDF asli memerlukan tindakan berbeda.
- Testing GUI Windows masih harus dijalankan. Lingkungan build ini tidak menyediakan PySide6.

## Pengujian

- `python -m pytest -q tests/test_correction_note_layout.py tests/test_review_navigation_source.py tests/test_review_pdf_writer.py`
- `python tests/run_tests.py`
- Pada suite lama terdapat satu kegagalan yang **sudah terjadi pada v1.8.33.3**: ekstraksi `Vessel` pada surat Meratus berlayout fleksibel; perbaikan pembaca itu sengaja tidak dicampur ke rilis UI ini.

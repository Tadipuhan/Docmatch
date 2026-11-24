# DocMatch v1.8.35.1 — Numbered Marker Only / Original Correction Notes

Revisi terbatas di atas v1.8.35 atas permintaan pengguna.

- **Hasil Koreksi:** pertahankan highlight nilai dan badge nomor (#01, #02, dst.) tanpa garis penghubung, mengikuti ekspor PDF v1.8.35.
- **Catatan Koreksi:** kembalikan `correction_preview.py` **identik** dengan v1.8.34. Editor catatan tetap berupa kotak teks langsung di margin kanan PDF hasil koreksi, dengan semua catatan terlihat, tanpa accordion.
- Perubahan catatan tersimpan ke `note_overrides` saat diketik, bisa dipreview ulang dan diekspor.
- Preview dan ekspor memakai pembuat PDF yang sama, sehingga penanda dan catatan mengikuti nilai yang terbaru.
- Tab 2 tetap menampilkan hasil setelah Bandingkan; tidak otomatis berpindah ke Tab 3.
- `waybill_rules.py`, OCR, aturan carrier dan mesin matching tidak berubah dari v1.8.35.
- Tidak mengembalikan **garis penghubung** karena tujuan update hanya membuat penanda tanpa garis.

Pengujian desktop GUI Windows belum dijalankan dalam lingkungan ini; lakukan uji edit catatan serta ekspor setelah menjalankan source.

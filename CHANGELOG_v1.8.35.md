# Changelog v1.8.35

- Hapus garis konektor merah antara highlight dokumen dan catatan koreksi.
- Tambah badge #01/#02/#03 pada posisi teks dokumen diperiksa.
- Highlight dokumen dan kartu catatan tetap memiliki ID temuan yang konsisten.
- Tab 3 kini menampilkan satu PDF di kiri serta panel Accordion Catatan yang
  dapat diperluas dan diedit di kanan.
- Nilai Saat Ini (read-only), Nilai Koreksi (editable), Batal, Simpan Perubahan.
- Klik bukti/nomor pada PDF membuka entri accordion yang relevan.
- Pratinjau menggunakan bagian dokumen dari PDF hasil ekspor agar penanda sama;
  PDF ekspor menyertakan catatan di margin kanan tanpa garis.
- Tambah modul `correction_markers.py`, update skrip portable dan tes regresi.
- Semua aturan ekstraksi/carrier dipertahankan dari v1.8.34.

# v1.8.33 — Universal Reference (label-based)
- Generalisasi flexible-reference reader dari GSL ke seluruh profil Waybill tanpa mengubah daftar field tiap carrier.
- Pilih reader secara independen untuk PDF A dan B berdasarkan bentuk dokumen yang dikenali.
- Tambahkan alias label terkendali untuk BL/SWB, rute, kapal, barang, berat, dan beberapa attached-list.
- Dukungan surat berlabel tabel dua kolom, field bernilai di baris berikutnya, dan `Field: Value`.
- Cegah false-MATCH ketika field rujukan tidak ada; catat `REFERENCE_NEEDS_REVIEW`.
- Perbandingan lintas-layout menggunakan nilai field lengkap, mengabaikan perbedaan pembungkus baris dan spasi.
- Pertahankan mesin GSL Type3 dan penentu koordinat semua SWB.
- Tambahkan regression tests untuk ONE, MAERSK, MERATUS, MSC dan partial-field.

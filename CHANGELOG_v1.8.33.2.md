# DocMatch v1.8.33.2 — Presisi nilai & kotak SWB ANL/CNC/CMA CGM

Dibangun di atas v1.8.33.1. UI, layout visual, Universal Reference Matching, dan profil
GSL/ONE/Maersk/Meratus/MSC/Evergreen **tidak diubah**.

## Akar masalah (terbukti pada kode v1.8.33.1 + 3 formulir nyata)
1. **Caption cetak ikut menjadi nilai.** Kotak profil ANL mencakup baris caption, sehingga nilai
   menjadi "PORT OF LOADING JAKARTA, INDONESIA", "VOYAGE NUMBER 0SQ5AN", "KGS KGS CBM 8455.454 ...",
   dan kotak penanda menutupi caption. Akibatnya nilai yang SAMA dilaporkan BERBEDA
   (Port of Loading pada surat uji vs formulir: false MISMATCH).
2. **Place & Date of Issue**: caption berada di baris yang sama dengan nilai; kata liar "and" dari baris
   klausa di dekatnya ikut terbaca.
3. **Kolom badan tabel** membaca baris "Shipped on Board ...", "... As agents for the Carrier" dan footer
   "Weight in Kgs Total: N CONTAINER(S)". Batas bawah tabel memakai angka tetap padahal footer berpindah
   (y .649 pada 1 kontainer, .658 pada 2-3 kontainer).
4. **Additional Clauses** menyertakan syarat cetak di bawah kotak dan membaca dua kolom berselang-seling.
5. **Rujukan berlayout berbeda**: "17,800.000 KGS / 100.500 CBM" di surat vs kolom Gross/Tare/Measurement
   di formulir tidak pernah bisa cocok; sel tabel rujukan yang panjang (>65 pt) terpotong.
6. Penanda rujukan menutup seluruh baris nilai, bukan hanya kata yang berbeda.

## Perubahan
- `anl_form.py` (baru): ekstraksi formulir ANL/CNC/CMA CGM. Kotak NILAI terukur (di antara caption dan
  nilai), pembuangan baris caption berdasarkan teks, jangkar baris footer untuk batas bawah tabel,
  total berat dari baris footer (`semantic_text`/`semantic_words`), klausa per kolom, urutan baca deterministik.
- `anl_semantics.py` (baru): kesetaraan nilai untuk Weight & Measurement (angka, locale koma/titik),
  Container & Seal (himpunan nomor kontainer & seal), Place & Date of Issue (tanggal dari berbagai format),
  Number of Original Waybills. Bagian yang hanya ada di satu sisi tidak dianggap berbeda; yang tak dapat
  diurai -> perbandingan teks biasa (tidak menebak).
- `waybill_rules.py`: `FIELDS` kini dari `anl_form.ANL_FIELDS` (nama & urutan sama); `extract` ANL memakai
  `anl_form`; perbandingan rujukan fleksibel pada profil ANL memakai `anl_semantics` dan kata individual.
- `flexible_reference.py`: parameter opsional `word_level` (kotak per kata) dan pembacaan nilai tinggi yang
  mengikuti jeda antar-baris; keduanya HANYA aktif untuk profil ANL (default tidak berubah).
- `hybrid_validation.py`: Tahap 2 untuk ANL memakai aturan titik-tengah-kata.
- `build_portable.bat`: modul baru terdaftar.
- Tes baru: `test_anl_semantics`, `test_anl_form_extraction`, `test_anl_reference_layouts`,
  `ref_letters.py`, `pdf_shim.py` (pengganti PyMuPDF tipis HANYA untuk lingkungan tanpa PyMuPDF).
  `test_anl_cnc_fields.py` lama dihapus (digantikan). `test_gsl_stage1_integration`: stub diperbaiki
  untuk deteksi rujukan fleksibel v1.8.33 (gagal sebelumnya di lingkungan tanpa PyMuPDF).

## Yang TIDAK diubah / batasan
- Kotak Tahap 2 untuk ANL memakai batas statis (nilai saja) tanpa jangkar footer; pada formulir dengan
  baris "Shipped on Board" panjang kata "-" di kolom berat dapat terbaca pada Tahap 2.
- Field yang tidak ada pada surat rujukan tetap "Perlu Verifikasi" (tidak ditebak).
- Hanya 3 formulir carrier (ANL x2, CNC x1) yang diverifikasi; layout CMA CGM lain belum tersedia.

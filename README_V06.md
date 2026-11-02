# DocMatch v0.6 — Editor Manual

## Baru
- Tombol **Edit Hasil Koreksi** pada panel kanan, membuka editor teks langsung di aplikasi.
- Editor mendukung pengetikan dan penggantian isi, undo/redo bawaan QTextEdit, serta stabilo kuning pada paragraf yang berubah selama pengeditan manual.
- Simpan Perubahan menyimpan edit dalam sesi aplikasi. **Ekspor DOCX/PDF** menyimpan hasil edit ke berkas. DOCX diberi stabilo kuning untuk paragraf yang berubah dibanding dokumen yang diperiksa.
- Batal menutup dialog tanpa menerapkan perubahan yang baru diketik.
- JSON mencatat apakah editor manual digunakan.

## Cara menjalankan
`pip install -r requirements.txt` lalu `python docmatch.py`.
Untuk DOC/DOCX dan ekspor PDF diperlukan LibreOffice terpasang atau runtime yang dibundel sesuai petunjuk README_PORTABLE.md. PDF vs PDF dapat diproses tanpa LibreOffice untuk pratinjau.

## Batasan
- Editor merupakan **editor teks hasil koreksi**, bukan editor tata letak PDF asli.
- Ekspor DOCX dibuat ulang dan belum mempertahankan tabel, gambar, header/footer, font, atau posisi elemen dokumen sumber.
- Penandaan dalam DOCX menggunakan stabilo paragraf kuning, bukan anotasi koordinat yang sama seperti viewer PDF.
- Perubahan manual yang belum diekspor hilang jika aplikasi ditutup; ekspor sebelum keluar.
- Jika pemilihan koreksi diubah setelah editor dibuka, hasil editor yang sudah disimpan tidak otomatis dihitung ulang. Gunakan tombol reset di editor untuk kembali ke snapshot koreksi otomatis saat editor pertama kali dibuka.
- Paket ini adalah source/build kit, **belum** menyertakan binary LibreOffice atau EXE Windows.

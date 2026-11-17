DocMatch v1.8.24 — One-Click Auto Verification (Tahap 2)

Perubahan dari v1.8.23:
- Klik parameter di sidebar otomatis mencari kandidat koordinat pada PDF A dan PDF B.
- OCR region pada kedua sisi dijalankan oleh background QThreadPool dengan dokumen PyMuPDF terpisah.
- OCR otomatis hemat CPU: grayscale, PSM 6 dan 11. OCR lengkap warna/grayscale PSM 6/7/11 tetap tersedia lewat tombol OCR Ulang Area A/B.
- Inspector menampilkan kandidat OCR A/B, disertai tombol Gunakan OCR A/B; nilai tidak dipromosikan otomatis ke Tahap 1.
- Cache hasil per parameter selama dialog aktif; Analisis Ulang untuk pemrosesan ulang.
- Pengguna tetap dapat drag/resize kotak pada A/B sebagai fallback.
- Berikutnya mempertahankan Tahap 1; pada indikasi OCR berbeda, pengguna diminta memastikan dulu.
- Koreksi harus dikonfirmasi dengan tombol Konfirmasi & Perbarui Tahap 1.
- Hasil sebelumnya tetap tersimpan untuk audit.

Batasan:
- Pencarian lokasi otomatis paling andal pada profil waybill dengan _profile_cells dalam waybill_rules.py. Pada dokumen non-waybill, pencarian memakai teks Tahap 1 dan bisa gagal jika teks tidak mirip; gunakan seleksi manual.
- OCR dapat meleset pada font sangat kecil dan scan buram. Skor Tesseract tidak sama dengan probabilitas kebenaran.
- Source ZIP tidak memuat rules.py yang diperlukan docmatch.py dari baseline sebelumnya. Tambahkan kembali file tersebut dari distribusi yang berfungsi.
- Pengujian syntax Python selesai; pengujian GUI langsung di Windows belum dilakukan.

Instalasi: jalankan pada salinan terpisah dari versi produksi; pasang dependencies dan Tesseract eng.traineddata seperti versi sebelumnya.

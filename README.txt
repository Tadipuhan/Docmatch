DocMatch v1.3 — Catatan koreksi satu baris penuh

Perubahan:
- Catatan koreksi default mengambil satu baris asli dari PDF diperiksa.
- Hanya frasa/kata yang berbeda yang diganti dengan nilai rujukan.
- Contoh: PT BRIDGESTONE TIRE INDONESIA -> PT. BRIDGESTONE TIRE INDONESIA.
- Editor visual kotak merah v1.2 dan ekspor PDF tetap digunakan.
- Bila frasa tidak bisa dipetakan secara unik ke satu baris, fallback tetap teks rujukan agar tidak mengarang konteks.
- Catatan yang sudah diubah manual (note_overrides) tidak ditimpa.
- OCR/JPG/PNG belum ditambahkan.

Instalasi:
1. Backup docmatch.py lama.
2. Ganti docmatch.py dari ZIP ini pada folder proyek.
3. Biarkan waybill_rules.py, legacy_v01.py, rules.py, editor.py dan dependensi lain tetap berada di folder yang sama.
4. Jalankan: py docmatch.py
5. Lakukan pemeriksaan ulang, lalu buka Preview & Edit Catatan Koreksi.

Catatan: perubahan kode lolos py_compile dan uji logika sederhana, tetapi GUI Windows dan PDF nyata belum diuji end-to-end.

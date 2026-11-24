# DocMatch v1.8.35 — Penanda Bernomor + Accordion Catatan

Versi ini didasarkan pada **v1.8.34**. Perubahan hanya di tampilan Tab 3,
PDF hasil koreksi, dan jalur build yang menyertakan modul penanda baru.
Tidak ada perubahan pada aturan pembacaan GSL/ANL/ONE/Maersk/Meratus/MSC/Evergreen.

## Penggunaan

1. Buka dokumen di langkah **1 Pilih Dokumen**.
2. Pilih mode SWB, field, lalu klik **Bandingkan** di langkah **2**.
   Hasil tetap berada pada langkah 2.
3. Buka **3 Hasil & Ekspor**.
4. PDF yang diperiksa ditampilkan di sebelah kiri, dengan highlight teks dan
   badge **#01, #02, ...** pada posisi nilai yang diperiksa. Tidak ada garis
   penghubung ke panel kanan.
5. Panel **Catatan Koreksi** di sebelah kanan memakai accordion. Klik judul
   catatan atau badge pada PDF untuk membukanya. Lihat nilai asli PDF,
   ubah nilai koreksi, lalu klik **Simpan Perubahan** (atau **Batal**).
6. Klik **Perbarui Preview** jika perlu; **Ekspor PDF Catatan** untuk menyimpan
   PDF dengan penanda bernomor dan catatan di margin kanannya.

## Detail dan batasan

- Penanda dan kotak highlight mengikuti koordinat *exam_marks* dari perbandingan,
  **bukan** pemetaan posisi dari dokumen rujukan. Profil GSL halaman pertama
  mempertahankan batasan koordinat presisi yang sudah dikalibrasi sebelumnya.
- Satu field pada satu halaman menghasilkan satu catatan dan satu badge. Jika
  ada beberapa perubahan dalam satu field, nomornya digabung, misalnya #03,#04.
- Checkbox `Tampilkan semua temuan` mempertahankan fungsi seleksi dari v1.8.34.
- Catatan diperbarui pada model data ketika disimpan; naskah PDF sumber tidak
  diubah. Teks yang belum disimpan akan dikomit ketika pengguna menekan
  Perbarui Preview atau Ekspor.
- PDF ekspor menyertakan kartu catatan di margin kanan, tetapi **tanpa garis
  yang menghubungkan** kartu dan teks. Kontrol accordion hanya ada di aplikasi,
  bukan widget interaktif di PDF hasil ekspor.
- Pengujian GUI Windows diperlukan untuk memverifikasi penyesuaian ukuran jendela,
  navigasi halaman, klik badge, dan input accordion.

## Run

```powershell
py docmatch.py
```

## Pengujian

```powershell
py -m pytest tests -q
```

Diketahui pada baseline v1.8.34 terdapat satu pengujian ekstraksi rujukan
Meratus sintetis yang gagal (`test_letter_that_mentions_meratus_is_still_a_flexible_reference`).
Kegagalan yang sama masih ada dan tidak disebabkan perubahan penanda.

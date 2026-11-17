DocMatch v1.8.18 — Audit 20 Field GSL Halaman Pertama

Perubahan:
- Koreksi koordinat kotak Forwarding Agent dan Remarks yang sebelumnya tumpang tindih.
- Koreksi koordinat Freight Payable At dan Place & Date of Issue agar nilai SINGAPORE dan JAKARTA terambil.
- Tambahkan audit_gsl_page1() di waybill_rules.py untuk memeriksa 20 field dan mengklasifikasi SAMA, BERBEDA, KOSONG_KEDUANYA, PERLU_VERIFIKASI.
- Lampiran GSL_20_Field_Audit_Sample.json berisi hasil pemeriksaan dua PDF contoh, bukan hasil OCR.

BATASAN: 4 dari 20 field masih memuat karakter Type3 belum terpetakan (Notify Party, Remarks, Main - Cargo Description, Place & Date of Issue). Jangan gunakan nilai parsial sebagai dasar koreksi otomatis.
Pengujian: sintaks Python dan audit ekstraksi dua PDF sampel. GUI Windows/ekspor tidak diuji.

Instalasi: backup source; salin file Python dalam paket ke folder DocMatch; rebuild exe portable bila diperlukan.

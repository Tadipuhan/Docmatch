# Changelog — DocMatch v1.8.36.2

## Added
- Switch checkable `Sama: OFF/ON` pada panel pemeriksaan Tab 2. Satu switch mengontrol dua viewer PDF.
- Stabilo hijau per-kata/per-nilai pada field SWB yang diverifikasi cocok di sisi A dan B; tanpa marker bernomor dan tanpa entri koreksi.
- Pengumpulan koordinat nilai sama secara opsional melalui `compare_waybills(..., matched_locations=[])`, **tanpa mengubah return contract** dua objek versi sebelumnya.
- Dukungan catatan cocok dari `additional_claims` (Invoice, HS Code, Net Weight) pada PL+SI.
- Pencocokan paragraf identik posisi-unik pada mode non-Waybill.
- PDF pemeriksaan beranotasi menyertakan hijau saat switch ON; export match-only dimungkinkan.
- Simpan/pulihkan switch dan kotak hijau di berkas sesi, dengan fallback kompatibel untuk sesi lama.

## Preserved
- Pembacaan SWB lintas carrier dan rujukan SWB atau PL+SI.
- Marker merah/kuning/biru bernomor, hasil perbandingan, daftar temuan, Tahap 2, dan Catatan Koreksi editable.
- Ekspor PDF Catatan Koreksi tidak dipenuhi penanda hijau.
- `build_portable.bat` tetap membuat ZIP dan, jika 7-Zip terpasang, 7z otomatis.

## Testing
- Tes independen untuk hasil 26YA1A nyata, error/sumber tidak terbaca, perbandingan API lama, SI/PL tambahan, switch ON/OFF dua panel, PDF export, sesi, dan build.
- Satu kegagalan lama pada `test_meratus_reference_detection` ditemukan baik pada v1.8.36.1 maupun v1.8.36.2.
- GUI Windows belum dieksekusi pada lingkungan uji ini.
